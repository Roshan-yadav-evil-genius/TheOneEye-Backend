"""
Node dependency resolution service.

This module handles resolving node dependencies and building input payloads
from connected nodes' outputs.
"""

from typing import Dict, Any, List
from ..models import Node, Connection


class DependencyService:
    """Service for resolving node dependencies and input payloads."""
    
    @staticmethod
    def get_node_dependencies(node: Node) -> List[Node]:
        """
        Find all nodes that the given node depends on (incoming connections).
        Returns a list of nodes in execution order (dependencies first).
        """
        dependencies = []
        visited = set()
        
        def collect_dependencies(current_node):
            if current_node.id in visited:
                return
            visited.add(current_node.id)
            
            # Find all incoming connections (nodes that connect TO this node)
            incoming_connections = Connection.objects.filter(
                target_node=current_node
            ).select_related('source_node')
            
            for connection in incoming_connections:
                source_node = connection.source_node
                collect_dependencies(source_node)
                if source_node not in dependencies:
                    dependencies.append(source_node)
        
        collect_dependencies(node)
        return dependencies
    
    @staticmethod
    def get_node_input_payload(node_id: str) -> Dict[str, Any]:
        """
        Get input payload for a node by collecting outputs from its dependency nodes.
        Returns a dictionary keyed by source node ID to preserve all outputs.
        """
        try:
            node = Node.objects.get(id=node_id)
            incoming_connections = Connection.objects.filter(target_node=node)
            
            payload = {}
            for conn in incoming_connections:
                source_node_id = str(conn.source_node.id)
                source_output = conn.source_node.output or {}
                # Keep outputs separated by source node ID to avoid data loss
                payload[source_node_id] = source_output
            
            return payload
        except Node.DoesNotExist:
            return {}
    
    
    @staticmethod
    def get_dependency_tree_info(node: Node) -> Dict[str, Any]:
        """
        Get detailed information about a node's dependency tree for logging.
        """
        dependencies = DependencyService.get_node_dependencies(node)
        
        tree_info = {
            "node_id": str(node.id),
            "node_name": node.node_type.name if node.node_type else "Unknown",
            "dependency_count": len(dependencies),
            "dependencies": []
        }
        
        for i, dep in enumerate(dependencies, 1):
            dep_info = {
                "order": i,
                "id": str(dep.id),
                "name": dep.node_type.name if dep.node_type else f"Node {str(dep.id)[:8]}",
                "has_output": bool(dep.output)
            }
            tree_info["dependencies"].append(dep_info)
        
        return tree_info
    
    @staticmethod
    def validate_dependency_chain(node: Node) -> Dict[str, Any]:
        """
        Validate that all dependencies have required outputs.
        Returns validation result with any missing dependencies.
        """
        dependencies = DependencyService.get_node_dependencies(node)
        missing_outputs = []
        
        for dep in dependencies:
            if not dep.output:
                missing_outputs.append({
                    "id": str(dep.id),
                    "name": dep.node_type.name if dep.node_type else "Unknown"
                })
        
        return {
            "is_valid": len(missing_outputs) == 0,
            "missing_outputs": missing_outputs,
            "total_dependencies": len(dependencies)
        }


# Global instance for backward compatibility
dependency_service = DependencyService()

