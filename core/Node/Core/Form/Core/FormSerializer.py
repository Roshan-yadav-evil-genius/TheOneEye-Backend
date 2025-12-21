"""
Field Parser Module

This module provides utilities for parsing Django form fields into JSON structures.
Each function follows the Single Responsibility Principle.
"""

from bs4 import BeautifulSoup
from typing import Any, Dict, List, Optional


class FormSerializer:
    """
    Serializes Django form instances to JSON representation.
    Each method follows the Single Responsibility Principle.
    """
    
    def __init__(self, form):
        """
        Initialize FormSerializer with a Django form instance.
        
        Args:
            form: Django form instance to serialize
        """
        self.form = form
    
    def _normalize_attribute_value(self, attr_value: Any) -> Any:
        """
        Normalize HTML attribute values to appropriate Python types.
        Single responsibility: Convert attribute values to appropriate types.
        
        Converts:
        - Lists to strings (space-separated) or single values
        - Empty/None values to True (boolean attributes)
        - Numeric strings to int or float
        - Other values remain as-is
        
        Args:
            attr_value: The raw attribute value from HTML parsing
            
        Returns:
            Normalized value (int, float, bool, str, or list)
        """
        if isinstance(attr_value, list):
            if len(attr_value) > 1:
                return ' '.join(attr_value)
            elif len(attr_value) == 1:
                return attr_value[0]
            else:
                return True
        elif attr_value is None or attr_value == '':
            return True
        elif isinstance(attr_value, str):
            if attr_value.isdigit():
                return int(attr_value)
            elif attr_value.replace('.', '', 1).replace('-', '', 1).isdigit():
                return float(attr_value)
        return attr_value
    
    def _extract_select_options(self, select_tag: Any) -> List[Dict[str, Any]]:
        """
        Extract option elements from a select tag.
        Single responsibility: Extract options from select elements.
        
        Args:
            select_tag: BeautifulSoup Tag object representing a select element
            
        Returns:
            List of dictionaries, each containing:
            - 'value': The option's value attribute
            - 'text': The option's display text
            - 'selected': True if the option is selected (optional)
        """
        options = []
        for option in select_tag.find_all('option'):
            option_data = {
                'value': option.get('value', ''),
                'text': option.get_text(strip=True)
            }
            if option.get('selected'):
                option_data['selected'] = True
            options.append(option_data)
        return options
    
    def _extract_tag_attributes(self, tag: Any) -> Dict[str, Any]:
        """
        Extract and normalize all attributes from an HTML tag.
        Single responsibility: Extract and normalize tag attributes.
        
        Args:
            tag: BeautifulSoup Tag object
            
        Returns:
            Dictionary of normalized attribute name-value pairs
        """
        attributes = {}
        for attr_name, attr_value in tag.attrs.items():
            attributes[attr_name] = self._normalize_attribute_value(attr_value)
        return attributes
    
    def _serialize_field(self, field: Any) -> Dict[str, Any]:
        """
        Serialize a single form field to JSON.
        Single responsibility: Convert a form field to JSON dictionary.
        
        Extracts:
        - Tag name (input, select, textarea, etc.)
        - Field label
        - Field errors
        - All HTML attributes (normalized)
        - Current field value
        - Options (for select elements)
        
        Args:
            field: Django form field (BoundField instance)
            
        Returns:
            Dictionary containing parsed field information
        """
        soup = BeautifulSoup(str(field), 'html.parser')
        tag = soup.find()
        
        if not tag:
            return {}
        
        result = {
            'tag': tag.name,
            'label': str(field.label) if field.label else '',
            'errors': list(field.errors) if field.errors else []
        }
        
        # Extract and normalize tag attributes
        attributes = self._extract_tag_attributes(tag)
        result.update(attributes)
        
        # Extract current field value
        field_value = field.value()
        if field_value is not None:
            result['value'] = field_value
        
        # Handle select elements - always include options (even if empty)
        if tag.name == 'select':
            options = self._extract_select_options(tag)
            result['options'] = options
        
        return result
    
    def _get_non_field_errors(self) -> List[str]:
        """
        Extract non-field (global) errors from the form.
        Single responsibility: Retrieve form-level errors not associated with specific fields.
        
        Returns:
            List of error message strings
        """
        # Django stores non-field errors in form.non_field_errors() or form.errors.get('__all__', [])
        non_field_errors = self.form.non_field_errors()
        return list(non_field_errors) if non_field_errors else []
    
    def _get_dependencies(self) -> Optional[Dict[str, List[str]]]:
        """
        Get field dependencies from the form if available.
        Single responsibility: Retrieve dependency configuration.
        
        Returns:
            Dictionary mapping parent fields to dependent fields, or None.
        """
        if hasattr(self.form, 'get_field_dependencies'):
            deps = self.form.get_field_dependencies()
            if deps:
                return deps
        return None
    
    def to_json(self) -> Dict[str, Any]:
        """
        Serialize entire form to JSON.
        Single responsibility: Convert form to JSON structure with fields and global errors.
        
        Returns:
            Dictionary containing:
            - 'fields': List of field JSON objects
            - 'dependencies': Dict of field dependencies (if any)
            - 'non_field_errors': List of global error messages (if any)
        """
        form_state = {
            'fields': []
        }
        
        # Serialize all fields
        for field in self.form:
            field_json = self._serialize_field(field)
            form_state['fields'].append(field_json)
        
        # Add field dependencies if they exist
        dependencies = self._get_dependencies()
        if dependencies:
            form_state['dependencies'] = dependencies
        
        # Add non-field errors if they exist
        non_field_errors = self._get_non_field_errors()
        if non_field_errors:
            form_state['non_field_errors'] = non_field_errors
        
        return form_state