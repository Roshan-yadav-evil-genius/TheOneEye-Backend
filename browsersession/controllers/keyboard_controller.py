"""Keyboard control operations for browser."""
from playwright.async_api import Page
from typing import Optional, List
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
    
    def _ensure_page(self) -> None:
        """Ensure page is initialized."""
        if not self.page:
            raise RuntimeError("Browser page not initialized. Page must be set before using keyboard controller.")
    
    async def key_down(self, key: str, code: Optional[str] = None, modifiers: Optional[List[str]] = None) -> None:
        """
        Press a key in the browser.
        
        Args:
            key: JavaScript key value
            code: JavaScript key code (optional)
            modifiers: List of modifier keys ['Control', 'Alt', 'Shift', 'Meta']
            
        Raises:
            Exception: If key press fails
        """
        self._ensure_page()
        
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
            key: JavaScript key value
            code: JavaScript key code (optional)
            modifiers: List of modifier keys ['Control', 'Alt', 'Shift', 'Meta']
            
        Raises:
            Exception: If key release fails
        """
        self._ensure_page()
        
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

