from abc import ABC, abstractmethod
from typing import Tuple, Optional

class TemplateRenderer(ABC):
    """Interface for template rendering only"""
    @abstractmethod
    def support(self, value: str) -> bool: ...

    @abstractmethod
    def render(self, template: str, data: dict) -> Tuple[str, Optional[str]]:
        """
        Render template with data.
        Returns: (rendered_value, error_message)
        - Success: (rendered_string, None)
        - Failure: (original_template, error_message)
        """
        ...
