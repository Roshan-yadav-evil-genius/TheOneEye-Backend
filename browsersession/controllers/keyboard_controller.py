"""Keyboard control operations for browser."""
from playwright.async_api import Page
from typing import Optional, List, Dict
from ..mappers.key_mapper import KeyMapper


class KeyboardController:
    """Handles keyboard operations in the browser."""
    
    _VALID_MODIFIERS = {'Control', 'Alt', 'Shift', 'Meta'}
    
    def __init__(self, page: Optional[Page] = None):
        """
        Initialize keyboard controller.
        
        Args:
            page: Playwright Page instance (optional, can be set later)
        """
        self.page = page
        self._key_mapper = KeyMapper()
        # Track pending keydown events for printable characters to use press() on keyup
        self._pending_press: Dict[str, Dict] = {}
    
    def _ensure_page(self) -> None:
        """Ensure page is initialized."""
        if not self.page:
            raise RuntimeError("Browser page not initialized. Page must be set before using keyboard controller.")
    
    async def key_down(self, key: str, code: Optional[str] = None, modifiers: Optional[List[str]] = None) -> None:
        """
        Press a key in the browser.
        
        Args:
            key: JavaScript key value (preserves case, e.g., 'A' or 'a')
            code: JavaScript key code (optional)
            modifiers: List of modifier keys ['Control', 'Alt', 'Shift', 'Meta']
            
        Raises:
            Exception: If key press fails
        """
        self._ensure_page()
        
        # For printable characters, store info to use press() on keyup for proper case handling
        if len(key) == 1 and key.isprintable() and not (modifiers and any(m in ['Control', 'Alt', 'Meta'] for m in modifiers)):
            # Store for keyup to use press() which handles case correctly
            # Use code as the key identifier to match keydown with keyup
            key_id = code or key
            self._pending_press[key_id] = {
                'key': key,
                'code': code,
                'modifiers': modifiers
            }
            # Don't call down() here - we'll use press() on keyup to avoid double presses
            # This ensures proper case handling for Shift and Caps Lock
        else:
            # For special keys or with Control/Alt/Meta, use normal down/up
            playwright_key = self._key_mapper.map_key(key, code)
            
            # Handle modifiers
            if modifiers:
                # Press modifiers first
                for mod in modifiers:
                    if mod in self._VALID_MODIFIERS:
                        await self.page.keyboard.down(mod)
            
            # Press the main key
            await self.page.keyboard.down(playwright_key)
    
    async def key_up(self, key: str, code: Optional[str] = None, modifiers: Optional[List[str]] = None) -> None:
        """
        Release a key in the browser.
        
        Args:
            key: JavaScript key value (preserves case, e.g., 'A' or 'a')
            code: JavaScript key code (optional)
            modifiers: List of modifier keys ['Control', 'Alt', 'Shift', 'Meta']
            
        Raises:
            Exception: If key release fails
        """
        self._ensure_page()
        
        # Check if this is a pending press for a printable character
        key_id = code or key
        pending = self._pending_press.pop(key_id, None)
        
        if pending and len(key) == 1 and key.isprintable() and not (modifiers and any(m in ['Control', 'Alt', 'Meta'] for m in modifiers)):
            # Use keyboard.press() which handles case and modifiers correctly
            # This ensures proper handling of Shift and Caps Lock
            press_key = pending['key']
            # Use modifiers from keydown (stored in pending) rather than keyup
            # This ensures Shift state is captured correctly even if released before keyup
            effective_modifiers = list(pending.get('modifiers', [])) if pending.get('modifiers') else []
            
            if effective_modifiers:
                # For modifiers, use the format Playwright expects: "Shift+a" for Shift+A
                # Use lowercase physical key with modifiers
                mod_list = sorted(effective_modifiers)
                physical = press_key.lower() if press_key.isalpha() else press_key
                mod_str = '+'.join(mod_list)
                await self.page.keyboard.press(f"{mod_str}+{physical}")
            else:
                # No modifiers - use the actual key value (preserves case for Caps Lock)
                # Playwright's press() will type the exact character
                await self.page.keyboard.press(press_key)
        else:
            # For special keys or normal up, use standard up
            # For single character keys not in pending, use physical key
            if len(key) == 1 and key.isprintable():
                physical_key = key.lower() if key.isalpha() else key
                effective_modifiers = list(modifiers) if modifiers else []
                await self.page.keyboard.up(physical_key)
                for mod in effective_modifiers:
                    if mod in self._VALID_MODIFIERS:
                        await self.page.keyboard.up(mod)
            else:
                # For special keys, use the mapped key
                playwright_key = self._key_mapper.map_key(key, code)
                
                # Release the main key first
                await self.page.keyboard.up(playwright_key)
                
                # Release modifiers
                if modifiers:
                    for mod in modifiers:
                        if mod in self._VALID_MODIFIERS:
                            await self.page.keyboard.up(mod)
    
    async def type_text(self, text: str) -> None:
        """
        Type text in the browser.
        
        Args:
            text: Text to type
            
        Raises:
            Exception: If typing fails
        """
        self._ensure_page()
        await self.page.keyboard.type(text)

