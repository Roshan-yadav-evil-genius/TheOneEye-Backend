"""Screenshot capture and streaming functionality."""
import asyncio
from typing import Awaitable, Callable, Optional
from playwright.async_api import Page, Error as PlaywrightError


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
    
    async def capture_screenshot_with_viewport(self) -> bytes:
        """
        Capture screenshot and return bytes with viewport dimensions prepended.
        
        Frame format: [width: 4 bytes][height: 4 bytes][JPEG data]
        - width/height are big-endian unsigned 32-bit integers
        - This allows frontend to know the actual viewport dimensions
        
        Returns:
            Bytes with viewport header + JPEG image data
            
        Raises:
            RuntimeError: If page is not set
        """
        if not self.page:
            raise RuntimeError("Page not set. Cannot capture screenshot.")
        
        # Get viewport dimensions
        viewport = self.page.viewport_size
        if viewport:
            width = viewport['width']
            height = viewport['height']
        else:
            # Fallback to default if viewport not available
            width = 1920
            height = 1080
        
        # Capture screenshot
        screenshot_bytes = await self.page.screenshot(
            type='jpeg',
            quality=self.quality
        )
        
        # Prepend viewport dimensions as 8 bytes (4 + 4)
        width_bytes = width.to_bytes(4, 'big')
        height_bytes = height.to_bytes(4, 'big')
        
        return width_bytes + height_bytes + screenshot_bytes
    
    async def capture_screenshot(self) -> bytes:
        """
        Capture screenshot and return raw JPEG bytes (legacy method).
        
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
    
    def _is_page_closed_error(self, error: Exception) -> bool:
        """
        Check if an error indicates the page was closed.
        
        Args:
            error: Exception to check
            
        Returns:
            True if error indicates page/context/browser was closed
        """
        error_message = str(error).lower()
        closed_indicators = [
            "target page, context or browser has been closed",
            "page has been closed",
            "context has been closed",
            "browser has been closed",
            "target closed",
            "execution context was destroyed",
        ]
        return any(indicator in error_message for indicator in closed_indicators)
    
    async def stream(
        self,
        send_callback: Callable[[bytes], Awaitable[None]],
        stop_event: Optional[asyncio.Event] = None
    ) -> None:
        """
        Stream screenshots continuously with viewport dimensions included.
        
        Each frame includes an 8-byte header with viewport dimensions,
        allowing the frontend to properly scale and map coordinates.
        
        Handles page close events gracefully by waiting for a new page
        to be set via set_page().
        
        Args:
            send_callback: Async function to send frame data (bytes with viewport header)
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
                    # Use the new method that includes viewport dimensions
                    frame_bytes = await self.capture_screenshot_with_viewport()
                    await send_callback(frame_bytes)
                except RuntimeError as e:
                    # Page reference is None
                    if "Page not set" in str(e):
                        await asyncio.sleep(0.1)
                        continue
                    raise
                except PlaywrightError as e:
                    # Page was closed (e.g., popup closed after auth)
                    if self._is_page_closed_error(e):
                        print(f"[!] Page closed during screenshot, waiting for new page...")
                        # Clear the stale page reference
                        self.page = None
                        # Wait for a new page to be set via set_page()
                        await asyncio.sleep(0.1)
                        continue
                    raise
                except Exception as e:
                    # Catch any other page closed errors (sometimes wrapped differently)
                    if self._is_page_closed_error(e):
                        print(f"[!] Page closed during screenshot, waiting for new page...")
                        self.page = None
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
