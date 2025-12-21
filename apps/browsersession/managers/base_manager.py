"""Base manager class with common error handling and validation."""
import structlog
from typing import Optional
from playwright.async_api import Page
from .browser_manager import BrowserManager
from .websocket_message_sender import WebSocketMessageSender

logger = structlog.get_logger(__name__)


class BaseManager:
    """Base class for managers with common error handling and validation."""
    
    def __init__(
        self,
        browser_manager: Optional[BrowserManager] = None,
        message_sender: Optional[WebSocketMessageSender] = None
    ):
        """
        Initialize base manager.
        
        Args:
            browser_manager: BrowserManager instance (optional)
            message_sender: WebSocketMessageSender instance (optional)
        """
        self.browser_manager = browser_manager
        self.message_sender = message_sender
    
    async def _ensure_browser_initialized(self) -> bool:
        """
        Ensure browser manager is initialized.
        
        Returns:
            True if initialized, False otherwise (error already sent)
        """
        if not self.browser_manager:
            if self.message_sender:
                await self.message_sender.send_error('Browser not initialized')
            return False
        return True
    
    async def _ensure_page_available(self) -> bool:
        """
        Ensure browser manager and active page are available.
        
        Returns:
            True if available, False otherwise (error already sent)
        """
        if not await self._ensure_browser_initialized():
            return False
        
        if not self.browser_manager.page:
            if self.message_sender:
                await self.message_sender.send_error('No active page available')
            return False
        
        return True
    
    async def _get_page_or_error(self, page_id: str) -> Optional[Page]:
        """
        Get page by ID or send error if not found.
        
        Args:
            page_id: UUID string of the page
            
        Returns:
            Page instance if found, None otherwise (error already sent)
        """
        if not await self._ensure_browser_initialized():
            return None
        
        page = self.browser_manager.get_page_by_id(page_id)
        if not page:
            if self.message_sender:
                await self.message_sender.send_error(f'Page with ID {page_id} not found')
            return None
        
        return page
    
    async def _handle_error(
        self,
        operation_name: str,
        error: Exception,
        error_message: str,
        success_message: Optional[str] = None
    ) -> None:
        """
        Handle errors consistently with logging and error sending.
        
        Args:
            operation_name: Name of the operation (for logging)
            error: Exception that occurred
            error_message: User-friendly error message
            success_message: Optional success message to print
        """
        logger.error("Error in operation", operation=operation_name, error=str(error), exc_info=True)
        if self.message_sender:
            await self.message_sender.send_error(error_message)
    
    async def _execute_with_error_handling(
        self,
        operation_name: str,
        operation_func,
        error_message_template: str,
        success_message: Optional[str] = None
    ) -> bool:
        """
        Execute an operation with consistent error handling.
        
        Args:
            operation_name: Name of the operation
            operation_func: Async function to execute
            error_message_template: Template for error message (will format with operation_name)
            success_message: Optional success message to print
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await operation_func()
            if success_message:
                logger.info("Operation completed successfully", operation=operation_name, message=success_message)
            return True
        except Exception as e:
            error_message = error_message_template.format(operation=operation_name, error=str(e))
            await self._handle_error(operation_name, e, error_message)
            return False

