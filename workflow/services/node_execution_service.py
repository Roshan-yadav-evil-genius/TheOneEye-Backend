"""
Node execution orchestration service.

This module handles the orchestration of node execution, including
storing results and managing execution state.
"""

from typing import Dict, Any, Optional
from ..models import Node
from .docker_service import docker_service
from .dependency_service import dependency_service


class NodeExecutionService:
    """Service for orchestrating node execution."""
    
    def __init__(self):
        self.docker_service = docker_service
        self.dependency_service = dependency_service
    
    def execute_node_in_container(self, workflow_id: str, node_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute a node in the container's command server.
        Returns the execution result or None if failed.
        """
        container_name = f"{workflow_id}-dev"
        
        result = self.docker_service.execute_node_in_container(
            container_name=container_name,
            node_id=node_id,
            payload=payload
        )
        
        return result
    
    def store_node_output(self, node_id: str, output: Dict[str, Any]) -> bool:
        """
        Store node execution result in the database.
        Returns True if successful, False otherwise.
        """
        try:
            node = Node.objects.get(id=node_id)
            node.output = output
            node.save()
            print(f"[+] Node {node_id} output stored successfully")
            return True
        except Node.DoesNotExist:
            print(f"[-] Node {node_id} not found")
            return False
        except Exception as e:
            print(f"[-] Error storing node output: {e}")
            return False
    
    def get_node_output(self, node_id: str) -> Dict[str, Any]:
        """
        Get stored output for a node.
        Returns empty dict if no output or node not found.
        """
        try:
            node = Node.objects.get(id=node_id)
            return node.output or {}
        except Node.DoesNotExist:
            return {}
    
    def execute_node_with_dependencies(self, workflow_id: str, node_id: str) -> Dict[str, Any]:
        """
        Execute a node with its dependencies resolved.
        This is the main orchestration method for single node execution.
        """
        try:
            # Get input payload from dependencies
            input_payload = self.dependency_service.get_node_input_payload(node_id)
            print(f"[+] Input payload for node {node_id}: {input_payload}")
            
            # Execute the node in the container
            result = self.execute_node_in_container(workflow_id, node_id, input_payload)
            
            if result and result.get("status") == "success":
                node_output = result.get("result", {})
                
                # Store result in database
                if self.store_node_output(node_id, node_output):
                    return {
                        "status": "success",
                        "node_id": node_id,
                        "result": node_output
                    }
                else:
                    return {
                        "status": "error",
                        "node_id": node_id,
                        "error": "Failed to store node output"
                    }
            else:
                error_msg = result.get("error", "Unknown error") if result else "No result from container"
                return {
                    "status": "error",
                    "node_id": node_id,
                    "error": error_msg
                }
                
        except Exception as e:
            print(f"[-] Error in node execution orchestration: {str(e)}")
            return {
                "status": "error",
                "node_id": node_id,
                "error": str(e)
            }
    
    def validate_node_execution(self, node_id: str) -> Dict[str, Any]:
        """
        Validate that a node can be executed (has required dependencies).
        Returns validation result.
        """
        try:
            node = Node.objects.get(id=node_id)
            validation = self.dependency_service.validate_dependency_chain(node)
            
            return {
                "node_id": node_id,
                "node_name": node.node_type.name if node.node_type else "Unknown",
                "can_execute": validation["is_valid"],
                "validation": validation
            }
        except Node.DoesNotExist:
            return {
                "node_id": node_id,
                "can_execute": False,
                "error": "Node not found"
            }
    
    def get_execution_summary(self, node_id: str) -> Dict[str, Any]:
        """
        Get a summary of node execution status and dependencies.
        """
        try:
            node = Node.objects.get(id=node_id)
            tree_info = self.dependency_service.get_dependency_tree_info(node)
            output = self.get_node_output(node_id)
            
            return {
                "node": {
                    "id": str(node.id),
                    "name": node.node_type.name if node.node_type else "Unknown",
                    "type": node.node_type.type if node.node_type else "unknown"
                },
                "dependencies": tree_info,
                "output": output,
                "has_output": bool(output)
            }
        except Node.DoesNotExist:
            return {
                "error": "Node not found"
            }


# Global instance for backward compatibility
node_execution_service = NodeExecutionService()
