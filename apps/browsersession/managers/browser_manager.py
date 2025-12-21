"""Browser management for Playwright browser instances."""
import uuid
import structlog
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from typing import Optional, Callable

logger = structlog.get_logger(__name__)


class BrowserManager:
    """Manages Playwright browser lifecycle only."""

    def __init__(self, viewport_width: int = 640, viewport_height: int = 480,
                 page_added_callback: Optional[Callable[[str], None]] = None,
                 page_removed_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize browser manager.

        Args:
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
            page_added_callback: Optional callback function(page_id: str) called when a page is added
            page_removed_callback: Optional callback function(page_id: str) called when a page is removed
        """
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.pages: dict[str, Page] = {}  # Track all pages with UUID keys
        self._page_to_id: dict[Page, str] = {}  # Reverse mapping: Page -> UUID
        self.page_added_callback = page_added_callback
        self.page_removed_callback = page_removed_callback

    def _register_page(self, page: Page) -> str:
        """
        Register a page with a UUID and set up close listener.

        Args:
            page: Page instance to register

        Returns:
            UUID string assigned to the page
        """
        page_id = uuid.uuid4().hex
        self.pages[page_id] = page
        self._page_to_id[page] = page_id
        logger.info("New page created", page_id=page_id)

        # Call page_added callback if provided
        if self.page_added_callback:
            self.page_added_callback(page_id)

        # Set up close listener to remove page from tracking when destroyed
        def on_close(_):
            if page_id in self.pages:
                del self.pages[page_id]
            if page in self._page_to_id:
                del self._page_to_id[page]
            logger.info("Page closed", page_id=page_id)

            # Call page_removed callback if provided
            if self.page_removed_callback:
                self.page_removed_callback(page_id)

        page.on('close', on_close)
        return page_id

    async def launch(self, url: str, headless: bool = False, session_id: Optional[str] = None) -> Page:
        """
        Launch browser and navigate to URL.

        Args:
            url: URL to navigate to
            headless: Whether to run browser in headless mode
            session_id: Optional session ID to use for persistent browser context storage

        Returns:
            Page instance

        Raises:
            Exception: If browser launch or navigation fails
        """
        self.playwright = await async_playwright().start()

        # Browser launch arguments to disable background throttling
        # These prevent the browser from throttling when in background
        browser_args = [
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--disable-plugins-discovery',
            '--disable-default-apps',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-field-trial-config',
            '--disable-back-forward-cache',
            '--disable-ipc-flooding-protection',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-component-extensions-with-background-pages',
            '--disable-background-networking',
            '--disable-sync',
            '--metrics-recording-only',
            '--no-report-upload',
            '--disable-logging',
            '--disable-gpu-logging',
            '--silent',
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-background-timer-throttling',
            '--disable-client-side-phishing-detection',
            '--disable-hang-monitor',
            '--disable-prompt-on-repost',
            '--disable-domain-reliability',
            '--disable-component-update',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection',
        ]

        # Prepare context options
        context_options = {
            'viewport': {
                'width': self.viewport_width,
                'height': self.viewport_height
            },
            # 'user_agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.3",
            'permissions': ["geolocation"],
            'locale': "en-US",
            'timezone_id': "Asia/Kolkata",
            # example: New Delhi
            'geolocation': {"latitude": 28.6139, "longitude": 77.2090},
        }

        # If session_id is provided, use persistent context
        if session_id:
            # Create directory for persistent browser data
            base_dir = Path("data") / "Browser"
            base_dir.mkdir(parents=True, exist_ok=True)

            user_data_dir = base_dir / session_id
            user_data_dir.mkdir(exist_ok=True)

            # Create persistent browser context
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=headless,
                args=browser_args,
                **context_options
            )

            # Get the browser instance from persistent context
            self.browser = self.context.browser
        else:
            # Launch browser normally (non-persistent)
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=browser_args
            )

            # Create browser context with viewport matching canvas dimensions
            self.context = await self.browser.new_context(**context_options)

        # Set up context event listener BEFORE creating pages
        # This will catch all pages including the initial one
        self.context.on('page', lambda page: self._register_page(page))

        # For persistent context, a page is automatically created
        # For regular context, we need to create a new page
        self.page = await self.context.new_page()

        # Navigate to URL - don't wait for full page load, start streaming immediately
        # Using 'commit' means we return as soon as navigation is committed
        await self.page.goto(url, wait_until='commit')
        return self.page

    async def cleanup(self) -> None:
        """Clean up browser and Playwright instances."""
        if self.page:
            try:
                await self.page.close()
            except Exception as e:
                logger.warning("Error closing page", error=str(e), exc_info=True)
            self.page = None

        if self.context:
            try:
                await self.context.close()
            except Exception as e:
                logger.warning("Error closing context", error=str(e), exc_info=True)
            self.context = None

        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                logger.warning("Error closing browser", error=str(e), exc_info=True)
            self.browser = None

        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                logger.warning("Error stopping playwright", error=str(e), exc_info=True)
            self.playwright = None

        # Clear page tracking dictionaries
        self.pages.clear()
        self._page_to_id.clear()

    def get_page_id(self, page: Page) -> Optional[str]:
        """
        Get UUID for a given Page instance.

        Args:
            page: Page instance to look up

        Returns:
            UUID string if page is tracked, None otherwise
        """
        return self._page_to_id.get(page)

    def get_all_page_ids(self) -> list[str]:
        """
        Get list of all active page IDs.

        Returns:
            List of UUID strings for all tracked pages
        """
        return list(self.pages.keys())

    def get_page_by_id(self, page_id: str) -> Optional[Page]:
        """
        Get page instance by its UUID.

        Args:
            page_id: UUID string of the page

        Returns:
            Page instance if found, None otherwise
        """
        return self.pages.get(page_id)
