"""Message validation utilities."""
from typing import Dict, Any
import json


class MessageValidator:
    """Validates incoming WebSocket messages."""
    
    @staticmethod
    def validate_json(text_data: str) -> Dict[str, Any]:
        """
        Validate and parse JSON message.
        
        Args:
            text_data: Raw text data from WebSocket
            
        Returns:
            Parsed JSON dictionary
            
        Raises:
            json.JSONDecodeError: If JSON is invalid
        """
        return json.loads(text_data)
    
    @staticmethod
    def validate_message_type(data: Dict[str, Any]) -> str:
        """
        Validate and extract message type.
        
        Args:
            data: Parsed message data
            
        Returns:
            Message type string
            
        Raises:
            ValueError: If message type is missing
        """
        message_type = data.get('type')
        if not message_type:
            raise ValueError("Missing 'type' field in message")
        return message_type
    
    @staticmethod
    def validate_mouse_event(data: Dict[str, Any]) -> None:
        """
        Validate mouse event data.
        
        Args:
            data: Event data dictionary
            
        Raises:
            ValueError: If mouse event data is invalid
        """
        x = data.get('x')
        y = data.get('y')
        
        if x is None or y is None:
            raise ValueError("Mouse event missing coordinates")
        
        try:
            int(x)
            int(y)
        except (ValueError, TypeError):
            raise ValueError("Invalid coordinate values")
    
    @staticmethod
    def validate_keyboard_event(data: Dict[str, Any]) -> None:
        """
        Validate keyboard event data.
        
        Args:
            data: Event data dictionary
            
        Raises:
            ValueError: If keyboard event data is invalid
        """
        key = data.get('key')
        if not key:
            raise ValueError("Keyboard event missing 'key' field")

