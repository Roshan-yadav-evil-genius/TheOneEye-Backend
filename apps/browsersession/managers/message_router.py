"""Message routing for WebSocket messages."""
import structlog
from typing import Dict, Any, Optional, Callable, Awaitable
from ..event_handlers.mouse_handler import MouseHandler
from ..event_handlers.keyboard_handler import KeyboardHandler
from ..utils.validators import MessageValidator

logger = structlog.get_logger(__name__)


class MessageRouter:
    """Routes WebSocket messages to appropriate handlers."""
    
    def __init__(
        self,
        mouse_handler: Optional[MouseHandler] = None,
        keyboard_handler: Optional[KeyboardHandler] = None,
        start_callback: Optional[Callable[[], Awaitable[None]]] = None
    ):
        """
        Initialize message router.
        
        Args:
            mouse_handler: MouseHandler instance
            keyboard_handler: KeyboardHandler instance
            start_callback: Async callback for 'start' messages
        """
        self.mouse_handler = mouse_handler
        self.keyboard_handler = keyboard_handler
        self.start_callback = start_callback
        self.validator = MessageValidator()
    
    async def route(self, text_data: str) -> None:
        """
        Route a message to the appropriate handler.
        
        Args:
            text_data: Raw text data from WebSocket
            
        Raises:
            json.JSONDecodeError: If JSON is invalid
            ValueError: If message is invalid
        """
        # Parse and validate JSON
        data = self.validator.validate_json(text_data)
        message_type = self.validator.validate_message_type(data)
        
        # Route to appropriate handler
        if message_type == 'start':
            if self.start_callback:
                await self.start_callback()
        elif message_type in ['mousemove', 'mousedown', 'mouseup', 'wheel']:
            await self._route_mouse_event(message_type, data)
        elif message_type in ['keydown', 'keyup']:
            await self._route_keyboard_event(message_type, data)
        else:
            logger.warning("Unknown message type", message_type=message_type)
    
    async def _route_mouse_event(self, message_type: str, data: Dict[str, Any]) -> None:
        """
        Route mouse event to mouse handler.
        
        Args:
            message_type: Type of mouse event
            data: Event data dictionary
        """
        if not self.mouse_handler:
            return
        
        self.validator.validate_mouse_event(data)
        
        handler_map = {
            'mousemove': self.mouse_handler.handle_mousemove,
            'mousedown': self.mouse_handler.handle_mousedown,
            'mouseup': self.mouse_handler.handle_mouseup,
            'wheel': self.mouse_handler.handle_wheel,
        }
        
        handler = handler_map.get(message_type)
        if handler:
            await handler(data)
    
    async def _route_keyboard_event(self, message_type: str, data: Dict[str, Any]) -> None:
        """
        Route keyboard event to keyboard handler.
        
        Args:
            message_type: Type of keyboard event
            data: Event data dictionary
        """
        if not self.keyboard_handler:
            return
        
        self.validator.validate_keyboard_event(data)
        
        handler_map = {
            'keydown': self.keyboard_handler.handle_keydown,
            'keyup': self.keyboard_handler.handle_keyup,
        }
        
        handler = handler_map.get(message_type)
        if handler:
            await handler(data)

