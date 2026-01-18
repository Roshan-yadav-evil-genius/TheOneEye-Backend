from jinja2 import Environment, StrictUndefined
from jinja2.exceptions import TemplateSyntaxError
from typing import Tuple, Optional
from .TemplateRenderer import TemplateRenderer

class jinja2TemplateRenderer(TemplateRenderer):
    def __init__(self):
        # Use StrictUndefined to raise errors for undefined variables
        self.env = Environment(undefined=StrictUndefined)

    def support(self, template: str) -> bool:
        """Check if string looks like a Jinja2 template (contains delimiters)."""
        if not isinstance(template, str):
            return False
        # Check for Jinja2 delimiters
        return "{{" in template or "{%" in template

    def render(self, template: str, data: dict) -> Tuple[str, Optional[str]]:
        """
        Render template with data.
        Returns: (rendered_value, error_message)
        - Success: (rendered_string, None)
        - Failure: (original_template, error_message)
        """
        try:
            tpl = self.env.from_string(template)
            return tpl.render(data=data), None
        except Exception as e:
            return template, str(e)