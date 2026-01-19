from django.forms import Form
from .DependencyFormMetaClass import DependencyFormMetaClass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .SchemaBuilder import FormSchemaBuilder


class BaseForm(Form, metaclass=DependencyFormMetaClass):
    """
    In short: BaseForm is a Django form with added dependency tracking and resolution. 
    Form provides the base form functionality, and the metaclass and _field_values add dependency management.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._field_values = {}
        # You need _field_values because Django forms have two states and you need to track values before binding/validation.

    def get_unbound_field_values(self):
        return self._field_values

    def get_field_value(self, field_name):
        """
        Get the value of a specific field.
        
        Args:
            field_name: Name of the field to get value for.
            
        Returns:
            The field value, or None if not set.
        """
        return self._field_values.get(field_name)

    # ==================== Field Value Management Methods ====================

    def _set_field_value(self, field_name, value):
        """Set a field's value in both _field_values and field's initial."""
        self._field_values[field_name] = value


    def _set_multiple_field_values(self, field_data):
        """Set multiple field values at once."""
        for field_name, value in field_data.items():
            self._set_field_value(field_name, value)
        return set(field_data.keys())

    # ==================== Dependency Checking Methods ====================

    def _are_dependencies_satisfied(self, field_name):
        """Check if all dependencies for a field have values."""
        dependencies = self._field_dependencies.get(field_name, {}).get("dependent_on", [])
        return all(dep in self._field_values for dep in dependencies)

    def _get_dependency_values(self, field_name):
        """Extract dependency values for a field in order."""
        dependencies = self._field_dependencies.get(field_name, {}).get("dependent_on", [])
        return [self._field_values[dep] for dep in dependencies]

    def _should_skip_loader(self, dep_field, provided_fields):
        """Determine if loader should be skipped for a dependent field."""
        if provided_fields is None:
            return False
        return dep_field in provided_fields

    # ==================== Loader Management Methods ====================

    def _call_field_loader(self, dep_field, meta):
        """Call the loader function for a dependent field."""
        loader = meta["loader"]
        return loader(self)

    def _populate_field_choices(self, dep_field, choices, provided_fields=None):
        """Set choices for a field, auto-select if single choice, and update dependents."""
        # Clear stale value unless user just provided it in this update
        if dep_field not in (provided_fields or set()):
            self._field_values.pop(dep_field, None)
        
        self.fields[dep_field].choices = choices
        
        # Auto-select if exactly one choice and not user-provided
        if len(choices) == 1 and dep_field not in (provided_fields or set()):
            self._set_field_value(dep_field, choices[0][0])
        
        self._update_dependents(dep_field, provided_fields=provided_fields)

    def _clear_dependent_field(self, dep_field):
        """Clear choices AND value when dependencies not met."""
        self.fields[dep_field].choices = []
        self._field_values.pop(dep_field, None)

    def _load_all_choices(self):
        """Load choices for ALL dependent fields without modifying values.
        Called before validation to ensure choices are available.
        
        If a field has a configured value not in loaded choices, adds it
        as a valid choice (handles shared resources not returned by list APIs).
        """
        for dep_field, meta in self._field_dependencies.items():
            if self._are_dependencies_satisfied(dep_field):
                choices = self._call_field_loader(dep_field, meta)
                
                # Preserve configured values not in loaded choices
                current_value = self._field_values.get(dep_field)
                if current_value:
                    choice_values = [c[0] for c in choices]
                    if current_value not in choice_values:
                        choices = list(choices) + [(current_value, f"{current_value} (configured)")]
                
                self.fields[dep_field].choices = choices

    # ==================== Update Methods ====================

    def update_fields(self, field_data):
        """
        Update multiple fields at once (public method).
        If a dependent field already has a value in field_data, skip its loader.
        Only call loaders for fields that don't have values yet.
        
        Args:
            field_data: dict of {field_name: value}
        """
        # Set all provided field values
        provided_fields = self._set_multiple_field_values(field_data)
        
        # Update dependents for all changed fields with smart loader logic
        for field_name in provided_fields:
            self._update_dependents(field_name, provided_fields=provided_fields)

    def validate_form(self):
        """
        Bind the form with current _field_values and validate.
        Returns True if form is valid, False otherwise.
        """
        # 1. Load all choices for dependent fields (for validation)
        self._load_all_choices()
        
        # 2. Create bound form for validation
        bound_form = self.__class__(data=self._field_values.copy())
        
        # 3. Copy loaded choices to bound form (new instance has empty defaults)
        for field_name, field in self.fields.items():
            if hasattr(field, 'choices'):
                bound_form.fields[field_name].choices = field.choices
        
        # 4. Validate and copy errors back
        is_valid = bound_form.is_valid()
        if hasattr(bound_form, '_errors'):
            self._errors = bound_form._errors
        if hasattr(bound_form, 'data'):
            self.data = bound_form.data
        # Copy cleaned_data for nodes that access it
        if hasattr(bound_form, 'cleaned_data'):
            self.cleaned_data = bound_form.cleaned_data
        
        return is_valid

    def _update_dependents(self, field_name, provided_fields=None):
        """
        Recursively update dependent fields with smart loader skipping.
        
        Args:
            field_name: Field that was updated
            provided_fields: Set of fields with user-provided values (None = always load)
        """
        for dep_field, meta in self._field_dependencies.items():
            if field_name not in meta["dependent_on"]:
                continue

            if self._are_dependencies_satisfied(dep_field):
                # Dependencies satisfied - check if we should skip loader
                if self._should_skip_loader(dep_field, provided_fields):
                    # User provided value, skip loader, just recurse to update dependents
                    self._update_dependents(dep_field, provided_fields=provided_fields)
                else:
                    # Need to call loader
                    choices = self._call_field_loader(dep_field, meta)
                    self._populate_field_choices(dep_field, choices, provided_fields=provided_fields)
            else:
                # Dependencies not met, clear choices AND value, then recurse for full cascade
                self._clear_dependent_field(dep_field)
                self._update_dependents(dep_field, provided_fields=provided_fields)

    # ==================== Schema Generation ====================

    def get_form_schema(self, builder: "FormSchemaBuilder" = None) -> dict:
        """
        Returns comprehensive form schema with all details needed for frontend rendering.
        Includes field metadata, widget information, validation rules, dependencies, and state.
        
        Args:
            builder: Optional custom schema builder. Uses DefaultFormSchemaBuilder if not provided.
            
        Returns:
            dict: The generated form schema
        """
        if builder is None:
            from .SchemaBuilder import DefaultFormSchemaBuilder
            builder = DefaultFormSchemaBuilder()
        return builder.build(self)
