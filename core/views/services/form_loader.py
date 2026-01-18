"""
Form Loader Module
Loads and serializes node forms.
"""

import traceback
from typing import Dict, List, Optional
import structlog

from .node_loader import NodeLoader

logger = structlog.get_logger(__name__)


class FormLoader:
    """
    Loads and serializes node forms.
    
    Responsibilities:
    - Create node instances to get forms
    - Serialize forms to JSON
    """
    
    def __init__(self, node_loader: NodeLoader):
        """
        Initialize FormLoader.
        
        Args:
            node_loader: NodeLoader for loading node classes.
        """
        self._node_loader = node_loader
    
    def load_form(self, node_metadata: Dict) -> Optional[Dict]:
        """
        Load and serialize the form from a node.
        
        Args:
            node_metadata: Node metadata dict.
            
        Returns:
            Serialized form JSON or None if no form.
        """
        if not node_metadata.get('has_form'):
            return None
        
        try:
            node_class = self._node_loader.load_class(node_metadata)
            if node_class is None:
                return None
            
            # Check if the class has get_form method
            if not hasattr(node_class, 'get_form'):
                return None
            
            # Create a dummy instance to call get_form
            instance = self._create_dummy_instance(node_class, node_metadata)
            form = instance.get_form()
            
            if form is None:
                return None
            
            # Serialize the form
            serialized = self._serialize_form(form)
            return serialized
            
        except Exception as e:
            print(f"Error loading form: {e}")
            traceback.print_exc()
            return None
    
    def _create_dummy_instance(self, node_class, node_metadata: Dict):
        """
        Create a dummy node instance for form extraction.
        """
        from Node.Core.Node.Core.Data import NodeConfig, NodeConfigData
        
        dummy_config = NodeConfig(
            id="temp",
            type=node_metadata.get('identifier', 'unknown'),
            data=NodeConfigData(form={})
        )
        
        return node_class(dummy_config)
    
    def _serialize_form(self, form) -> Dict:
        """
        Serialize a form instance to JSON.
        """
        return form.get_form_schema()
    
    def get_field_options(
        self, 
        node_metadata: Dict, 
        field_name: str, 
        parent_value: str,
        form_values: Dict = None
    ) -> List:
        """
        Get options for a dependent field based on parent value.
        
        Args:
            node_metadata: Node metadata dict.
            field_name: Name of the dependent field.
            parent_value: Value of the parent field.
            form_values: All current form values for multi-parent access.
            
        Returns:
            List of (value, text) tuples for the field options.
        """
        form_values = form_values or {}
        
        try:
            node_class = self._node_loader.load_class(node_metadata)
            if node_class is None:
                return []
            
            # Check if the class has get_form method
            if not hasattr(node_class, 'get_form'):
                return []
            
            # Create a dummy instance to get the form
            instance = self._create_dummy_instance(node_class, node_metadata)
            form = instance.get_form()
            
            if form is None:
                return []
            
            # Populate form with current values - this triggers loaders for dependent fields
            if form_values:
                form.update_fields(form_values)
            
            # Get the field's choices after update_fields triggered the loaders
            field = form.fields.get(field_name)
            if field is None:
                return []
            
            # Return choices from the field
            if hasattr(field, 'choices'):
                return list(field.choices)
            
            return []
            
        except Exception as e:
            # Let exceptions propagate - they will be caught by DRF exception handler
            # This allows ValidationError and other exceptions to be properly handled
            # Log the error for debugging, but let it propagate
            logger.error(
                "Error getting field options",
                field_name=field_name,
                parent_value=parent_value,
                error=str(e)
            )
            raise

    def update_form(self, node_metadata: Dict, field_values: Dict = None) -> Optional[Dict]:
        """
        Update form with field values and return serialized form.
        
        Args:
            node_metadata: Node metadata dict.
            field_values: Dict of field values to update.
            
        Returns:
            Serialized form JSON or None if no form.
        """
        field_values = field_values or {}
        
        try:
            node_class = self._node_loader.load_class(node_metadata)
            if node_class is None:
                return None
            
            # Check if the class has get_form method
            if not hasattr(node_class, 'get_form'):
                return None
            
            # Create a dummy instance to get the form
            instance = self._create_dummy_instance(node_class, node_metadata)
            form = instance.get_form()
            
            if form is None:
                return None
            
            # Update form with provided values - this triggers loaders for dependent fields
            if field_values:
                form.update_fields(field_values)
            
            # Return serialized form with updated state
            return self._serialize_form(form)
            
        except Exception as e:
            logger.error(
                "Error updating form",
                field_values=field_values,
                error=str(e)
            )
            raise
