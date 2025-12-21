"""
Dependency Handler

Single Responsibility: Handle field dependency cascading in forms.
This class manages the initialization, update, and clearing of dependent fields.
"""

from typing import TYPE_CHECKING, Dict, List, Any, Optional

if TYPE_CHECKING:
    from .BaseForm import BaseForm


class DependencyHandler:
    """
    Handles field dependency cascading for forms.
    
    Single Responsibility: Manages dependent field operations only.
    - Initialize dependent fields based on parent values
    - Update dependent fields when parent values change
    - Clear dependent fields when parent values are reset
    
    This class does NOT handle:
    - Form validation
    - Field value storage
    - Form rebinding
    """
    
    def __init__(self, form: 'BaseForm'):
        """
        Initialize DependencyHandler with a form instance.
        
        Args:
            form: The BaseForm instance to manage dependencies for.
                  Must implement get_field_dependencies() and populate_field().
        """
        self._form = form
    
    def initialize_dependencies(self):
        """
        Initialize dependent fields based on parent field values.
        This method automatically handles cascading dependencies by processing
        fields in dependency order.
        
        Called once during form initialization to set up initial field choices
        based on any pre-populated parent field values.
        """
        dependencies = self._form.get_field_dependencies()
        
        # If no dependencies defined, nothing to initialize
        if not dependencies:
            return
        
        processed_fields: set = set()
        
        def process_field(field_name: str):
            """Recursively process field and its dependencies."""
            if field_name in processed_fields:
                return
            
            field_value = self._form.get_field_value(field_name)
            if field_value:
                # Update dependent fields
                self._update_dependent_field(field_name, field_value, dependencies)
            
            processed_fields.add(field_name)
            
            # Process dependent fields recursively
            if field_name in dependencies:
                for dependent_field in dependencies[field_name]:
                    process_field(dependent_field)
        
        # Start processing from all parent fields (fields that have dependencies)
        for parent_field in dependencies.keys():
            process_field(parent_field)
    
    def handle_field_change(self, field_name: str, value: Any):
        """
        Handle cascading updates when a parent field changes.
        
        This method:
        1. Clears all dependent fields (and their dependents, recursively)
        2. Updates dependent fields with new choices based on the new value
        
        Args:
            field_name: Name of the field that was updated
            value: New value of the field
        """
        dependencies = self._form.get_field_dependencies()
        
        # If no dependencies defined, nothing to handle
        if not dependencies:
            return
        
        if field_name in dependencies:
            # Clear dependent fields first
            self.clear_dependent_fields(field_name, dependencies)
            # Update dependent fields with new choices
            self._update_dependent_field(field_name, value, dependencies)
    
    def clear_dependent_fields(
        self, 
        parent_field: str, 
        dependencies: Optional[Dict[str, List[str]]] = None
    ):
        """
        Clear child fields when parent changes.
        Recursively clears all dependent fields in the dependency chain.
        
        Args:
            parent_field: Name of the parent field that changed
            dependencies: Optional dependencies dict. If None, fetches from form.
        """
        if dependencies is None:
            dependencies = self._form.get_field_dependencies()
        
        if parent_field in dependencies:
            for dependent_field in dependencies[parent_field]:
                # Clear the dependent field value from incremental data
                if hasattr(self._form, '_incremental_data'):
                    self._form._incremental_data.pop(dependent_field, None)
                
                # Reset choices to empty
                if dependent_field in self._form.fields:
                    self._form.fields[dependent_field].choices = []
                
                # Recursively clear fields that depend on this dependent field
                self.clear_dependent_fields(dependent_field, dependencies)
    
    def _update_dependent_field(
        self, 
        parent_field: str, 
        parent_value: Any, 
        dependencies: Optional[Dict[str, List[str]]] = None
    ):
        """
        Update a dependent field based on parent field value.
        
        Calls the form's populate_field() method to get choices for the
        dependent field based on the parent's value.
        
        Args:
            parent_field: Name of the parent field
            parent_value: Current value of the parent field
            dependencies: Optional dependencies dict. If None, fetches from form.
        """
        if dependencies is None:
            dependencies = self._form.get_field_dependencies()
        
        if parent_field in dependencies:
            for dependent_field in dependencies[parent_field]:
                # Get choices from the form's populate_field method
                choices = self._form.populate_field(dependent_field, parent_value)
                
                # Update the field's choices
                if dependent_field in self._form.fields:
                    self._form.fields[dependent_field].choices = choices

