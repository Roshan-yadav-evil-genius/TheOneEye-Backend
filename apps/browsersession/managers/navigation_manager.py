"""Browser navigation operations."""
from .base_manager import BaseManager
from .browser_manager import BrowserManager
from .websocket_message_sender import WebSocketMessageSender


class NavigationManager(BaseManager):
    """Handles browser navigation commands."""
    
    def __init__(
        self,
        browser_manager: BrowserManager,
        message_sender: WebSocketMessageSender
    ):
        """
        Initialize navigation manager.
        
        Args:
            browser_manager: BrowserManager instance
            message_sender: WebSocketMessageSender instance
        """
        super().__init__(browser_manager, message_sender)
    
    async def handle_navigation(self, data: dict) -> None:
        """
        Handle navigation commands (back, forward, refresh, goto).
        
        Args:
            data: Navigation command data with 'action' and optional 'url'
        """
        if not await self._ensure_page_available():
            return
        
        page = self.browser_manager.page
        action = data.get('action')
        
        # Validate action first
        valid_actions = ['back', 'forward', 'refresh', 'goto']
        if action not in valid_actions:
            await self.message_sender.send_error(f'Unknown navigation action: {action}')
            return
        
        # Validate action-specific requirements
        if action == 'goto':
            url = data.get('url')
            if not url:
                await self.message_sender.send_error('URL required for goto action')
                return
        
        async def _navigate_operation():
            if action == 'back':
                await page.go_back()
            elif action == 'forward':
                await page.go_forward()
            elif action == 'refresh':
                await page.reload()
            elif action == 'goto':
                await page.goto(data.get('url'), wait_until='commit')
            
            # Update address bar with current URL
            current_url = page.url
            await self.message_sender.send_url_changed(current_url)
        
        await self._execute_with_error_handling(
            operation_name='handle_navigation',
            operation_func=_navigate_operation,
            error_message_template='Navigation error: {error}',
            success_message=f"[+] Navigation: {action}"
        )

