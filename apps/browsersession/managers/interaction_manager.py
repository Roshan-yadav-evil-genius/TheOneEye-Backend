"""User interaction management for a single page."""
from typing import Optional
from playwright.async_api import Page
from ..streaming.screenshot_streamer import ScreenshotStreamer
from ..controllers.mouse_controller import MouseController
from ..controllers.keyboard_controller import KeyboardController
from ..config import StreamConfig


class InteractionManager:
    """Manages all user interaction components for a single page."""
    
    def __init__(self, fps: float = None, quality: int = None):
        """
        Initialize interaction manager.
        Creates all internal components (streamer, controllers) internally.
        
        Args:
            fps: Frames per second for streaming (defaults to StreamConfig.STREAMING_FPS)
            quality: JPEG quality for screenshots (defaults to StreamConfig.STREAMING_QUALITY)
        """
        # Create components internally
        self.screenshot_streamer = ScreenshotStreamer(
            fps=fps if fps is not None else StreamConfig.STREAMING_FPS,
            quality=quality if quality is not None else StreamConfig.STREAMING_QUALITY
        )
        self.mouse_controller = MouseController()
        self.keyboard_controller = KeyboardController()
        self._page: Optional[Page] = None
    
    @property
    def page(self) -> Optional[Page]:
        """Get the current page instance."""
        return self._page
    
    def set_page(self, page: Optional[Page]) -> None:
        """
        Set the page for all interaction components atomically.
        
        Args:
            page: Playwright Page instance or None to clear
        """
        self._page = page
        
        # Update all components with the new page (components are always initialized)
        self.screenshot_streamer.set_page(page)
        self.mouse_controller.page = page
        self.keyboard_controller.page = page
    
    def stop_streaming(self) -> None:
        """Stop screenshot streaming."""
        self.screenshot_streamer.stop()

