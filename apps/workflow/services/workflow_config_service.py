"""
Workflow configuration building service.

This module handles building workflow configurations from database models
for use in Docker containers.
"""

from typing import Dict, Any, List
from ..models import WorkFlow, Node, Connection


class WorkflowConfigService:
    """Service for building workflow configurations from database models."""
    
    @staticmethod
    def build_workflow_config(workflow: WorkFlow, task_id: str = None) -> Dict[str, Any]:
        """Build complete workflow configuration from database models."""
        config = {
            "id": str(workflow.id),
            "nodes": WorkflowConfigService.serialize_nodes(workflow),
            "connections": WorkflowConfigService.serialize_connections(workflow)
        }
        
        if task_id:
            config["task_id"] = task_id
            
        return config
    
    @staticmethod
    def serialize_nodes(workflow: WorkFlow) -> List[Dict[str, Any]]:
        """Serialize workflow nodes to configuration format."""
        nodes = []
        
        for node in workflow.nodes.all():
            node_data = {
                "id": str(node.id),
                "node_type": node.node_type or None,
                "form_values": node.form_values or {}
            }
            nodes.append(node_data)
        
        return nodes
    
    @staticmethod
    def serialize_connections(workflow: WorkFlow) -> List[Dict[str, Any]]:
        """Serialize workflow connections to configuration format."""
        connections = []
        
        for connection in workflow.connections.all():
            conn_data = {
                "source_node": str(connection.source_node.id),
                "target_node": str(connection.target_node.id)
            }
            connections.append(conn_data)
        
        return connections
    
    @staticmethod
    def get_workflow_summary(workflow: WorkFlow) -> Dict[str, Any]:
        """Get a summary of the workflow for logging purposes."""
        return {
            "id": str(workflow.id),
            "name": workflow.name,
            "node_count": workflow.nodes.count(),
            "connection_count": workflow.connections.count(),
            "status": workflow.status
        }


# Global instance for backward compatibility
workflow_config_service = WorkflowConfigService()
