from typing import Dict, Tuple, Optional
from ..Core.BaseForm import BaseForm
from .TemplateRenderer import TemplateRenderer


class FormTemplateProcessor:
    def __init__(self, renderer: TemplateRenderer):
        self.renderer = renderer
        self.errors: Dict[str, str] = {}

    def process(self, template: str, data: dict) -> Tuple[str, Optional[str]]:
        """
        Process a single template string.
        Returns: (rendered_value, error_message)
        """
        if not isinstance(template, str):
            return template, None
        
        if self.renderer.support(template):
            return self.renderer.render(template, data)
        
        return template, None
    
    def process_form(self, form: BaseForm, data: dict) -> Dict[str, str]:
        """
        Process all form field values through template rendering.
        Returns: dict of {field_name: error_message} for fields with errors
        """
        self.errors = {}  # Reset errors
        processed_values = {}
        
        for field_name, value in form.get_unbound_field_values().items():
            if isinstance(value, str) and self.renderer.support(value):
                rendered_value, error = self.renderer.render(value, data)
                processed_values[field_name] = rendered_value
                if error:
                    self.errors[field_name] = error
            else:
                processed_values[field_name] = value
        
        if processed_values:
            form.update_fields(processed_values)
        
        return self.errors