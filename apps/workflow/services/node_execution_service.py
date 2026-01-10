"""
Node execution service.

This module handles executing individual nodes and saving their results.
Follows Single Responsibility Principle - only handles node execution logic.
"""

from typing import Dict, Any, Optional
from apps.common.exceptions import ValidationError, NodeNotFoundError, NodeTypeNotFoundError, FormValidationException
from ..models import Node


class NodeExecutionService:
    """Service for executing nodes and managing their input/output data."""
    
    @staticmethod
    def execute_node(
        node: Node,
        form_values: Dict[str, Any],
        input_data: Dict[str, Any],
        session_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute a node with given form values and input data.
        
        Args:
            node: The Node model instance to execute
            form_values: Form field values for the node
            input_data: Input data from connected nodes
            session_id: Optional session ID for stateful execution
            timeout: Optional timeout in seconds (default: None, no timeout)
            
        Returns:
            Dict with execution result including success status, output, and any errors
        """
        # Save form_values and input_data before execution
        node.form_values = form_values
        node.input_data = input_data
        node.save()
        
        try:
            from apps.nodes.services import get_node_services
            services = get_node_services()
            
            # Find the node type metadata
            node_metadata = services.node_registry.find_by_identifier(node.node_type)
            
            if node_metadata is None:
                # Return error result instead of raising exception
                # This allows execute_node to be used in contexts where exceptions aren't desired
                return {
                    'success': False,
                    'error': f'Node type not found: {node.node_type}',
                    'error_type': 'NodeTypeNotFound',
                    'node_id': str(node.id),
                    'node_type': node.node_type,
                }
            
            # Execute the node with session support
            result = services.node_executor.execute(
                node_metadata, input_data, form_values, session_id, timeout
            )
            
            # Save output_data if execution was successful
            if result.get('success'):
                output = result.get('output', {})
                # Extract data from output if it's wrapped
                if isinstance(output, dict) and 'data' in output:
                    node.output_data = output.get('data', {})
                else:
                    node.output_data = output
                node.save()
            
            # Return the execution result
            return {
                'success': result.get('success', False),
                'node_id': str(node.id),
                'node_type': node.node_type,
                'input_data': input_data,
                'form_values': form_values,
                'output': result.get('output'),
                'error': result.get('error'),
                'error_type': result.get('error_type'),
                'message': result.get('message'),
                'form': result.get('form'),
                'session_id': session_id,
            }
            
        except FormValidationException as e:
            # Let FormValidationException propagate - it will be handled by DRF exception handler
            raise
        except Exception as e:
            # For other exceptions, still return error dict for backward compatibility
            # But in the future, these should also be raised as exceptions
            return {
                'success': False,
                'error': str(e),
                'error_type': 'ExecutionError',
                'node_id': str(node.id),
                'node_type': node.node_type,
            }
    
    @staticmethod
    def get_node_for_execution(workflow_id: str, node_id: str) -> Node:
        """
        Get a node instance for execution, verifying it belongs to the workflow.
        
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
    
    @staticmethod
    def execute_and_save_node(
        workflow_id: str,
        node_id: str,
        form_values: Dict[str, Any],
        input_data: Dict[str, Any],
        session_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow node and save all execution data.
        This method handles the full flow including validation.
        
        Args:
            workflow_id: The workflow UUID
            node_id: The node UUID
            form_values: Form field values for the node
            input_data: Input data from connected nodes
            session_id: Optional session ID for stateful execution
            timeout: Optional timeout in seconds (default: None, no timeout)
            
        Returns:
            Dict with execution result including success status, output, and any errors
            
        Raises:
            ValidationError: If node_id is not provided
            NodeNotFoundError: If node is not found in workflow
            NodeTypeNotFoundError: If node type is not found
        """
        # Validate node_id is provided
        if not node_id:
            raise ValidationError('node_id is required')
        
        # Get the node instance (raises NodeNotFoundError if not found)
        node = NodeExecutionService.get_node_for_execution(workflow_id, node_id)
        
        # Execute the node
        result = NodeExecutionService.execute_node(node, form_values, input_data, session_id, timeout)
        
        # Check if execution failed due to node type not found and raise exception
        if result.get('error_type') == 'NodeTypeNotFound':
            raise NodeTypeNotFoundError(node.node_type)
        
        return result


# Global instance for convenience
node_execution_service = NodeExecutionService()

