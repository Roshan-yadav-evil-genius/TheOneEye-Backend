import asyncio
import concurrent.futures
from typing import Optional, Dict, Any
import structlog

from .path_service import PathService

logger = structlog.get_logger(__name__)


class SessionConfigService:
    """Service to fetch browser session configuration from Django models."""

    @staticmethod
    async def get_session_config(session_id: str, pool_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch full session config: browser from BrowserSession; throttle/blocking from BrowserPool when pool_id is set.
        Uses a thread pool for DB calls to avoid CurrentThreadExecutor deadlock.

        Args:
            session_id: The UUID of the browser session (resolved from pool).
            pool_id: The UUID of the browser pool (always set when execution is pool-only).

        Returns:
            Session config dict with browser_type, playwright_config, user_persistent_directory,
            and when pool_id is set: domain_throttle_enabled, resource_blocking_enabled, blocked_resource_types from pool.
        """
        try:
            from apps.browsersession.models import BrowserSession, BrowserPool

            def _fetch_sync():
                try:
                    session = BrowserSession.objects.get(id=session_id)
                except BrowserSession.DoesNotExist:
                    return None, None
                pool = None
                if pool_id:
                    try:
                        pool = BrowserPool.objects.get(id=pool_id)
                    except BrowserPool.DoesNotExist:
                        pass
                return session, pool

            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                session, pool = await loop.run_in_executor(executor, _fetch_sync)
            if session is None:
                logger.warning("Session not found", session_id=session_id)
                return None

            user_persistent_directory = PathService.get_browser_session_path(str(session.id))

            config = {
                "browser_type": session.browser_type,
                "playwright_config": session.playwright_config or {},
                "status": session.status,
                "name": session.name,
                "description": session.description,
                "user_persistent_directory": user_persistent_directory,
            }

            if pool is not None:
                config["domain_throttle_enabled"] = getattr(pool, "domain_throttle_enabled", True)
                config["resource_blocking_enabled"] = getattr(pool, "resource_blocking_enabled", False)
                config["blocked_resource_types"] = (
                    list(pool.blocked_resource_types) if getattr(pool, "blocked_resource_types", None) else []
                )
            else:
                config["domain_throttle_enabled"] = False
                config["resource_blocking_enabled"] = False
                config["blocked_resource_types"] = []

            logger.debug(
                "Fetched session config",
                session_id=session_id,
                pool_id=pool_id,
                browser_type=config.get("browser_type"),
                has_playwright_config=bool(config.get("playwright_config")),
            )
            return config
        except Exception as e:
            logger.error(
                "Unexpected error fetching session config",
                session_id=session_id,
                pool_id=pool_id,
                error=str(e),
            )
        return None

