"""Mouse control operations for browser."""
from playwright.async_api import Page
from typing import Optional
from ..mappers.button_mapper import ButtonMapper


class MouseController:
    """Handles mouse operations in the browser."""
    
    def __init__(self, page: Optional[Page] = None):
        """
        Initialize mouse controller.
        
        Args:
            page: Playwright Page instance (optional, can be set later)
        """
        self.page = page
        self._button_mapper = ButtonMapper()
    
    def _ensure_page(self) -> None:
        """Ensure page is initialized."""
        if not self.page:
            raise RuntimeError("Browser page not initialized. Page must be set before using mouse controller.")
    
    async def move(self, x: int, y: int) -> None:
        """
        Move mouse to specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Raises:
            Exception: If move fails
        """
        self._ensure_page()
        await self.page.mouse.move(x, y)
    
    async def click(self, x: int, y: int, button: str = 'left') -> None:
        """
        Click at specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            button: Button name ('left', 'right', 'middle')
            
        Raises:
            Exception: If click fails
        """
        self._ensure_page()
        playwright_button = self._button_mapper.map_button(button)
        await self.page.mouse.click(x, y, button=playwright_button)
    
    async def mouse_down(self, x: int, y: int, button: str = 'left') -> None:
        """
        Press mouse button at specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            button: Button name ('left', 'right', 'middle')
            
        Raises:
            Exception: If mouse down fails
        """
        self._ensure_page()
        playwright_button = self._button_mapper.map_button(button)
        await self.page.mouse.move(x, y)
        await self.page.mouse.down(button=playwright_button)
    
    async def mouse_up(self, x: int, y: int, button: str = 'left') -> None:
        """
        Release mouse button at specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            button: Button name ('left', 'right', 'middle')
            
        Raises:
            Exception: If mouse up fails
        """
        self._ensure_page()
        playwright_button = self._button_mapper.map_button(button)
        await self.page.mouse.move(x, y)
        await self.page.mouse.up(button=playwright_button)
    
    async def scroll(self, x: int, y: int, delta_x: float = 0, delta_y: float = 0) -> None:
        """
        Scroll at specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            delta_x: Horizontal scroll delta
            delta_y: Vertical scroll delta
            
        Raises:
            Exception: If scroll fails
        """
        self._ensure_page()
        await self.page.mouse.move(x, y)
        await self.page.mouse.wheel(delta_x, delta_y)

