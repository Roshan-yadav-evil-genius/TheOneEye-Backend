"""Page event coordination."""
import asyncio
from typing import Callable
from .page_manager import PageManager
from .websocket_message_sender import WebSocketMessageSender


class PageEventCoordinator:
    """Coordinates page lifecycle events and auto-switching."""
    
    def __init__(
        self,
        page_manager: PageManager,
        message_sender: WebSocketMessageSender
    ):
        """
        Initialize page event coordinator.
        
        Args:
            page_manager: PageManager instance for switching pages
            message_sender: WebSocketMessageSender instance
        """
        self.page_manager = page_manager
        self.message_sender = message_sender
    
    def create_page_added_callback(self) -> Callable[[str], None]:
        """
        Create a callback function for when pages are added.
        This callback will be called from sync contexts (Playwright event handlers).
        
        Returns:
            Synchronous callback function that schedules async operations
        """
        def page_added_callback(page_id: str):
            """Synchronous wrapper that schedules async operations for new pages."""
            try:
                loop = asyncio.get_running_loop()
                # Send page_added notification
                loop.create_task(self.message_sender.send_page_added(page_id))
                # Automatically switch to the new page
                loop.create_task(self.page_manager.switch_active_page(page_id))
            except RuntimeError:
                # If no event loop is running, create a new one (shouldn't happen)
                asyncio.create_task(self.message_sender.send_page_added(page_id))
                asyncio.create_task(self.page_manager.switch_active_page(page_id))
        
        return page_added_callback
    
    def create_page_removed_callback(self) -> Callable[[str], None]:
        """
        Create a callback function for when pages are removed.
        This callback will be called from sync contexts (Playwright event handlers).
        
        Returns:
            Synchronous callback function that schedules async operations
        """
        def page_removed_callback(page_id: str):
            """Synchronous wrapper that schedules async send_page_removed."""
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.message_sender.send_page_removed(page_id))
            except RuntimeError:
                # If no event loop is running, create a new one (shouldn't happen)
                asyncio.create_task(self.message_sender.send_page_removed(page_id))
        
        return page_removed_callback

