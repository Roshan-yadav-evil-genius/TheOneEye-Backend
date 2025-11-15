"""Screenshot capture and streaming functionality."""
import asyncio
from typing import Awaitable, Callable, Optional
from playwright.async_api import Page


class ScreenshotStreamer:
    """Handles screenshot capture and streaming."""
    
    def __init__(self, page: Optional[Page] = None, fps: float = 15.0, quality: int = 85):
        """
        Initialize screenshot streamer.
        
        Args:
            page: Playwright Page instance (optional, can be set later)
            fps: Frames per second for streaming
            quality: JPEG quality (1-100)
        """
        self.page = page
        self.fps = fps
        self.quality = quality
        self.frame_delay = 1.0 / fps
        self.streaming = False
    
    async def capture_screenshot(self) -> bytes:
        """
        Capture screenshot and return raw JPEG bytes.
        
        Returns:
            Raw JPEG image bytes
            
        Raises:
            RuntimeError: If page is not set
        """
        if not self.page:
            raise RuntimeError("Page not set. Cannot capture screenshot.")
        screenshot_bytes = await self.page.screenshot(
            type='jpeg',
            quality=self.quality
        )
        return screenshot_bytes
    
    async def stream(
        self,
        send_callback: Callable[[bytes], Awaitable[None]],
        stop_event: Optional[asyncio.Event] = None
    ) -> None:
        """
        Stream screenshots continuously.
        
        Args:
            send_callback: Async function to send frame data (raw bytes)
            stop_event: Optional event to signal stopping
        """
        self.streaming = True
        
        try:
            while self.streaming:
                if stop_event and stop_event.is_set():
                    break
                
                # Wait for page to be set if not available yet
                if not self.page:
                    await asyncio.sleep(0.1)  # Wait a bit before checking again
                    continue
                
                try:
                    frame_bytes = await self.capture_screenshot()
                    await send_callback(frame_bytes)
                except RuntimeError as e:
                    # Page might have been removed, wait and retry
                    if "Page not set" in str(e):
                        await asyncio.sleep(0.1)
                        continue
                    raise
                
                await asyncio.sleep(self.frame_delay)
        except asyncio.CancelledError:
            print("Screenshot streaming cancelled")
            raise
        finally:
            self.streaming = False
    
    def stop(self) -> None:
        """Stop streaming."""
        self.streaming = False
    
    def set_page(self, page: Page) -> None:
        """
        Update the page instance for streaming.
        
        Args:
            page: New Playwright Page instance to stream from
        """
        self.page = page

