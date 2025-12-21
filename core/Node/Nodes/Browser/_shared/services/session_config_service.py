from typing import Optional, Dict, Any
import structlog
from asgiref.sync import sync_to_async

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
            
            @sync_to_async
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
            @sync_to_async
            def _get_base_dir():
                from django.conf import settings
                return settings.BASE_DIR
            
            base_dir = await _get_base_dir()
            # Use backend/data/Browser/{session_id} as the persistent directory
            user_persistent_directory = str(base_dir / 'data' / 'Browser' / str(session.id))
            
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

