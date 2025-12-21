"""Mouse event handler."""
from typing import Dict, Optional
from .base_handler import BaseEventHandler
from ..controllers.mouse_controller import MouseController


class MouseHandler(BaseEventHandler):
    """Handles mouse events."""
    
    def __init__(self, mouse_controller: Optional[MouseController] = None):
        """
        Initialize mouse handler.
        
        Args:
            mouse_controller: MouseController instance
        """
        self.mouse_controller = mouse_controller
    
    def _validate_coordinates(self, data: Dict) -> tuple:
        """
        Validate and extract coordinates from event data.
        
        Args:
            data: Event data dictionary
            
        Returns:
            Tuple of (x, y) coordinates
            
        Raises:
            ValueError: If coordinates are invalid
        """
        x = data.get('x')
        y = data.get('y')
        
        if x is None or y is None:
            raise ValueError("Missing coordinates in event data")
        
        return int(x), int(y)
    
    async def handle_mousemove(self, data: Dict) -> None:
        """Handle mouse movement events."""
        if not self.mouse_controller:
            return
        
        x, y = self._validate_coordinates(data)
        await self.mouse_controller.move(x, y)
    
    async def handle_mousedown(self, data: Dict) -> None:
        """Handle mouse down events."""
        if not self.mouse_controller:
            return
        
        x, y = self._validate_coordinates(data)
        button = data.get('button', 'left')
        await self.mouse_controller.mouse_down(x, y, button)
    
    async def handle_mouseup(self, data: Dict) -> None:
        """Handle mouse up events."""
        if not self.mouse_controller:
            return
        
        x, y = self._validate_coordinates(data)
        button = data.get('button', 'left')
        await self.mouse_controller.mouse_up(x, y, button)
    
    async def handle_wheel(self, data: Dict) -> None:
        """Handle wheel/scroll events."""
        if not self.mouse_controller:
            return
        
        x, y = self._validate_coordinates(data)
        delta_x = data.get('deltaX', 0)
        delta_y = data.get('deltaY', 0)
        await self.mouse_controller.scroll(x, y, delta_x, delta_y)
    
    async def handle(self, data: Dict) -> None:
        """Handle mouse event (base implementation)."""
        # This is a placeholder - specific handlers should override
        pass

