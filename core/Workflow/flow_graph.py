from typing import Dict, List, Optional

import structlog
from Node.Core.Node.Core.BaseNode import BaseNode
from .flow_utils import node_type
from .flow_node import FlowNode

logger = structlog.get_logger(__name__)


class FlowGraph:
    """
    Class to hold flow graph structure with linked FlowNode instances.
    Follows Single Responsibility Principle - only handles graph structure management.
    """

    def __init__(self):
        self.node_map: Dict[str, FlowNode] = {}

    def add_node(self, flow_node: FlowNode):
        """
        Add a node to the graph.
        """
        if flow_node.id in self.node_map:
            raise ValueError(
                f"Node with id '{flow_node.id}' already exists in the graph"
            )

        self.node_map[flow_node.id] = flow_node
        logger.info(f"FlowNode Added To Graph", node_id=flow_node.id, base_node_type=node_type(flow_node.instance), identifier=f"{flow_node.instance.__class__.__name__}({flow_node.instance.identifier()})")

    def add_node_at_end_of(
        self, node_id: str, flow_node: FlowNode, key: str = "default"
    ):
        """
        Add a node at the end of a specific node.
        """
        if node_id not in self.node_map:
            raise ValueError(f"Node with id '{node_id}' not found in the graph")

        self.add_node(flow_node)
        self.node_map[node_id].add_next(flow_node, key)

    def connect_nodes(self, from_id: str, to_id: str, key: str = "default"):
        """
        Connect two existing nodes.
        """
        if from_id not in self.node_map:
            raise ValueError(f"Node with id '{from_id}' not found in the graph")
        if to_id not in self.node_map:
            raise ValueError(f"Node with id '{to_id}' not found in the graph")

        self.node_map[from_id].add_next(self.node_map[to_id], key)
        logger.info(f"Connected Nodes", from_id=from_id, to_id=to_id, key=key)

    def get_all_next(self, node_id: str) -> Dict[str, List[FlowNode]]:
        """
        Get all next nodes.
        """
        if node_id not in self.node_map:
            return {}

        node = self.node_map[node_id]
        return node.next.copy()

    def get_node(self, node_id: str) -> Optional[FlowNode]:
        """
        Get FlowNode by ID.
        """
        return self.node_map.get(node_id)

    def get_node_instance(self, node_id: str) -> Optional[BaseNode]:
        """
        Get BaseNode instance by ID.
        """
        flow_node = self.node_map.get(node_id)
        return flow_node.instance if flow_node else None

    def get_upstream_nodes(self, node_id: str) -> List[FlowNode]:
        """
        Get all upstream (parent) nodes that have this node as their next node.
        """
        if node_id not in self.node_map:
            return []
        
        upstream_nodes = []
        
        for flow_node in self.node_map.values():
            for next_nodes_list in flow_node.next.values():
                for next_node in next_nodes_list:
                    if next_node.id == node_id:
                        upstream_nodes.append(flow_node)
                        break
                else:
                    continue
                break
        
        return upstream_nodes
