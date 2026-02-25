import asyncio
import structlog
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from ...Node.Core.Node.Core.BaseNode import ProducerNode, NonBlockingNode, ConditionalNode, LoopNode
from ...Node.Core.Node.Core.Data import NodeOutput, PoolType
from ..flow_utils import node_type, log_safe_output
from ..flow_node import FlowNode
from .pool_executor import PoolExecutor
from .fork_join import merge_branch_outputs
from ...Node.Core.Node.Core.Data import ExecutionCompleted

if TYPE_CHECKING:
    from ..events import WorkflowEventEmitter
    from ..flow_graph import FlowGraph


logger = structlog.get_logger(__name__)


class FlowRunner:
    """
    Manages a single flow loop in Production Mode.
    """

    def __init__(
        self,
        producer_flow_node: FlowNode,
        executor: Optional[PoolExecutor] = None,
        events: Optional["WorkflowEventEmitter"] = None,
        flow_graph: Optional["FlowGraph"] = None,
        fork_execution_pool: Optional[str] = None,
    ):
        self.producer_flow_node = producer_flow_node
        self.producer = producer_flow_node.instance
        self.executor = executor or PoolExecutor()
        self.events = events
        self.flow_graph = flow_graph
        self.fork_execution_pool = fork_execution_pool
        self.running = False
        self.loop_count = 0

    def _get_pool_for_fork_branch(self, flow_node: FlowNode) -> PoolType:
        """Resolve pool for a fork branch: fork_execution_pool if set, else node's execution_pool."""
        if self.fork_execution_pool:
            m = {"process": PoolType.PROCESS, "thread": PoolType.THREAD, "async": PoolType.ASYNC}
            return m.get(self.fork_execution_pool.lower(), flow_node.instance.execution_pool)
        return flow_node.instance.execution_pool

    def _is_join_node(self, node_id: str) -> bool:
        """True if node has more than one upstream (join point)."""
        if not self.flow_graph:
            return False
        return len(self.flow_graph.get_upstream_nodes(node_id)) > 1

    async def _run_branch_until_join_or_sink(
        self,
        current_flow_node: FlowNode,
        input_data: NodeOutput,
    ) -> Tuple[Optional[FlowNode], NodeOutput]:
        """
        Run path from current node until we hit a join node or sink.
        Returns (join_flow_node, branch_final_output) or (None, output) if sink.
        Does not run the join node; caller merges and runs it once.
        """
        instance = current_flow_node.instance
        next_node_type = instance.identifier()
        if self.events:
            self.events.emit_node_started(current_flow_node.id, next_node_type)
        logger.info(
            "Initiating node execution",
            node_id=current_flow_node.id,
            node_type=f"{node_type(instance)}({next_node_type})",
        )
        try:
            pool = self._get_pool_for_fork_branch(current_flow_node)
            output = await self.executor.execute_in_pool(pool, instance, input_data)
        except Exception as e:
            if self.events:
                self.events.emit_node_failed(current_flow_node.id, next_node_type, str(e))
            logger.exception("Error executing node", node_id=current_flow_node.id, error=str(e))
            raise
        route = None
        if isinstance(instance, ConditionalNode) and instance.output:
            route = instance.output
        if self.events:
            self.events.emit_node_completed(
                current_flow_node.id,
                next_node_type,
                output_data=log_safe_output(output.data) if hasattr(output, "data") and output.data else None,
                route=route,
            )
        logger.info(
            "Node execution completed",
            node_id=current_flow_node.id,
            node_type=f"{node_type(instance)}({next_node_type})",
            output=log_safe_output(output.data),
        )
        if isinstance(instance, NonBlockingNode):
            return (None, output)
        next_nodes = current_flow_node.next.get("default") or []
        if not next_nodes:
            return (None, output)
        next_flow_node = next_nodes[0]
        if self._is_join_node(next_flow_node.id):
            return (next_flow_node, output)
        return await self._run_branch_until_join_or_sink(next_flow_node, output)

    async def start(self):
        self.running = True
        await self._init_nodes()
        
        try:
            while self.running:
                self.loop_count += 1
                try:
                    producer = self.producer_flow_node.instance
                    producer_type = producer.identifier()
                    
                    # Emit node_started event
                    if self.events:
                        self.events.emit_node_started(self.producer_flow_node.id, producer_type)
                    
                    logger.info("Initiating node execution", node_id=self.producer_flow_node.id, node_type=f"{node_type(producer)}({producer_type})")
                    data = await self.executor.execute_in_pool(
                        producer.execution_pool, producer, NodeOutput(data={})
                    )
                    
                    # Determine route for conditional nodes
                    route = None
                    if isinstance(producer, ConditionalNode) and producer.output:
                        route = producer.output
                    
                    # Emit node_completed event
                    if self.events:
                        self.events.emit_node_completed(
                            self.producer_flow_node.id,
                            producer_type,
                            output_data=log_safe_output(data.data) if hasattr(data, 'data') and data.data else None,
                            route=route
                        )
                    
                    logger.info(
                        "Node execution completed",
                        node_id=self.producer_flow_node.id,
                        node_type=f"{node_type(producer)}({producer_type})",
                        output=log_safe_output(data.data),
                    )

                    if isinstance(data, ExecutionCompleted):
                        await self.kill_producer()

                    await self._process_next_nodes(
                        self.producer_flow_node, data, current_already_executed=True
                    )

                except asyncio.CancelledError:
                    logger.info("FlowRunner loop cancelled", node_id=self.producer_flow_node.id)
                    self.running = False
                    raise # Re-raise to let the task know it's cancelled
                except Exception as e:
                    logger.exception("Error in loop", error=str(e))
                    await asyncio.sleep(1)
        finally:
           self.shutdown()

    async def _process_next_nodes(
        self,
        current_flow_node: FlowNode,
        input_data: NodeOutput,
        sink_collector: Optional[List[NodeOutput]] = None,
        current_already_executed: bool = False,
    ):
        """
        Recursively process downstream nodes.
        Handles branching logic:
        - If LogicalNode: Executes selected branch (if any).
        - If LoopNode: Runs subDAG per element, then follows default branch only.
        - Otherwise: Executes default branch or first available branch.
        When current_already_executed is False (e.g. subDAG entry), executes the
        current node first and passes its output to next nodes.
        When sink_collector is provided and there are no next nodes, appends the
        current node's output (input_data, already produced by the parent) to
        sink_collector. Does not re-execute the node.
        """
        next_nodes: Optional[Dict[str, List[FlowNode]]] = current_flow_node.next
        if not next_nodes:
            # This node was already executed by the parent; input_data is its output.
            if sink_collector is not None:
                sink_collector.append(input_data)
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
                    "Loop node has no subdag entry; skipping iterations",
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
                    await self._process_next_nodes(
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

            default_list = next_nodes.get("default") or []
            for next_flow_node in default_list:
                if self.events:
                    self.events.emit_node_started(
                        next_flow_node.id, next_flow_node.instance.identifier()
                    )
                try:
                    data = await self.executor.execute_in_pool(
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
                            output_data=log_safe_output(data.data) if hasattr(data, "data") and data.data else None,
                            route=route,
                        )
                    if isinstance(next_flow_node.instance, NonBlockingNode):
                        continue
                    await self._process_next_nodes(
                        next_flow_node, data, current_already_executed=True
                    )
                except Exception as e:
                    if self.events:
                        self.events.emit_node_failed(
                            next_flow_node.id,
                            next_flow_node.instance.identifier(),
                            str(e),
                        )
                    logger.exception(
                        "Error executing node",
                        node_id=next_flow_node.id,
                        error=str(e),
                    )
            return

        # Determine which branches to follow
        if isinstance(input_data, ExecutionCompleted):
            # If Sentinel Pill, broadcast to ALL downstream nodes regardless of logic
            for key in next_nodes:
                keys_to_process.add(key)

        elif isinstance(instance, ConditionalNode):
            # For LogicalNodes, we follow the selected output branch
            if instance.output:
                keys_to_process.add(instance.output)
        else:
            # For non-LogicalNodes, we follow the default branch
            keys_to_process.add("default")

        # Collect all nodes from selected branches
        for key in keys_to_process:
            if key in next_nodes:
                nodes_to_run.extend(next_nodes[key])

        # Current node's output: use input_data if already executed (e.g. producer),
        # otherwise execute current node first so its output is passed to next nodes.
        if current_already_executed:
            current_output = input_data
        else:
            if self.events:
                self.events.emit_node_started(current_flow_node.id, instance.identifier())
            logger.info(
                "Initiating node execution",
                node_id=current_flow_node.id,
                node_type=f"{node_type(instance)}({instance.identifier()})",
            )
            try:
                current_output = await self.executor.execute_in_pool(
                    instance.execution_pool, instance, input_data
                )
            except Exception as e:
                if self.events:
                    self.events.emit_node_failed(
                        current_flow_node.id, instance.identifier(), str(e)
                    )
                logger.exception(
                    "Error executing node",
                    node_id=current_flow_node.id,
                    error=str(e),
                )
                raise
            if self.events:
                self.events.emit_node_completed(
                    current_flow_node.id,
                    instance.identifier(),
                    output_data=log_safe_output(current_output.data) if hasattr(current_output, "data") and current_output.data else None,
                )
            logger.info(
                "Node execution completed",
                node_id=current_flow_node.id,
                node_type=f"{node_type(instance)}({instance.identifier()})",
                output=log_safe_output(current_output.data),
            )

        # Fork path: multiple next nodes and graph available -> run branches in parallel, merge at join
        if len(nodes_to_run) > 1 and self.flow_graph:
            logger.info("Running N branches in parallel", n=len(nodes_to_run))
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
                    "Running join node with M upstream outputs",
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
                            join_flow_node.id, join_node_type, str(e)
                        )
                    logger.exception(
                        "Error executing join node",
                        node_id=join_flow_node.id,
                        error=str(e),
                    )
                    raise
                if self.events:
                    self.events.emit_node_completed(
                        join_flow_node.id,
                        join_node_type,
                        output_data=log_safe_output(join_result.data) if hasattr(join_result, "data") and join_result.data else None,
                    )
                await self._process_next_nodes(
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
                "Initiating node execution",
                node_id=next_flow_node.id,
                node_type=f"{node_type(next_instance)}({next_node_type})",
            )

            try:
                data = await self.executor.execute_in_pool(
                    next_instance.execution_pool, next_instance, current_output
                )

                route = None
                if isinstance(next_instance, ConditionalNode) and next_instance.output:
                    route = next_instance.output

                if self.events:
                    self.events.emit_node_completed(
                        next_flow_node.id,
                        next_node_type,
                        output_data=log_safe_output(data.data) if hasattr(data, 'data') and data.data else None,
                        route=route
                    )

                logger.info(
                    "Node execution completed",
                    node_id=next_flow_node.id,
                    node_type=f"{node_type(next_instance)}({next_node_type})",
                    output=log_safe_output(data.data),
                )

                if isinstance(next_instance, NonBlockingNode):
                    continue

                await self._process_next_nodes(
                    next_flow_node, data, sink_collector, current_already_executed=True
                )

            except Exception as e:
                if self.events:
                    self.events.emit_node_failed(next_flow_node.id, next_node_type, str(e))
                logger.exception(
                    "Error executing node", node_id=next_flow_node.id, error=str(e)
                )

    async def kill_producer(self):
        # Clean up producer resources
        await self.producer.cleanup()
        # Set running to False to stop next iteration
        self.running = False
        logger.warning("Producer cleanup completed", node_id=self.producer_flow_node.id, node_type=f"{node_type(self.producer)}({self.producer.identifier()})")

    def shutdown(self, force: bool = False):
        logger.info(
            "Shutting down FlowRunner",
            loop_count=self.loop_count,
            node_id=self.producer_flow_node.id,
            node_type=f"{node_type(self.producer)}({self.producer.identifier()})",
            force=force
        )
        if force:
            self.running = False
            # Force shutdown executor (don't wait for tasks)
            self.executor.shutdown(wait=False)
        else:
            self.executor.shutdown(wait=True)

    async def _init_nodes(self):
        """Initialize all nodes in the flow by calling their init() method."""
        visited = set()
        await self._init_node_recursive(self.producer_flow_node, visited)

    async def _init_node_recursive(self, flow_node: FlowNode, visited: set):
        """Recursively initialize a node and its downstream nodes."""
        if flow_node.id in visited:
            return
        visited.add(flow_node.id)
        
        await flow_node.instance.init()
        
        for branch_nodes in flow_node.next.values():
            for next_node in branch_nodes:
                await self._init_node_recursive(next_node, visited)
