"""Base event handler class."""
from abc import ABC, abstractmethod
from typing import Dict


class BaseEventHandler(ABC):
    """Base class for event handlers."""
    
    @abstractmethod
    async def handle(self, data: Dict) -> None:
        """
        Handle an event.
        
        Args:
            data: Event data dictionary
            
        Raises:
            Exception: If handling fails
        """
        pass

