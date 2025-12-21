import asyncio
import structlog
from typing import Dict, List, Any, Type, Optional
from Node.Core.Node.Core.BaseNode import BaseNode, ProducerNode
from Node.Core.Node.Core.Data import NodeOutput
from .flow_graph import FlowGraph
from .flow_analyzer import FlowAnalyzer
from .flow_builder import FlowBuilder
from .flow_node import FlowNode
from .node_registry import NodeRegistry
from .PostProcessing import PostProcessor
from .PostProcessing.queue_mapper import QueueMapper
from .PostProcessing.node_validator import NodeValidator
from .execution.flow_runner import FlowRunner
from .storage.data_store import DataStore
from .events import WorkflowEventEmitter, ExecutionStateTracker

logger = structlog.get_logger(__name__)


class FlowEngine:
    """
    Central coordination system for flow execution.
    """

    _post_processors: List[Type[PostProcessor]] = [QueueMapper, NodeValidator]

    def __init__(self, workflow_id: Optional[str] = None):
        self.workflow_id = workflow_id
        self.data_store = DataStore()
        self.flow_runners: List[FlowRunner] = []
        self.flow_graph = FlowGraph()
        self.flow_analyzer = FlowAnalyzer(self.flow_graph)
        self.flow_builder = FlowBuilder(self.flow_graph, NodeRegistry())
        
        # Event system for real-time updates
        self.events = WorkflowEventEmitter(workflow_id)
        self.state_tracker: Optional[ExecutionStateTracker] = None

    def create_loop(self, producer_flow_node: FlowNode):
        producer = producer_flow_node.instance
        if not isinstance(producer, ProducerNode):
            raise ValueError(f"Node {producer_flow_node.id} is not a ProducerNode")
        runner = FlowRunner(producer_flow_node, events=self.events)
        self.flow_runners.append(runner)

    async def run_production(self):
        logger.info("Starting Production Mode...")
        
        if not self.flow_runners:
            logger.info("No flows to run.")
            return
        
        # Initialize state tracker with total node count
        total_nodes = len(self.flow_graph.node_map)
        self.state_tracker = ExecutionStateTracker(self.workflow_id, total_nodes)
        
        # Wire events to state tracker
        self._wire_events_to_state_tracker()
        
        # Start workflow
        self.state_tracker.start_workflow()
        
        # Register all runners
        for _ in self.flow_runners:
            self.state_tracker.register_runner()
        
        self.tasks = [asyncio.create_task(runner.start()) for runner in self.flow_runners]

        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            logger.info("Production execution cancelled")
        except Exception as e:
            if self.state_tracker:
                self.state_tracker.on_workflow_failed(str(e))
            raise
        finally:
            # Unregister runners (this will mark workflow as complete when all done)
            if self.state_tracker:
                for _ in self.flow_runners:
                    self.state_tracker.unregister_runner()
    
    def _wire_events_to_state_tracker(self):
        """Wire event emitter to state tracker for automatic state updates."""
        if not self.state_tracker:
            return
        
        self.events.subscribe(
            WorkflowEventEmitter.NODE_STARTED,
            lambda data: self.state_tracker.on_node_started(
                data.get("node_id"),
                data.get("node_type")
            )
        )
        
        self.events.subscribe(
            WorkflowEventEmitter.NODE_COMPLETED,
            lambda data: self.state_tracker.on_node_completed(
                data.get("node_id"),
                data.get("node_type"),
                data.get("route")
            )
        )
        
        self.events.subscribe(
            WorkflowEventEmitter.NODE_FAILED,
            lambda data: self.state_tracker.on_node_failed(
                data.get("node_id"),
                data.get("node_type"),
                data.get("error")
            )
        )

    def force_shutdown(self):
        """
        Forcefully terminate all execution loops.
        Does not wait for running tasks to complete.
        """
        logger.warning("Initiating FORCE SHUTDOWN of all flows")
        
        # 1. Cancel all runner tasks (breaks await on async calls like brpop)
        if hasattr(self, 'tasks'):
            for task in self.tasks:
                if not task.done():
                    task.cancel()
        
        # 2. Force shutdown internal executors
        for runner in self.flow_runners:
            runner.shutdown(force=True)
        
        self.flow_runners.clear()

    async def run_development_node(self, node_id: str, input_data: NodeOutput) -> NodeOutput:
        node = self.flow_graph.get_node_instance(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        result = await node.run(input_data)
        return result

    def load_workflow(self, workflow_json: Dict[str, Any]):
        self.flow_builder.load_workflow(workflow_json)

        for processor_class in self._post_processors:
            processor = processor_class(self.flow_graph)
            processor.execute()

        first_node_id = self.flow_analyzer.get_first_node_id()
        if first_node_id:
            first_node = self.flow_graph.node_map[first_node_id]
            logger.info(f"Workflow Loaded Successfully", graph=first_node.to_dict())
        else:
            raise ValueError("No first node found in the workflow")

        producer_nodes = self.flow_analyzer.get_producer_nodes()
        for producer_flow_node in producer_nodes:
            try:
                self.create_loop(producer_flow_node)
                logger.info(f"Created Loop", producer_node_id=producer_flow_node.id)
            except ValueError as e:
                logger.warning(f"Failed to create loop", error=str(e))
