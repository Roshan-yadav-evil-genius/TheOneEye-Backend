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
        from Node.Core.Form.Core.FormSerializer import FormSerializer
        
        serializer = FormSerializer(form)
        return serializer.to_json()
    
    async def get_field_options(
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
        import asyncio
        import inspect
        
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
            
            # Check if form has populate_field method
            if not hasattr(form, 'populate_field'):
                return []
            
            # Populate form with current values for multi-parent access
            if form_values and hasattr(form, 'update_field'):
                for key, value in form_values.items():
                    form.update_field(key, value)
            
            # Get options from the form's populate_field method
            # Handle both sync and async populate_field methods
            populate_method = form.populate_field
            if inspect.iscoroutinefunction(populate_method):
                options = await populate_method(field_name, parent_value, form_values)
            else:
                options = populate_method(field_name, parent_value, form_values)
            
            return options if options else []
            
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

