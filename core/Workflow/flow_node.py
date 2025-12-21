"""
FlowNode - Core Data Structure for Flow Graph

ARCHITECTURAL CHANGE: Multiple Branch Support
=============================================
Previously, FlowNode.next was Dict[str, FlowNode], meaning only one node
could be stored per key. This prevented multiple outgoing edges with the same key
(e.g., multiple "default" branches) from being stored.

CHANGE: next is now Dict[str, List[FlowNode]]
- Allows multiple nodes per key (e.g., multiple "default" branches)
- When multiple edges share the same key, they are stored as a list
- Example: workflow1.json has two edges from node "1" with sourceHandle=null
  Both normalize to "default" key and are stored as a list: ["node_10", "node_14"]

EXECUTION BEHAVIOR:
- Logical nodes: Select first node from list for chosen branch key ("yes"/"no")
- Non-logical nodes: Execute ALL nodes in list sequentially
- Backward compatible: Single-node lists behave like old single-node structure
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from Node.Core.Node.Core.BaseNode import BaseNode


@dataclass
class FlowNode:
    """
    Data structure representing a node in the flow graph.
    Contains only node data and connection management.
    
    ARCHITECTURE:
    - id: Unique identifier for the node
    - instance: The actual BaseNode implementation (ProducerNode, BlockingNode, etc.)
    - next: Dictionary mapping branch keys to lists of next FlowNodes
            Key examples: "default", "yes", "no" (for logical branches)
            Value: List of FlowNodes (supports multiple branches per key)
    
    MULTIPLE BRANCH SUPPORT:
    The 'next' field uses Dict[str, List[FlowNode]] instead of Dict[str, FlowNode]
    to support multiple outgoing edges with the same key. This is essential for workflows
    like workflow1.json where node "1" has two edges both with sourceHandle=null, which
    both normalize to the "default" key.
    """
    id: str
    instance: BaseNode
    
    next: Dict[str, List["FlowNode"]] = field(default_factory=dict)

    def add_next(self, node: "FlowNode", key: str = "default"):
        """
        Add a next node connection.
        """
        if key not in self.next:
            self.next[key] = []
        self.next[key].append(node)
    
    def get_all_next_nodes(self) -> List["FlowNode"]:
        """
        Get all next nodes flattened from all branches.
        """
        all_nodes = []
        for node_list in self.next.values():
            all_nodes.extend(node_list)
        return all_nodes
    
    def to_dict(self, visited: Optional[set] = None) -> Dict[str, Any]:
        """
        Convert FlowNode to dictionary for serialization.
        """
        if visited is None:
            visited = set()

        if self.id in visited:
            return {"id": self.id, "next": {}, "_circular_reference": True}

        visited.add(self.id)

        next_dict = {}
        for key, next_nodes_list in self.next.items():
            if len(next_nodes_list) == 1:
                next_dict[key] = next_nodes_list[0].to_dict(visited.copy())
            else:
                next_dict[key] = [node.to_dict(visited.copy()) for node in next_nodes_list]

        return {
            "id": self.id,
            "next": next_dict
        }
