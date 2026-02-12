"""
Schema builder classes for generating form schemas.

Following SOLID principles:
- SRP: Schema generation is separated from form logic
- OCP: New schema formats can be added without modifying BaseForm
- DIP: BaseForm depends on FormSchemaBuilder abstraction
"""
import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .BaseForm import BaseForm


class FormSchemaBuilder(ABC):
    """
    Abstract interface for building form schemas.
    
    Implement this interface to create custom schema formats
    (e.g., OpenAPI, GraphQL, etc.)
    """
    
    @abstractmethod
    def build(self, form: "BaseForm") -> dict:
        """
        Build and return the schema for the form.
        
        Args:
            form: The BaseForm instance to generate schema for
            
        Returns:
            dict: The generated schema
        """
        ...


class DefaultFormSchemaBuilder(FormSchemaBuilder):
    """
    Default JSON schema builder for forms.
    
    Generates a comprehensive schema with:
    - Form metadata (name, field order, dependencies graph)
    - Field metadata (name, label, help_text, value, etc.)
    - Widget information
    - Dependency status
    - Validation errors
    """
    
    def build(self, form: "BaseForm") -> dict:
        """Build complete form schema."""
        schema = self._build_base_structure(form)
        
        # Build schema for each field
        for field_name, field in form.fields.items():
            field_schema = self._build_field_schema(form, field_name, field)
            schema["fields"].append(field_schema)
        
        # Add form-level errors if any
        schema["form_level_errors"] = self._extract_form_errors(form)
        
        return schema
    
    def _build_base_structure(self, form: "BaseForm") -> dict:
        """Build the base schema structure with form metadata."""
        return {
            "form_name": form.__class__.__name__,
            "fields": [],
            "field_order": list(form.fields.keys()),
            "dependencies_graph": {
                name: meta.get("dependent_on", [])
                for name, meta in form._field_dependencies.items()
            }
        }
    
    def _build_field_schema(self, form: "BaseForm", field_name: str, field) -> dict:
        """Build complete schema for a single field."""
        field_schema = {}
        
        # Add basic metadata
        field_schema.update(self._extract_field_metadata(form, field_name, field))
        
        # Add dependency information
        field_schema.update(self._extract_dependency_info(form, field_name))
        
        # Add widget information
        field_schema["widget"] = self._extract_widget_info(field)
        
        # Add errors if any
        field_schema["field_level_errors"] = self._extract_field_errors(form, field_name)
        
        return field_schema
    
    def _is_field_ready(self, form: "BaseForm", field_name: str) -> bool:
        """Check if all dependencies for a field are satisfied."""
        dependencies = form._field_dependencies.get(field_name, {}).get("dependent_on", [])
        return all(dep in form._field_values for dep in dependencies)
    
    def _extract_field_metadata(self, form: "BaseForm", field_name: str, field) -> dict:
        """Extract basic metadata for a field."""
        is_ready = self._is_field_ready(form, field_name)
        
        return {
            "name": field_name,
            "label": field.label or field_name.title(),
            "help_text": field.help_text or None,
            "disabled": getattr(field, 'disabled', False) or not is_ready,
            "initial": field.initial if not callable(field.initial) else None,
            "value": getattr(form, '_original_field_values', form._field_values).get(field_name),
        }
    
    def _extract_dependency_info(self, form: "BaseForm", field_name: str) -> dict:
        """Extract dependency information for a field."""
        dependencies = form._field_dependencies.get(field_name, {}).get("dependent_on", [])
        dependency_status = {
            dep: dep in form._field_values 
            for dep in dependencies
        }
        ready = self._is_field_ready(form, field_name)
        
        return {
            "dependencies": dependencies,
            "dependency_status": dependency_status,
            "ready": ready
        }
    
    def _extract_widget_info(self, field) -> dict:
        """Extract widget information for a field. Only includes JSON-serializable values."""
        if hasattr(field.widget, 'input_type'):
            input_type = field.widget.input_type
        else:
            input_type = None

        out = {"input_type": input_type}
        for key, value in field.widget.__dict__.items():
            if callable(value):
                continue
            try:
                json.dumps(value)
            except (TypeError, ValueError):
                continue
            out[key] = value
        return out
    
    def _extract_field_errors(self, form: "BaseForm", field_name: str) -> list:
        """Extract validation errors for a field if form is bound."""
        if hasattr(form, 'errors') and field_name in form.errors:
            error_list = form.errors[field_name]
            return [str(error) for error in error_list]
        return []
    
    def _extract_form_errors(self, form: "BaseForm") -> list:
        """Extract form-level validation errors if any."""
        if hasattr(form, 'errors') and form.errors:
            non_field_errors = form.errors.get('__all__', [])
            if non_field_errors:
                return [str(error) for error in non_field_errors]
        return []
