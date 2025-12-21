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
        
        When the active page closes (e.g., a popup after authentication),
        automatically switches to another available page to prevent streaming errors.
        
        Returns:
            Synchronous callback function that schedules async operations
        """
        def page_removed_callback(page_id: str):
            """Synchronous wrapper that schedules async operations for closed pages."""
            try:
                loop = asyncio.get_running_loop()
                # Send page_removed notification
                loop.create_task(self.message_sender.send_page_removed(page_id))
                # Handle switching to another page if the active page was closed
                loop.create_task(self._handle_page_closed(page_id))
            except RuntimeError:
                # If no event loop is running, create a new one (shouldn't happen)
                asyncio.create_task(self.message_sender.send_page_removed(page_id))
                asyncio.create_task(self._handle_page_closed(page_id))
        
        return page_removed_callback
    
    async def _handle_page_closed(self, closed_page_id: str) -> None:
        """
        Switch to another page if the active page was closed.
        
        This prevents streaming errors when popups (like Google Sign-In) close
        automatically after user interaction.
        
        Args:
            closed_page_id: UUID of the page that was closed
        """
        # Get current active page
        current_page = self.page_manager.browser_manager.page
        if not current_page:
            # No active page, nothing to switch from
            return
        
        # Get the ID of the current active page
        current_page_id = self.page_manager.browser_manager.get_page_id(current_page)
        
        # Check if the closed page was the active page
        # Also handle case where current_page_id is None (page already removed from tracking)
        if current_page_id == closed_page_id or current_page_id is None:
            # Get remaining pages (the closed page should already be removed from the dict)
            remaining_page_ids = self.page_manager.browser_manager.get_all_page_ids()
            
            if remaining_page_ids:
                # Switch to the last remaining page (most recently opened)
                print(f"[+] Active page closed, switching to: {remaining_page_ids[-1]}")
                await self.page_manager.switch_active_page(remaining_page_ids[-1])
            else:
                # No pages left, clear all page references
                print("[+] All pages closed, clearing page references")
                self.page_manager.interaction_manager.set_page(None)
                self.page_manager.browser_manager.page = None
