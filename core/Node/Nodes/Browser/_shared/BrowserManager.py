"""
Browser Manager

Singleton manager for Playwright browser instances and contexts.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from playwright.async_api import (
    async_playwright,
    Browser,
    Playwright,
    BrowserContext,
    Page,
)
import structlog

from .services.session_config_service import SessionConfigService
from .services.path_service import PathService

logger = structlog.get_logger(__name__)

# Browser-specific args configuration
# These args are only compatible with Chromium-based browsers
CHROMIUM_ONLY_ARGS = [
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
    '--disable-client-side-phishing-detection',
    '--disable-hang-monitor',
    '--disable-prompt-on-repost',
    '--disable-domain-reliability',
    '--disable-component-update',
    '--disable-features=TranslateUI',
]

# Common args that work across all browser types
COMMON_ARGS = [
    '--no-sandbox',
    '--disable-blink-features=AutomationControlled',
]

# Valid browser types supported by Playwright
VALID_BROWSER_TYPES = ['chromium', 'firefox', 'webkit']


class BrowserManager:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrowserManager, cls).__new__(cls)
            cls._instance._playwright: Optional[Playwright] = None
            # (context, event_loop) so we only reuse when on same loop (avoid cross-loop use → about:blank/hang)
            cls._instance._contexts: Dict[str, Tuple[BrowserContext, asyncio.AbstractEventLoop]] = {}
            cls._instance._initialized = False
            cls._instance._loop: Optional[asyncio.AbstractEventLoop] = None
            cls._instance._headless: bool = True
        return cls._instance

    async def initialize(self, headless: bool = True):
        """Initialize Playwright. Re-initializes if called from a different event loop."""
        running_loop = asyncio.get_running_loop()
        if self._initialized and self._loop is running_loop:
            return
        # Different loop (e.g. new request): drop stale state; old Playwright/contexts will be GC'd
        if self._initialized and self._loop is not running_loop:
            self._contexts.clear()
            self._playwright = None
            self._initialized = False
            self._loop = None

        async with self._lock:
            if self._initialized and self._loop is running_loop:
                return
            logger.info("Initializing BrowserManager...")
            self._playwright = await async_playwright().start()
            self._headless = headless
            self._loop = running_loop
            self._initialized = True
            logger.info("BrowserManager initialized successfully")

    def _get_browser_args(self, browser_type: str) -> List[str]:
        """
        Get browser-specific args (hardcoded for anti-bot mitigation).
        
        Chromium gets all args, Firefox/WebKit only get common args.
        
        Args:
            browser_type: The browser type (chromium, firefox, webkit)
            
        Returns:
            List of browser args
        """
        base_args = COMMON_ARGS.copy()
        
        if browser_type == 'chromium':
            base_args.extend(CHROMIUM_ONLY_ARGS)
        
        return base_args

    def _get_browser_launcher(self, browser_type: str):
        """
        Get the appropriate browser launcher based on browser_type.
        
        Args:
            browser_type: The browser type (chromium, firefox, webkit)
            
        Returns:
            The Playwright browser launcher
        """
        if browser_type not in VALID_BROWSER_TYPES:
            logger.warning(
                "Invalid browser_type, falling back to chromium",
                browser_type=browser_type
            )
            browser_type = 'chromium'
        
        return getattr(self._playwright, browser_type)

    async def get_context(self, session_id: str, **kwargs) -> BrowserContext:
        """
        Get an existing persistent context by session_id or create a new one.
        The session_id is used to fetch config from DB and as the directory name.
        
        Args:
            session_id: The UUID of the browser session from the database
            **kwargs: Additional launch arguments to override defaults
            
        Returns:
            The browser context
        """
        if not self._initialized:
            await self.initialize()

        running_loop = asyncio.get_running_loop()
        if session_id in self._contexts:
            context, ctx_loop = self._contexts[session_id]
            if ctx_loop is running_loop:
                logger.info("Reusing existing persistent context", session_id=session_id)
                return context
            # Stale context from another loop; remove and create new one
            del self._contexts[session_id]

        # Fetch session config from Django model
        session_config = await SessionConfigService.get_session_config(session_id)
        
        # Extract config values with defaults
        browser_type = 'chromium'
        playwright_config = {}
        
        if session_config:
            browser_type = session_config.get('browser_type', 'chromium')
            playwright_config = session_config.get('playwright_config', {}) or {}
            # Use user_persistent_directory from config if available
            user_data_dir = session_config.get('user_persistent_directory')
        else:
            browser_type = 'chromium'
            playwright_config = {}
            user_data_dir = None
        
        # Fallback to default path if not in config
        if not user_data_dir:
            # Use backend/data/Browser/{session_id} as default
            # No async wrapper needed - Django settings are just Python objects
            user_data_dir = PathService.get_browser_session_path(session_id)
        
        # Ensure directory exists
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "Creating browser context",
            session_id=session_id,
            browser_type=browser_type,
            has_user_agent=bool(playwright_config.get('user_agent')),
            user_data_dir=user_data_dir
        )

        # Get browser-specific args (hardcoded)
        browser_args = self._get_browser_args(browser_type)

        # Build launch args (timeout avoids indefinite hang when profile dir is still locked)
        launch_args = {
            "headless": self._headless,
            "args": browser_args,
            "timeout": 60_000,  # 60s; fail fast instead of hanging if profile locked
        }

        # Override with any kwargs passed directly
        launch_args.update(kwargs)

        # Get the appropriate browser launcher
        browser_launcher = self._get_browser_launcher(browser_type)
        
        context = await browser_launcher.launch_persistent_context(
            user_data_dir, **launch_args
        )
        self._contexts[session_id] = (context, asyncio.get_running_loop())
        
        logger.info(
            "Browser context created successfully",
            session_id=session_id,
            browser_type=browser_type
        )
        
        return context

    async def close(self):
        """Close contexts for this event loop and playwright. Always clears _contexts."""
        logger.info("Closing BrowserManager...")
        running_loop = asyncio.get_running_loop()
        try:
            for name, entry in list(self._contexts.items()):
                context, ctx_loop = entry
                if ctx_loop is running_loop:
                    try:
                        await context.close()
                    except Exception as e:
                        logger.warning("Error closing context", session_id=name, error=str(e))
        finally:
            self._contexts.clear()

        if self._playwright and self._loop is running_loop:
            try:
                await self._playwright.stop()
            except Exception as e:
                logger.warning("Error stopping Playwright", error=str(e))
            self._playwright = None
            self._initialized = False
            self._loop = None
        # Let the OS release the profile dir lock before next launch with same path
        await asyncio.sleep(2)
        logger.info("BrowserManager closed")

