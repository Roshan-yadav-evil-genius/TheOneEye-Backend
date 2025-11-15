"""Page management operations."""
from typing import Optional
from playwright.async_api import Page
from .base_manager import BaseManager
from .browser_manager import BrowserManager
from .interaction_manager import InteractionManager
from .websocket_message_sender import WebSocketMessageSender


class PageManager(BaseManager):
    """Manages page operations: switching, creating, and closing tabs."""
    
    def __init__(
        self,
        browser_manager: BrowserManager,
        interaction_manager: InteractionManager,
        message_sender: WebSocketMessageSender
    ):
        """
        Initialize page manager.
        
        Args:
            browser_manager: BrowserManager instance
            interaction_manager: InteractionManager instance
            message_sender: WebSocketMessageSender instance
        """
        super().__init__(browser_manager, message_sender)
        self.interaction_manager = interaction_manager
    
    async def switch_active_page(self, page_id: str) -> None:
        """
        Switch the active page for streaming and input handling.
        Single Responsibility: This method coordinates updating all page-dependent components.
        
        Args:
            page_id: UUID string of the page to switch to
        """
        page = await self._get_page_or_error(page_id)
        if not page:
            return
        
        async def _switch_operation():
            # Bring the page to front and make it active
            await page.bring_to_front()
            
            # Update all page-dependent components atomically via interaction manager
            self.interaction_manager.set_page(page)
            
            # Update the main page reference
            self.browser_manager.page = page
            
            # Send confirmation to frontend with current URL
            current_url = page.url
            await self.message_sender.send_page_switched(page_id, current_url)
        
        await self._execute_with_error_handling(
            operation_name='switch_active_page',
            operation_func=_switch_operation,
            error_message_template='Error switching page: {error}',
            success_message=f"[+] Switched to page: {page_id}"
        )
    
    async def create_new_tab(self) -> None:
        """
        Create a new tab/page and navigate it to duckduckgo.com.
        The page will be automatically tracked and switched to via page_added_callback.
        """
        if not await self._ensure_browser_initialized():
            return
        
        if not self.browser_manager.context:
            await self.message_sender.send_error('Browser context not initialized')
            return
        
        async def _create_tab_operation():
            # Create a new page in the existing context
            # This will trigger the page_added_callback which will auto-switch to it
            new_page = await self.browser_manager.context.new_page()
            
            # Navigate to duckduckgo.com
            await new_page.goto('https://duckduckgo.com/', wait_until='commit')
        
        await self._execute_with_error_handling(
            operation_name='create_new_tab',
            operation_func=_create_tab_operation,
            error_message_template='Error creating new tab: {error}',
            success_message="[+] Created new tab and navigated to duckduckgo.com"
        )
    
    async def close_tab(self, page_id: str) -> None:
        """
        Close a tab/page by its ID.
        If closing the active page, switch to another available page.
        
        Args:
            page_id: UUID string of the page to close
        """
        page = await self._get_page_or_error(page_id)
        if not page:
            return
        
        # Check if this is the active page
        is_active_page = (self.browser_manager.page == page)
        
        async def _close_tab_operation():
            # If closing the active page, switch to another page first to avoid errors
            if is_active_page:
                # Get all remaining pages (excluding the one we're about to close)
                all_page_ids = self.browser_manager.get_all_page_ids()
                remaining_page_ids = [pid for pid in all_page_ids if pid != page_id]
                
                if remaining_page_ids:
                    # Switch to the last remaining page before closing
                    await self.switch_active_page(remaining_page_ids[-1])
                else:
                    # No pages left, clear all page references before closing
                    self.browser_manager.page = None
                    self.interaction_manager.set_page(None)
            
            # Now close the page - this will trigger page_removed_callback to remove from dict
            await page.close()
        
        await self._execute_with_error_handling(
            operation_name='close_tab',
            operation_func=_close_tab_operation,
            error_message_template='Error closing tab: {error}',
            success_message=f"[+] Closed tab: {page_id}"
        )

