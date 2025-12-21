from typing import Any, Dict, List, Optional
import structlog
from Node.Core.Node.Core.Data import NodeConfig
from .flow_graph import FlowGraph
from .node_registry import NodeRegistry
from .flow_utils import BranchKeyNormalizer
from .flow_node import FlowNode

logger = structlog.get_logger(__name__)


class FlowBuilder:
    """
    Handles building flow graph from JSON definitions.
    """

    def __init__(self, graph: FlowGraph, node_registry: NodeRegistry):
        self.graph = graph
        self.node_registry = node_registry

    def load_workflow(self, workflow_json: Dict[str, Any]) -> None:
        logger.info("Loading workflow...")
        self._add_nodes(workflow_json.get("nodes", []))
        self._connect_nodes(workflow_json.get("edges", []))

    def _add_nodes(self, nodes: List[Dict[str, Any]]):
        for node_def in nodes:
            try:
                flow_node = self._get_flow_node_instance(node_def)
                if flow_node:
                    self.graph.add_node(flow_node)
            except ValueError as e:
                logger.error(f"Could not add node: {e}")
                raise e

    def _get_flow_node_instance(self, node_def: Dict[str, Any]) -> Optional[FlowNode]:
        node_config = NodeConfig(**node_def)
        base_node = self.node_registry.create_node(node_config)
        if not base_node:
            return None
        return FlowNode(id=node_config.id, instance=base_node)

    def _connect_nodes(self, edges: List[Dict[str, Any]]):
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            source_handle = edge.get("sourceHandle")
            if source and target:
                key = BranchKeyNormalizer.normalize_to_lowercase(source_handle)
                try:
                    self.graph.connect_nodes(source, target, key)
                except ValueError as e:
                    logger.warning(f"Could not connect {source} -> {target}: {e}")
