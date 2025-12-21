from typing import List, Optional, Tuple, Set
import structlog
from Node.Core.Node.Core.BaseNode import BaseNode, ProducerNode, NonBlockingNode
from .flow_graph import FlowGraph
from .flow_node import FlowNode

logger = structlog.get_logger(__name__)


class FlowAnalyzer:
    """
    Handles all graph traversal and analysis operations.
    Follows Single Responsibility Principle - only handles traversal and querying.
    """

    def __init__(self, graph: FlowGraph):
        self.graph = graph

    def get_producer_nodes(self) -> List[FlowNode]:
        return [self.graph.node_map[node_id] for node_id in self.producer_node_ids]

    @property
    def producer_node_ids(self) -> List[str]:
        return [
            node_id
            for node_id, node_instance in self.graph.node_map.items()
            if isinstance(node_instance.instance, ProducerNode)
        ]

    def get_first_node_id(self) -> Optional[str]:
        if not self.graph.node_map:
            return None

        nodes_with_incoming_edges = set()
        for node in self.graph.node_map.values():
            for next_nodes_list in node.next.values():
                for next_node in next_nodes_list:
                    nodes_with_incoming_edges.add(next_node.id)

        root_nodes = [
            node_id for node_id in self.graph.node_map.keys()
            if node_id not in nodes_with_incoming_edges
        ]

        if root_nodes:
            return root_nodes[0]

        producer_ids = self.producer_node_ids
        if producer_ids:
            return producer_ids[0]

        return list(self.graph.node_map.keys())[0] if self.graph.node_map else None

    def find_non_blocking_nodes(self) -> List[FlowNode]:
        return [
            flow_node for flow_node in self.graph.node_map.values()
            if isinstance(flow_node.instance, NonBlockingNode)
        ]

    def find_loops(self) -> List[Tuple[FlowNode, FlowNode]]:
        loops = []
        for producer_node in self.get_producer_nodes():
            ending_node = self._find_ending_node_from_producer(producer_node)
            if ending_node:
                loops.append((producer_node, ending_node))
            else:
                logger.warning(f"No ending NonBlockingNode found for producer {producer_node.id}")
        return loops

    def _find_ending_node_from_producer(self, producer_node: FlowNode) -> Optional[FlowNode]:
        visited: Set[str] = set()
        return self._traverse_to_ending_node(producer_node, visited)

    def _traverse_to_ending_node(self, current_node: FlowNode, visited: Set[str]) -> Optional[FlowNode]:
        if isinstance(current_node.instance, NonBlockingNode):
            return current_node

        if current_node.id in visited:
            return None

        visited.add(current_node.id)

        for next_nodes_list in current_node.next.values():
            for next_flow_node in next_nodes_list:
                ending_node = self._traverse_to_ending_node(next_flow_node, visited.copy())
                if ending_node:
                    return ending_node

        return None

    def build_chain_from_start_to_end(self, start_node: FlowNode, end_node: FlowNode) -> List[BaseNode]:
        chain: List[BaseNode] = []
        visited: Set[str] = {start_node.id}
        current = start_node

        while current and current.id != end_node.id:
            next_nodes = current.next
            if not next_nodes:
                break

            first_list = list(next_nodes.values())[0] if next_nodes else []
            if not first_list:
                break
            next_flow_node = first_list[0]

            if next_flow_node.id == end_node.id:
                chain.append(next_flow_node.instance)
                break

            if next_flow_node.id in visited:
                break

            visited.add(next_flow_node.id)
            chain.append(next_flow_node.instance)
            current = next_flow_node

        return chain
