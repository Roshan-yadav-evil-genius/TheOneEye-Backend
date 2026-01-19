import time
import threading
import structlog
from typing import Dict, List, Optional, TYPE_CHECKING
from Node.Core.Node.Core.BaseNode import ProducerNode, NonBlockingNode, ConditionalNode
from Node.Core.Node.Core.Data import NodeOutput
from ..flow_utils import node_type
from ..flow_node import FlowNode
from .pool_executor import PoolExecutor
from Node.Core.Node.Core.Data import ExecutionCompleted

if TYPE_CHECKING:
    from ..events import WorkflowEventEmitter


logger = structlog.get_logger(__name__)


class FlowRunner:
    """
    Manages a single flow loop in Production Mode.
    """

    def __init__(
        self, 
        producer_flow_node: FlowNode, 
        executor: Optional[PoolExecutor] = None,
        events: Optional["WorkflowEventEmitter"] = None
    ):
        self.producer_flow_node = producer_flow_node
        self.producer = producer_flow_node.instance
        self.executor = executor or PoolExecutor()
        self.events = events
        self.running = False
        self.loop_count = 0
        self._shutdown_event: Optional[threading.Event] = None

    def start(self):
        self.running = True
        self._init_nodes()
        
        try:
            while self.running:
                # Check if shutdown was requested
                if self._shutdown_event and self._shutdown_event.is_set():
                    logger.info("FlowRunner received shutdown signal", node_id=self.producer_flow_node.id)
                    self.running = False
                    break
                
                self.loop_count += 1
                try:
                    producer = self.producer_flow_node.instance
                    producer_type = producer.identifier()
                    
                    # Emit node_started event
                    if self.events:
                        self.events.emit_node_started(self.producer_flow_node.id, producer_type)
                    
                    logger.info("Initiating node execution", node_id=self.producer_flow_node.id, node_type=f"{node_type(producer)}({producer_type})")
                    data = self.executor.execute_in_pool(
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
                            output_data=data.data if hasattr(data, 'data') else None,
                            route=route
                        )
                    
                    logger.info(
                        "Node execution completed",
                        node_id=self.producer_flow_node.id,
                        node_type=f"{node_type(producer)}({producer_type})",
                        output=data.data,
                    )

                    if isinstance(data, ExecutionCompleted):
                        self.kill_producer()

                    self._process_next_nodes(self.producer_flow_node, data)

                except Exception as e:
                    logger.exception("Error in loop", error=str(e))
                    time.sleep(1)
        finally:
           self.shutdown()

    def _process_next_nodes(
        self, current_flow_node: FlowNode, input_data: NodeOutput
    ):
        """
        Recursively process downstream nodes.
        Handles branching logic:
        - If LogicalNode: Executes selected branch (if any).
        - Otherwise: Executes default branch or first available branch.
        """
        next_nodes: Optional[Dict[str, List[FlowNode]]] = current_flow_node.next
        if not next_nodes:
            # No next nodes, break the loop
            return

        instance = current_flow_node.instance
        nodes_to_run: List[FlowNode] = []
        keys_to_process = set()

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

        # Execute selected nodes
        for next_flow_node in nodes_to_run:
            next_instance = next_flow_node.instance
            next_node_type = next_instance.identifier()

            # Emit node_started event
            if self.events:
                self.events.emit_node_started(next_flow_node.id, next_node_type)

            logger.info(
                "Initiating node execution",
                node_id=next_flow_node.id,
                node_type=f"{node_type(next_instance)}({next_node_type})",
            )

            try:
                data = self.executor.execute_in_pool(
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
                        output_data=data.data if hasattr(data, 'data') else None,
                        route=route
                    )

                logger.info(
                    "Node execution completed",
                    node_id=next_flow_node.id,
                    node_type=f"{node_type(next_instance)}({next_node_type})",
                    output=data.data,
                )

                if isinstance(next_instance, NonBlockingNode):
                    continue

                # Recurse for the next steps in this branch
                self._process_next_nodes(next_flow_node, data)

            except Exception as e:
                # Emit node_failed event
                if self.events:
                    self.events.emit_node_failed(next_flow_node.id, next_node_type, str(e))
                logger.exception(
                    "Error executing node", node_id=next_flow_node.id, error=str(e)
                )

    def kill_producer(self):
        # Clean up producer resources
        self.producer.cleanup()
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

    def _init_nodes(self):
        """Initialize all nodes in the flow by calling their init() method."""
        visited = set()
        self._init_node_recursive(self.producer_flow_node, visited)

    def _init_node_recursive(self, flow_node: FlowNode, visited: set):
        """Recursively initialize a node and its downstream nodes."""
        if flow_node.id in visited:
            return
        visited.add(flow_node.id)
        
        flow_node.instance.init()
        
        for branch_nodes in flow_node.next.values():
            for next_node in branch_nodes:
                self._init_node_recursive(next_node, visited)
