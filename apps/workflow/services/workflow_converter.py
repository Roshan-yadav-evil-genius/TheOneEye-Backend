"""
Workflow format converter service.

This module handles converting workflow data from Django model format
(as output by RawWorkFlawSerializer) to the FlowEngine expected format.
"""

from typing import Dict, Any, List
import structlog

logger = structlog.get_logger(__name__)


class WorkflowConverter:
    """Service for converting workflow data formats."""
    
    @staticmethod
    def convert_to_flow_engine_format(workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert RawWorkFlawSerializer output to FlowEngine format.
        
        Django Model Format:
        {
            "id": "uuid",
            "nodes": [
                {"id": "uuid", "node_type": "...", "form_values": {...}, "config": {...}}
            ],
            "connections": [
                {"source_node": "uuid", "target_node": "uuid", "source_handle": "..."}
            ]
        }
        
        FlowEngine Format:
        {
            "nodes": [
                {"id": "uuid", "type": "...", "data": {"form": {...}, "config": {...}}}
            ],
            "edges": [
                {"source": "uuid", "target": "uuid", "sourceHandle": "..."}
            ]
        }
        """
        nodes = WorkflowConverter._convert_nodes(workflow_config.get("nodes", []))
        edges = WorkflowConverter._convert_connections(workflow_config.get("connections", []))
        
        logger.info(
            "Converted workflow to FlowEngine format",
            workflow_id=workflow_config.get("id"),
            node_count=len(nodes),
            edge_count=len(edges)
        )
        
        return {
            "nodes": nodes,
            "edges": edges,
            "env": workflow_config.get("env") or {},
        }
    
    @staticmethod
    def _convert_nodes(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Django node format to FlowEngine node format."""
        converted_nodes = []
        
        for node in nodes:
            converted_node = {
                "id": str(node.get("id", "")),
                "type": node.get("node_type", ""),
                "data": {
                    "form": node.get("form_values", {}),
                    "config": node.get("config", {})
                }
            }
            converted_nodes.append(converted_node)
            
        return converted_nodes
    
    @staticmethod
    def _convert_connections(connections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Django connection format to FlowEngine edge format."""
        edges = []
        
        for conn in connections:
            edge = {
                "source": str(conn.get("source_node", "")),
                "target": str(conn.get("target_node", "")),
                "sourceHandle": conn.get("source_handle", "default")
            }
            edges.append(edge)
            
        return edges
    
    @staticmethod
    def validate_workflow(workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that workflow has required fields.
        Returns validation result with any errors.
        """
        errors = []
        
        nodes = workflow_config.get("nodes", [])
        if not nodes:
            errors.append("Workflow has no nodes")
        
        for i, node in enumerate(nodes):
            if not node.get("id"):
                errors.append(f"Node at index {i} has no id")
            if not node.get("node_type"):
                errors.append(f"Node at index {i} has no node_type")
        
        connections = workflow_config.get("connections", [])
        node_ids = {str(n.get("id")) for n in nodes}
        
        for i, conn in enumerate(connections):
            source = str(conn.get("source_node", ""))
            target = str(conn.get("target_node", ""))
            
            if source not in node_ids:
                errors.append(f"Connection {i} references unknown source node: {source}")
            if target not in node_ids:
                errors.append(f"Connection {i} references unknown target node: {target}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }


# Global instance for convenience
workflow_converter = WorkflowConverter()

