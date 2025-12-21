from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple, Optional


class DependencyInjector(ABC):
    """
    Abstract mixin class that defines the interface for field dependency injection.
    
    Forms that need cascading field dependencies should inherit from this mixin
    and implement the two required abstract methods.
    """
    
    @abstractmethod
    def get_field_dependencies(self) -> Dict[str, List[str]]:
        """
        REQUIRED: Define field dependencies.
        
        Returns:
            dict: Mapping of parent_field -> [dependent_field1, dependent_field2, ...]
            Example: {'country': ['state'], 'state': ['language']}
        """
        pass
    
    @abstractmethod
    def populate_field(
        self, 
        field_name: str, 
        parent_value: Any, 
        form_values: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, str]]:
        """
        REQUIRED: Populate choices for a dependent field based on parent value.
        
        Args:
            field_name: Name of the dependent field to populate
            parent_value: Value of the immediate parent field
            form_values: All current form values for multi-parent access (optional)
            
        Returns:
            list: List of tuples (value, label) for the dependent field
            Example: [('maharashtra', 'Maharashtra'), ('karnataka', 'Karnataka')]
        """
        pass

