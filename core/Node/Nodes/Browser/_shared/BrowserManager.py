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

# URLs considered "blank" (default page, nothing in use) for idle-context cleanup
BLANK_PAGE_URLS = ('about:blank', 'about:blank#')


def _is_blank_url(url: Optional[str]) -> bool:
    """True if the page URL is considered blank (default, not in use)."""
    if not url or not url.strip():
        return True
    u = url.strip().split('#')[0].rstrip('#')
    return u.lower() in BLANK_PAGE_URLS


class BrowserManager:
    _instance = None
    # Lock is created per event loop (see initialize()); class-level Lock would be bound to one loop and break on next request.
    # Per-session locks so parallel nodes (e.g. fork) share one profile: first launches, second waits and reuses.
    _session_locks: Dict[str, asyncio.Lock] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrowserManager, cls).__new__(cls)
            cls._instance._playwright: Optional[Playwright] = None
            cls._instance._contexts: Dict[str, Tuple[BrowserContext, asyncio.AbstractEventLoop]] = {}
            cls._instance._initialized = False
            cls._instance._loop: Optional[asyncio.AbstractEventLoop] = None
            cls._instance._headless: bool = True
            cls._instance._lock: Optional[asyncio.Lock] = None
        return cls._instance

    def _get_session_lock(self, session_id: str) -> asyncio.Lock:
        """Return a lock for this session; lock is created in the current event loop."""
        if session_id not in self._session_locks:
            self._session_locks[session_id] = asyncio.Lock()
        return self._session_locks[session_id]

    def _ensure_loop_locks(self, running_loop: asyncio.AbstractEventLoop) -> None:
        """Clear session locks when event loop changed so new locks are created in current loop."""
        if self._loop is not running_loop:
            self._session_locks.clear()
            self._lock = asyncio.Lock()

    async def initialize(self, headless: bool = True):
        """Initialize Playwright. Re-initializes if called from a different event loop."""
        running_loop = asyncio.get_running_loop()
        if self._initialized and self._loop is running_loop:
            return
        # Different loop (e.g. new request): drop stale state; old Playwright/contexts will be GC'd
        if self._initialized and self._loop is not running_loop:
            self._contexts.clear()
            self._session_locks.clear()
            self._playwright = None
            self._initialized = False
            self._loop = None
        # Use a lock created in the current loop (avoids "bound to a different event loop" on 2nd request)
        self._ensure_loop_locks(running_loop)
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
        Uses a per-session lock so when multiple nodes (e.g. WebPageLoader and NetworkInterceptor
        in a fork) use the same session_id, only one launches the profile; others wait and reuse
        the same context (shared session/memory, no ProcessSingleton conflict).

        Args:
            session_id: The UUID of the browser session from the database
            **kwargs: Additional launch arguments to override defaults

        Returns:
            The browser context
        """
        # Always call initialize so that when the event loop changes (e.g. 2nd API request),
        # we clear stale locks and re-init; otherwise _get_session_lock would return a lock bound to the old loop.
        await self.initialize()

        running_loop = asyncio.get_running_loop()
        self._ensure_loop_locks(running_loop)
        session_lock = self._get_session_lock(session_id)

        async with session_lock:
            if session_id in self._contexts:
                context, ctx_loop = self._contexts[session_id]
                if ctx_loop is running_loop:
                    logger.info("Reusing existing persistent context", session_id=session_id)
                    return context
                del self._contexts[session_id]

            # Fetch session config from Django model
            session_config = await SessionConfigService.get_session_config(session_id)

            browser_type = 'chromium'
            playwright_config = {}

            if session_config:
                browser_type = session_config.get('browser_type', 'chromium')
                playwright_config = session_config.get('playwright_config', {}) or {}
                user_data_dir = session_config.get('user_persistent_directory')
            else:
                user_data_dir = None

            if not user_data_dir:
                user_data_dir = PathService.get_browser_session_path(session_id)

            Path(user_data_dir).mkdir(parents=True, exist_ok=True)

            logger.info(
                "Creating browser context",
                session_id=session_id,
                browser_type=browser_type,
                has_user_agent=bool(playwright_config.get('user_agent')),
                user_data_dir=user_data_dir
            )

            browser_args = self._get_browser_args(browser_type)
            launch_args = {
                "headless": self._headless,
                "args": browser_args,
                "timeout": 60_000,
            }
            launch_args.update(kwargs)

            browser_launcher = self._get_browser_launcher(browser_type)
            context = await browser_launcher.launch_persistent_context(
                user_data_dir, **launch_args
            )
            self._contexts[session_id] = (context, asyncio.get_running_loop())

            blocked_types = (session_config or {}).get("blocked_resource_types") or []
            if (session_config or {}).get("resource_blocking_enabled") and blocked_types:
                blocked_set = frozenset(blocked_types)

                async def _block_handler(route):
                    if route.request.resource_type in blocked_set:
                        await route.abort()
                    else:
                        await route.fallback()

                await context.route("**/*", _block_handler)
                logger.info(
                    "Resource blocking enabled for context",
                    session_id=session_id,
                    blocked_types=list(blocked_set),
                )

            logger.info(
                "Browser context created successfully",
                session_id=session_id,
                browser_type=browser_type
            )

            return context

    async def close_idle_contexts(self) -> None:
        """
        Close contexts that have only blank page(s) (e.g. default about:blank).
        Frees memory when no request is using the context; next request will create it again.
        Must be called from the same event loop that owns the contexts.
        """
        running_loop = asyncio.get_running_loop()
        to_remove: List[str] = []
        for session_id, (context, ctx_loop) in list(self._contexts.items()):
            if ctx_loop is not running_loop:
                continue
            try:
                pages = context.pages
                if not pages:
                    continue
                if all(_is_blank_url(p.url) for p in pages):
                    to_remove.append(session_id)
            except Exception as e:
                logger.warning(
                    "Error checking context pages for idle cleanup",
                    session_id=session_id,
                    error=str(e),
                )
        for session_id in to_remove:
            context, _ = self._contexts[session_id]
            try:
                await context.close()
                del self._contexts[session_id]
                logger.info("Closed idle browser context", session_id=session_id)
            except Exception as e:
                logger.warning(
                    "Error closing idle context",
                    session_id=session_id,
                    error=str(e),
                )

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

