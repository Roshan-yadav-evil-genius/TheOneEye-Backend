from typing import Optional, Dict, Any
import structlog
from channels.db import database_sync_to_async

from .path_service import PathService

logger = structlog.get_logger(__name__)


class SessionConfigService:
    """Service to fetch browser session configuration from Django models."""
    
    @staticmethod
    async def get_session_config(session_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch full session config from Django model using async-safe calls.
        
        Args:
            session_id: The UUID of the browser session
            
        Returns:
            Session config dict with browser_type, playwright_config, etc.
            Returns None if session not found.
        """
        try:
            from apps.browsersession.models import BrowserSession
            
            @database_sync_to_async
            def _fetch_session():
                try:
                    return BrowserSession.objects.get(id=session_id)
                except BrowserSession.DoesNotExist:
                    return None
            
            session = await _fetch_session()
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
                'browser_type': session.browser_type,
                'playwright_config': session.playwright_config or {},
                'status': session.status,
                'name': session.name,
                'description': session.description,
                'user_persistent_directory': user_persistent_directory,
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

