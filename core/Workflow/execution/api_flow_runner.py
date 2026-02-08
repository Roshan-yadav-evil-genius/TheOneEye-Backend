"""
API Flow Runner - Single-pass workflow execution for request-response workflows.

This module provides synchronous, single-pass workflow execution for API workflows.
Unlike FlowRunner which runs in an infinite loop for production workflows,
APIFlowRunner executes the workflow once and returns the final output.

Key Differences from FlowRunner:
- No `while self.running` loop - single pass execution
- Accepts initial input_data - passed to first node (WebhookProducer)
- Tracks last_output - returns final node's output
- All nodes must complete in sequence (no NonBlockingNode skip behavior)
"""

import asyncio
import structlog
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from ...Node.Core.Node.Core.BaseNode import ProducerNode, NonBlockingNode, ConditionalNode, LoopNode
from ...Node.Core.Node.Core.Data import NodeOutput, PoolType
from ..flow_utils import node_type
from ..flow_node import FlowNode
from .pool_executor import PoolExecutor
from .fork_join import merge_branch_outputs

if TYPE_CHECKING:
    from ..events import WorkflowEventEmitter
    from ..flow_graph import FlowGraph

logger = structlog.get_logger(__name__)


class APIFlowRunner:
    """
    Single-pass workflow runner for API request-response execution.
    
    This runner executes a workflow once from start to finish, collecting
    the output from the last executed node. It's designed for synchronous
    API workflows where the caller expects a response.
    
    Attributes:
        start_node: The first node in the workflow (must be WebhookProducer)
        executor: Pool executor for running nodes in appropriate pools
        events: Event emitter for workflow events
        last_output: The output from the last executed node
    """

    def __init__(
        self,
        start_node: FlowNode,
        executor: Optional[PoolExecutor] = None,
        events: Optional["WorkflowEventEmitter"] = None,
        flow_graph: Optional["FlowGraph"] = None,
        fork_execution_pool: Optional[str] = None,
    ):
        """
        Initialize the API flow runner.

        Args:
            start_node: The first node to execute (typically WebhookProducer)
            executor: Optional pool executor (creates default if not provided)
            events: Optional event emitter for workflow events
            flow_graph: Optional graph for join detection (len(upstream) > 1)
            fork_execution_pool: Optional "process" | "thread" | "async" for fork branches
        """
        self.start_node = start_node
        self.executor = executor or PoolExecutor()
        self.events = events
        self.flow_graph = flow_graph
        self.fork_execution_pool = fork_execution_pool
        self.last_output: Optional[NodeOutput] = None

    def _get_pool_for_fork_branch(self, flow_node: FlowNode) -> PoolType:
        if self.fork_execution_pool:
            m = {"process": PoolType.PROCESS, "thread": PoolType.THREAD, "async": PoolType.ASYNC}
            return m.get(self.fork_execution_pool.lower(), flow_node.instance.execution_pool)
        return flow_node.instance.execution_pool

    def _is_join_node(self, node_id: str) -> bool:
        if not self.flow_graph:
            return False
        return len(self.flow_graph.get_upstream_nodes(node_id)) > 1

    async def _run_branch_until_join_or_sink(
        self,
        current_flow_node: FlowNode,
        input_data: NodeOutput,
    ) -> Tuple[Optional[FlowNode], NodeOutput]:
        instance = current_flow_node.instance
        next_node_type = instance.identifier()
        if self.events:
            self.events.emit_node_started(current_flow_node.id, next_node_type)
        logger.info(
            "API execution: Executing node",
            node_id=current_flow_node.id,
            node_type=f"{node_type(instance)}({next_node_type})",
        )
        try:
            pool = self._get_pool_for_fork_branch(current_flow_node)
            output = await self.executor.execute_in_pool(pool, instance, input_data)
        except Exception as e:
            if self.events:
                self.events.emit_node_failed(current_flow_node.id, next_node_type, str(e))
            logger.exception(
                "API execution: Node failed",
                node_id=current_flow_node.id,
                error=str(e),
            )
            raise
        route = None
        if isinstance(instance, ConditionalNode) and instance.output:
            route = instance.output
        if self.events:
            self.events.emit_node_completed(
                current_flow_node.id,
                next_node_type,
                output_data=output.data if hasattr(output, "data") else None,
                route=route,
            )
        logger.info(
            "API execution: Node completed",
            node_id=current_flow_node.id,
            node_type=f"{node_type(instance)}({next_node_type})",
            output=output.data,
        )
        # LoopNode: run subDAG per item, build aggregated_output, then continue along default out-edge
        if isinstance(instance, LoopNode):
            items = output.data.get("items", [])
            next_nodes = current_flow_node.next
            subdag_list = next_nodes.get("subdag") or []
            entry_flow_node = subdag_list[0] if subdag_list else None
            if not entry_flow_node:
                aggregated_data = dict(output.data)
                aggregated_data["loop_results"] = []
                aggregated_data["forEachNode"] = {
                    "input": items,
                    "results": [],
                    "state": {"index": len(items) - 1, "item": items[-1]} if items else {"index": 0, "item": None},
                }
                output = NodeOutput(
                    id=output.id,
                    data=aggregated_data,
                    metadata=output.metadata,
                )
            else:
                all_results: List = []
                for idx, element in enumerate(items):
                    for_each_for_subdag = {
                        "input": items,
                        "results": list(all_results),
                        "state": {"index": idx, "item": element},
                    }
                    element_output = NodeOutput(
                        id=output.id,
                        data={**output.data, "forEachNode": for_each_for_subdag},
                        metadata=output.metadata,
                    )
                    collected: List[NodeOutput] = []
                    await self._process_downstream(
                        entry_flow_node, element_output, sink_collector=collected
                    )
                    iteration_data = [o.data for o in collected]
                    if len(iteration_data) == 1:
                        all_results.append(iteration_data[0])
                    elif iteration_data:
                        all_results.append(iteration_data)
                aggregated_data = dict(output.data)
                aggregated_data["loop_results"] = all_results
                aggregated_data["forEachNode"] = {
                    "input": items,
                    "results": all_results,
                    "state": {"index": len(items) - 1, "item": items[-1]} if items else {"index": 0, "item": None},
                }
                output = NodeOutput(
                    id=output.id,
                    data=aggregated_data,
                    metadata=output.metadata,
                )
            default_list = next_nodes.get("default") or []
            if not default_list:
                return (None, output)
            next_flow_node = default_list[0]
            if self.events:
                self.events.emit_node_started(next_flow_node.id, next_flow_node.instance.identifier())
            logger.info(
                "API execution: Executing node",
                node_id=next_flow_node.id,
                node_type=f"{node_type(next_flow_node.instance)}({next_flow_node.instance.identifier()})",
            )
            try:
                next_output = await self.executor.execute_in_pool(
                    next_flow_node.instance.execution_pool,
                    next_flow_node.instance,
                    output,
                )
            except Exception as e:
                if self.events:
                    self.events.emit_node_failed(next_flow_node.id, next_flow_node.instance.identifier(), str(e))
                logger.exception(
                    "API execution: Node failed",
                    node_id=next_flow_node.id,
                    error=str(e),
                )
                raise
            route = None
            if isinstance(next_flow_node.instance, ConditionalNode) and next_flow_node.instance.output:
                route = next_flow_node.instance.output
            if self.events:
                self.events.emit_node_completed(
                    next_flow_node.id,
                    next_flow_node.instance.identifier(),
                    output_data=next_output.data if hasattr(next_output, "data") else None,
                    route=route,
                )
            logger.info(
                "API execution: Node completed",
                node_id=next_flow_node.id,
                node_type=f"{node_type(next_flow_node.instance)}({next_flow_node.instance.identifier()})",
                output=next_output.data,
            )
            if self._is_join_node(next_flow_node.id):
                return (next_flow_node, next_output)
            return await self._run_branch_until_join_or_sink(next_flow_node, next_output)
        if isinstance(instance, NonBlockingNode):
            return (None, output)
        next_nodes = current_flow_node.next.get("default") or []
        if not next_nodes:
            return (None, output)
        next_flow_node = next_nodes[0]
        if self._is_join_node(next_flow_node.id):
            return (next_flow_node, output)
        return await self._run_branch_until_join_or_sink(next_flow_node, output)

    async def run(self, input_data: NodeOutput) -> NodeOutput:
        """
        Execute the workflow once from start to finish.
        
        Args:
            input_data: Initial input data (passed to first node)
            
        Returns:
            NodeOutput from the last executed node
            
        Raises:
            Exception: If any node execution fails
        """
        # Initialize all nodes first
        await self._init_nodes()
        
        # Execute start node with input data
        start_instance = self.start_node.instance
        start_node_type = start_instance.identifier()
        
        # Emit node_started event
        if self.events:
            self.events.emit_node_started(self.start_node.id, start_node_type)
        
        logger.info(
            "API execution: Starting first node",
            node_id=self.start_node.id,
            node_type=f"{node_type(start_instance)}({start_node_type})"
        )
        
        try:
            output = await self.executor.execute_in_pool(
                start_instance.execution_pool, start_instance, input_data
            )
            
            # Determine route for conditional nodes
            route = None
            if isinstance(start_instance, ConditionalNode) and start_instance.output:
                route = start_instance.output
            
            # Emit node_completed event
            if self.events:
                self.events.emit_node_completed(
                    self.start_node.id,
                    start_node_type,
                    output_data=output.data if hasattr(output, 'data') else None,
                    route=route
                )
            
            logger.info(
                "API execution: First node completed",
                node_id=self.start_node.id,
                node_type=f"{node_type(start_instance)}({start_node_type})",
                output=output.data
            )
            
            # Track last output
            self.last_output = output
            
            # Process all downstream nodes (start node already executed above)
            await self._process_downstream(
                self.start_node, output, sink_collector=None, current_already_executed=True
            )
            
            return self.last_output
            
        except Exception as e:
            # Emit node_failed event
            if self.events:
                self.events.emit_node_failed(self.start_node.id, start_node_type, str(e))
            logger.exception(
                "API execution: First node failed",
                node_id=self.start_node.id,
                error=str(e)
            )
            raise
        finally:
            # Shutdown executor
            self.executor.shutdown(wait=True)

    async def _process_downstream(
        self,
        current_flow_node: FlowNode,
        input_data: NodeOutput,
        sink_collector: Optional[List[NodeOutput]] = None,
        current_already_executed: bool = False,
    ):
        """
        Recursively process downstream nodes sequentially.
        
        Handles branching logic:
        - If LoopNode: Runs subDAG per element, then follows default branch only.
        - If ConditionalNode: Executes selected branch based on condition result
        - Otherwise: Executes default branch
        
        When current_already_executed is False (e.g. subDAG entry), executes the
        current node first and passes its output to next nodes. When True (e.g.
        start node from run()), uses input_data as current output.
        
        When sink_collector is provided and there are no next nodes, appends the
        current node's output (input_data, already produced by the parent) to
        sink_collector; otherwise sets last_output. Does not re-execute the node.
        """
        next_nodes: Optional[Dict[str, List[FlowNode]]] = current_flow_node.next
        if not next_nodes:
            # This node was already executed by the parent; input_data is its output.
            # Collect it without re-executing (re-execution caused forEachNode etc. to be lost).
            if sink_collector is not None:
                sink_collector.append(input_data)
            else:
                self.last_output = input_data
            logger.info(
                "API execution: Reached end of workflow",
                last_node_id=current_flow_node.id,
            )
            return

        instance = current_flow_node.instance
        nodes_to_run: List[FlowNode] = []
        keys_to_process = set()

        # LoopNode: run subDAG for each element, collect sink outputs, then follow only default branch
        if isinstance(instance, LoopNode):
            items = input_data.data.get("items", [])
            subdag_list = next_nodes.get("subdag") or []
            entry_flow_node = subdag_list[0] if subdag_list else None

            if not entry_flow_node:
                logger.warning(
                    "API execution: Loop node has no subdag entry; skipping iterations",
                    node_id=current_flow_node.id,
                )
                aggregated_data = dict(input_data.data)
                aggregated_data["loop_results"] = []
                aggregated_data["forEachNode"] = {
                    "input": items,
                    "results": [],
                    "state": {"index": len(items) - 1, "item": items[-1]} if items else {"index": 0, "item": None},
                }
                aggregated_output = NodeOutput(
                    id=input_data.id,
                    data=aggregated_data,
                    metadata=input_data.metadata,
                )
            else:
                all_results: List = []
                for idx, element in enumerate(items):
                    # Centralized shape: subDAG receives forEachNode (no top-level item/item_index)
                    for_each_for_subdag = {
                        "input": items,
                        "results": list(all_results),
                        "state": {"index": idx, "item": element},
                    }
                    element_output = NodeOutput(
                        id=input_data.id,
                        data={**input_data.data, "forEachNode": for_each_for_subdag},
                        metadata=input_data.metadata,
                    )
                    collected: List[NodeOutput] = []
                    await self._process_downstream(
                        entry_flow_node, element_output, sink_collector=collected
                    )
                    iteration_data = [o.data for o in collected]
                    if len(iteration_data) == 1:
                        all_results.append(iteration_data[0])
                    elif iteration_data:
                        all_results.append(iteration_data)
                aggregated_data = dict(input_data.data)
                aggregated_data["loop_results"] = all_results
                aggregated_data["forEachNode"] = {
                    "input": items,
                    "results": all_results,
                    "state": {"index": len(items) - 1, "item": items[-1]} if items else {"index": 0, "item": None},
                }
                aggregated_output = NodeOutput(
                    id=input_data.id,
                    data=aggregated_data,
                    metadata=input_data.metadata,
                )

            self.last_output = aggregated_output
            default_list = next_nodes.get("default") or []
            for next_flow_node in default_list:
                if self.events:
                    self.events.emit_node_started(
                        next_flow_node.id, next_flow_node.instance.identifier()
                    )
                try:
                    output = await self.executor.execute_in_pool(
                        next_flow_node.instance.execution_pool,
                        next_flow_node.instance,
                        aggregated_output,
                    )
                    route = None
                    if isinstance(next_flow_node.instance, ConditionalNode) and next_flow_node.instance.output:
                        route = next_flow_node.instance.output
                    if self.events:
                        self.events.emit_node_completed(
                            next_flow_node.id,
                            next_flow_node.instance.identifier(),
                            output_data=output.data if hasattr(output, "data") else None,
                            route=route,
                        )
                    self.last_output = output
                    await self._process_downstream(
                        next_flow_node, output, sink_collector, current_already_executed=True
                    )
                except Exception as e:
                    if self.events:
                        self.events.emit_node_failed(
                            next_flow_node.id,
                            next_flow_node.instance.identifier(),
                            str(e),
                        )
                    logger.exception(
                        "API execution: Node failed",
                        node_id=next_flow_node.id,
                        error=str(e),
                    )
                    raise
            return

        # Determine which branches to follow
        if isinstance(instance, ConditionalNode):
            # For ConditionalNodes, follow the selected output branch
            if instance.output:
                keys_to_process.add(instance.output)
        else:
            # For non-conditional nodes, follow the default branch
            keys_to_process.add("default")

        # Collect all nodes from selected branches
        for key in keys_to_process:
            if key in next_nodes:
                nodes_to_run.extend(next_nodes[key])

        # Current node's output: use input_data if already executed (e.g. start node from run()),
        # otherwise execute current node first so its output is passed to next nodes (e.g. Cosine -> Data Transformer).
        if current_already_executed:
            current_output = input_data
        else:
            if self.events:
                self.events.emit_node_started(current_flow_node.id, instance.identifier())
            logger.info(
                "API execution: Executing node",
                node_id=current_flow_node.id,
                node_type=f"{node_type(instance)}({instance.identifier()})"
            )
            try:
                current_output = await self.executor.execute_in_pool(
                    instance.execution_pool, instance, input_data
                )
            except Exception as e:
                if self.events:
                    self.events.emit_node_failed(current_flow_node.id, instance.identifier(), str(e))
                logger.exception(
                    "API execution: Node failed",
                    node_id=current_flow_node.id,
                    error=str(e)
                )
                raise
            if self.events:
                self.events.emit_node_completed(
                    current_flow_node.id,
                    instance.identifier(),
                    output_data=current_output.data if hasattr(current_output, "data") else None,
                )
            logger.info(
                "API execution: Node completed",
                node_id=current_flow_node.id,
                node_type=f"{node_type(instance)}({instance.identifier()})",
                output=current_output.data
            )
        self.last_output = current_output

        # Fork path: multiple next nodes and graph available -> run branches in parallel, merge at join
        if len(nodes_to_run) > 1 and self.flow_graph:
            logger.info("API execution: Running N branches in parallel", n=len(nodes_to_run))
            tasks = [
                self._run_branch_until_join_or_sink(fn, current_output)
                for fn in nodes_to_run
            ]
            results = await asyncio.gather(*tasks)
            join_to_flow_node_and_outputs: Dict[str, Tuple[FlowNode, List[NodeOutput]]] = {}
            for join_flow_node, branch_out in results:
                if join_flow_node is not None:
                    jid = join_flow_node.id
                    if jid not in join_to_flow_node_and_outputs:
                        join_to_flow_node_and_outputs[jid] = (join_flow_node, [])
                    join_to_flow_node_and_outputs[jid][1].append(branch_out)
            for join_flow_node, branch_outputs in join_to_flow_node_and_outputs.values():
                merged = merge_branch_outputs(current_output, branch_outputs)
                logger.info(
                    "API execution: Running join node with M upstream outputs",
                    node_id=join_flow_node.id,
                    m=len(branch_outputs),
                )
                join_instance = join_flow_node.instance
                join_node_type = join_instance.identifier()
                if self.events:
                    self.events.emit_node_started(join_flow_node.id, join_node_type)
                try:
                    join_result = await self.executor.execute_in_pool(
                        join_instance.execution_pool, join_instance, merged
                    )
                except Exception as e:
                    if self.events:
                        self.events.emit_node_failed(
                            join_flow_node.id, join_node_type, str(e),
                        )
                    logger.exception(
                        "API execution: Join node failed",
                        node_id=join_flow_node.id,
                        error=str(e),
                    )
                    raise
                if self.events:
                    self.events.emit_node_completed(
                        join_flow_node.id,
                        join_node_type,
                        output_data=join_result.data if hasattr(join_result, "data") else None,
                    )
                self.last_output = join_result
                await self._process_downstream(
                    join_flow_node,
                    join_result,
                    sink_collector,
                    current_already_executed=True,
                )
            return

        # Single next node: current behavior
        for next_flow_node in nodes_to_run:
            next_instance = next_flow_node.instance
            next_node_type = next_instance.identifier()

            if self.events:
                self.events.emit_node_started(next_flow_node.id, next_node_type)

            logger.info(
                "API execution: Executing node",
                node_id=next_flow_node.id,
                node_type=f"{node_type(next_instance)}({next_node_type})"
            )

            try:
                output = await self.executor.execute_in_pool(
                    next_instance.execution_pool, next_instance, current_output
                )

                route = None
                if isinstance(next_instance, ConditionalNode) and next_instance.output:
                    route = next_instance.output

                if self.events:
                    self.events.emit_node_completed(
                        next_flow_node.id,
                        next_node_type,
                        output_data=output.data if hasattr(output, 'data') else None,
                        route=route
                    )

                logger.info(
                    "API execution: Node completed",
                    node_id=next_flow_node.id,
                    node_type=f"{node_type(next_instance)}({next_node_type})",
                    output=output.data
                )

                self.last_output = output

                await self._process_downstream(
                    next_flow_node, output, sink_collector, current_already_executed=True
                )

            except Exception as e:
                if self.events:
                    self.events.emit_node_failed(next_flow_node.id, next_node_type, str(e))
                logger.exception(
                    "API execution: Node failed",
                    node_id=next_flow_node.id,
                    error=str(e)
                )
                raise

    async def run_subdag_once(
        self, entry_flow_node: FlowNode, element_output: NodeOutput
    ) -> List[NodeOutput]:
        """
        Run the subDAG once from entry_flow_node with element_output, collecting sink outputs.
        Used for ForEach "iterate and stop" (single iteration).
        """
        collected: List[NodeOutput] = []
        await self._process_downstream(entry_flow_node, element_output, sink_collector=collected)
        return collected

    async def _init_nodes(self):
        """Initialize all nodes in the flow by calling their init() method."""
        visited = set()
        await self._init_node_recursive(self.start_node, visited)

    async def _init_node_recursive(self, flow_node: FlowNode, visited: set):
        """Recursively initialize a node and its downstream nodes."""
        if flow_node.id in visited:
            return
        visited.add(flow_node.id)
        
        await flow_node.instance.init()
        
        for branch_nodes in flow_node.next.values():
            for next_node in branch_nodes:
                await self._init_node_recursive(next_node, visited)
