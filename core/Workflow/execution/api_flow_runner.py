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

import structlog
from typing import Dict, List, Optional, TYPE_CHECKING

from Node.Core.Node.Core.BaseNode import ProducerNode, NonBlockingNode, ConditionalNode
from Node.Core.Node.Core.Data import NodeOutput
from ..flow_utils import node_type
from ..flow_node import FlowNode
from .pool_executor import PoolExecutor

if TYPE_CHECKING:
    from ..events import WorkflowEventEmitter

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
        events: Optional["WorkflowEventEmitter"] = None
    ):
        """
        Initialize the API flow runner.
        
        Args:
            start_node: The first node to execute (typically WebhookProducer)
            executor: Optional pool executor (creates default if not provided)
            events: Optional event emitter for workflow events
        """
        self.start_node = start_node
        self.executor = executor or PoolExecutor()
        self.events = events
        self.last_output: Optional[NodeOutput] = None

    def run(self, input_data: NodeOutput) -> NodeOutput:
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
        self._init_nodes()
        
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
            output = self.executor.execute_in_pool(
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
            
            # Process all downstream nodes
            self._process_downstream(self.start_node, output)
            
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

    def _process_downstream(
        self, current_flow_node: FlowNode, input_data: NodeOutput
    ):
        """
        Recursively process downstream nodes sequentially.
        
        Handles branching logic:
        - If ConditionalNode: Executes selected branch based on condition result
        - Otherwise: Executes default branch
        
        Args:
            current_flow_node: The node that just completed
            input_data: Output from the current node (input for next nodes)
        """
        next_nodes: Optional[Dict[str, List[FlowNode]]] = current_flow_node.next
        if not next_nodes:
            # No more nodes - execution complete
            logger.info(
                "API execution: Reached end of workflow",
                last_node_id=current_flow_node.id
            )
            return

        instance = current_flow_node.instance
        nodes_to_run: List[FlowNode] = []
        keys_to_process = set()

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

        # Execute selected nodes sequentially
        for next_flow_node in nodes_to_run:
            next_instance = next_flow_node.instance
            next_node_type = next_instance.identifier()

            # Emit node_started event
            if self.events:
                self.events.emit_node_started(next_flow_node.id, next_node_type)

            logger.info(
                "API execution: Executing node",
                node_id=next_flow_node.id,
                node_type=f"{node_type(next_instance)}({next_node_type})"
            )

            try:
                output = self.executor.execute_in_pool(
                    next_instance.execution_pool, next_instance, input_data
                )

                # Determine route for conditional nodes
                route = None
                if isinstance(next_instance, ConditionalNode) and next_instance.output:
                    route = next_instance.output

                # Emit node_completed event
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

                # Update last output
                self.last_output = output

                # Continue to downstream nodes (recursive)
                self._process_downstream(next_flow_node, output)

            except Exception as e:
                # Emit node_failed event
                if self.events:
                    self.events.emit_node_failed(next_flow_node.id, next_node_type, str(e))
                logger.exception(
                    "API execution: Node failed",
                    node_id=next_flow_node.id,
                    error=str(e)
                )
                raise

    def _init_nodes(self):
        """Initialize all nodes in the flow by calling their init() method."""
        visited = set()
        self._init_node_recursive(self.start_node, visited)

    def _init_node_recursive(self, flow_node: FlowNode, visited: set):
        """Recursively initialize a node and its downstream nodes."""
        if flow_node.id in visited:
            return
        visited.add(flow_node.id)
        
        flow_node.instance.init()
        
        for branch_nodes in flow_node.next.values():
            for next_node in branch_nodes:
                self._init_node_recursive(next_node, visited)
