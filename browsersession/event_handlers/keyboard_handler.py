"""Keyboard event handler."""
from typing import Dict, List, Optional
from .base_handler import BaseEventHandler
from ..controllers.keyboard_controller import KeyboardController


class KeyboardHandler(BaseEventHandler):
    """Handles keyboard events."""
    
    _MODIFIER_KEYS = {'Control', 'Alt', 'Shift', 'Meta'}
    
    def __init__(self, keyboard_controller: Optional[KeyboardController] = None):
        """
        Initialize keyboard handler.
        
        Args:
            keyboard_controller: KeyboardController instance
        """
        self.keyboard_controller = keyboard_controller
    
    def _extract_modifiers(self, data: Dict) -> List[str]:
        """
        Extract modifier keys from event data.
        
        Args:
            data: Event data dictionary
            
        Returns:
            List of modifier key names
        """
        modifiers = []
        if data.get('ctrlKey', False):
            modifiers.append('Control')
        if data.get('altKey', False):
            modifiers.append('Alt')
        if data.get('shiftKey', False):
            modifiers.append('Shift')
        if data.get('metaKey', False):
            modifiers.append('Meta')
        return modifiers
    
    def _validate_key(self, data: Dict) -> tuple:
        """
        Validate and extract key information from event data.
        
        Args:
            data: Event data dictionary
            
        Returns:
            Tuple of (key, code)
            
        Raises:
            ValueError: If key is missing
        """
        key = data.get('key')
        if not key:
            raise ValueError("Missing key in event data")
        
        code = data.get('code')
        return key, code
    
    async def handle_keydown(self, data: Dict) -> None:
        """Handle key down events."""
        if not self.keyboard_controller:
            return
        
        key, code = self._validate_key(data)
        repeat = data.get('repeat', False)
        
        # Skip if this is a repeat event for modifier keys (to avoid spam)
        if repeat and key in self._MODIFIER_KEYS:
            return
        
        modifiers = self._extract_modifiers(data)
        await self.keyboard_controller.key_down(
            key, 
            code, 
            modifiers if modifiers else None
        )
    
    async def handle_keyup(self, data: Dict) -> None:
        """Handle key up events."""
        if not self.keyboard_controller:
            return
        
        key, code = self._validate_key(data)
        modifiers = self._extract_modifiers(data)
        await self.keyboard_controller.key_up(
            key, 
            code, 
            modifiers if modifiers else None
        )
    
    async def handle(self, data: Dict) -> None:
        """Handle keyboard event (base implementation)."""
        # This is a placeholder - specific handlers should override
        pass

