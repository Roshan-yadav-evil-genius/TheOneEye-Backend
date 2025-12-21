"""
Node execution service.

This module handles executing individual nodes and saving their results.
Follows Single Responsibility Principle - only handles node execution logic.
"""

from typing import Dict, Any, Optional
from ..models import Node


class NodeExecutionService:
    """Service for executing nodes and managing their input/output data."""
    
    @staticmethod
    def execute_node(
        node: Node,
        form_values: Dict[str, Any],
        input_data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a node with given form values and input data.
        
        Args:
            node: The Node model instance to execute
            form_values: Form field values for the node
            input_data: Input data from connected nodes
            session_id: Optional session ID for stateful execution
            
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
                return {
                    'success': False,
                    'error': f'Node type not found: {node.node_type}',
                    'error_type': 'NodeTypeNotFound',
                    'node_id': str(node.id),
                    'node_type': node.node_type,
                }
            
            # Execute the node with session support
            result = services.node_executor.execute(
                node_metadata, input_data, form_values, session_id
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
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': 'ExecutionError',
                'node_id': str(node.id),
                'node_type': node.node_type,
            }
    
    @staticmethod
    def get_node_for_execution(workflow_id: str, node_id: str) -> Optional[Node]:
        """
        Get a node instance for execution, verifying it belongs to the workflow.
        
        Args:
            workflow_id: The workflow UUID
            node_id: The node UUID
            
        Returns:
            Node instance if found, None otherwise
        """
        try:
            return Node.objects.get(id=node_id, workflow_id=workflow_id)
        except Node.DoesNotExist:
            return None


# Global instance for convenience
node_execution_service = NodeExecutionService()

