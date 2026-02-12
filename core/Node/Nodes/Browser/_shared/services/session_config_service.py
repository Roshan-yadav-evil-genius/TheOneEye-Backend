import asyncio
import concurrent.futures
from typing import Optional, Dict, Any
import structlog

from .path_service import PathService

logger = structlog.get_logger(__name__)


class SessionConfigService:
    """Service to fetch browser session configuration from Django models."""
    
    @staticmethod
    async def get_session_config(session_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch full session config from Django model using async-safe calls.
        Uses a thread pool for the DB call to avoid CurrentThreadExecutor deadlock
        when the async code is run from NodeExecutor's run_until_complete() loop.
        
        Args:
            session_id: The UUID of the browser session
            
        Returns:
            Session config dict with browser_type, playwright_config, etc.
            Returns None if session not found.
        """
        try:
            from apps.browsersession.models import BrowserSession
            
            def _fetch_session_sync():
                try:
                    return BrowserSession.objects.get(id=session_id)
                except BrowserSession.DoesNotExist:
                    return None
            
            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                session = await loop.run_in_executor(executor, _fetch_session_sync)
            if session is None:
                logger.warning(
                    "Session not found",
                    session_id=session_id
                )
                return None
            
            # Calculate user_persistent_directory path
            # No async wrapper needed - Django settings are just Python objects
            # Use PathService for consistent path construction
            user_persistent_directory = PathService.get_browser_session_path(str(session.id))
            
            config = {
                "browser_type": session.browser_type,
                "playwright_config": session.playwright_config or {},
                "status": session.status,
                "name": session.name,
                "description": session.description,
                "user_persistent_directory": user_persistent_directory,
                "domain_throttle_enabled": getattr(session, "domain_throttle_enabled", True),
                "resource_blocking_enabled": getattr(session, "resource_blocking_enabled", False),
                "blocked_resource_types": session.blocked_resource_types if getattr(session, "blocked_resource_types", None) is not None else [],
            }
            
            logger.debug(
                "Fetched session config",
                session_id=session_id,
                browser_type=config.get('browser_type'),
                has_playwright_config=bool(config.get('playwright_config'))
            )
            return config
        except Exception as e:
            logger.error(
                "Unexpected error fetching session config",
                session_id=session_id,
                error=str(e)
            )
        return None

