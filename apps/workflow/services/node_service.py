"""
Node Service

Handles all node-related business logic, separated from views.
Single responsibility: Node CRUD operations and business logic.
"""

from typing import Dict, Any, Optional, Tuple
from django.core.exceptions import ValidationError
from apps.common.exceptions import ValidationError as APIValidationError, NodeNotFoundError
from ..models import Node, WorkFlow


class NodeService:
    """
    Service for handling node operations.
    Single responsibility: Node business logic.
    """
    
    @staticmethod
    def create_node(
        workflow: WorkFlow,
        node_type: str,
        position: Dict[str, float],
        form_values: Optional[Dict[str, Any]] = None
    ) -> Node:
        """
        Create a new node in a workflow.
        
        Args:
            workflow: The workflow instance
            node_type: The node type identifier
            position: Dictionary with 'x' and 'y' coordinates
            form_values: Optional form field values
            
        Returns:
            Node instance
            
        Raises:
            APIValidationError: If validation fails or creation fails
        """
        try:
            # Validate position
            x = position.get('x', 0)
            y = position.get('y', 0)
            
            # Create the node
            node = Node.objects.create(
                workflow=workflow,
                node_type=node_type,
                x=x,
                y=y,
                form_values=form_values or {}
            )
            
            return node
            
        except ValidationError as e:
            raise APIValidationError(f'Validation failed: {str(e)}', str(e))
        except Exception as e:
            raise APIValidationError(f'Failed to create node: {str(e)}', str(e))
    
    @staticmethod
    def update_node_position(
        node: Node,
        position: Dict[str, float]
    ) -> Node:
        """
        Update a node's position.
        
        Args:
            node: The node instance
            position: Dictionary with 'x' and 'y' coordinates
            
        Returns:
            Updated node instance
            
        Raises:
            APIValidationError: If update fails
        """
        try:
            # Update position
            if 'x' in position:
                node.x = position['x']
            if 'y' in position:
                node.y = position['y']
            
            node.save()
            return node
            
        except Exception as e:
            raise APIValidationError(f'Failed to update node position: {str(e)}', str(e))
    
    @staticmethod
    def delete_node(node: Node) -> None:
        """
        Delete a node from a workflow.
        
        Args:
            node: The node instance to delete
            
        Raises:
            APIValidationError: If deletion fails
        """
        try:
            node.delete()
        except Exception as e:
            raise APIValidationError(f'Failed to delete node: {str(e)}', str(e))
    
    @staticmethod
    def get_node_by_id(workflow_id: str, node_id: str) -> Node:
        """
        Get a node instance, verifying it belongs to the workflow.
        
        Args:
            workflow_id: The workflow UUID
            node_id: The node UUID
            
        Returns:
            Node instance
            
        Raises:
            NodeNotFoundError: If node is not found
        """
        try:
            return Node.objects.get(id=node_id, workflow_id=workflow_id)
        except Node.DoesNotExist:
            raise NodeNotFoundError(node_id, workflow_id)


# Global instance for convenience
node_service = NodeService()
