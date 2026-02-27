"""
Session resolver: map form value (session:uuid or pool:uuid) to a concrete session_id.
When value is pool:uuid, calls pool_service.pick_session_from_pool (via run_in_executor).
"""

import asyncio
from typing import Optional
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger(__name__)

POOL_PREFIX = "pool:"
SESSION_PREFIX = "session:"


def extract_domain_from_url(url: Optional[str]) -> Optional[str]:
    """Extract normalized domain (host) from URL for pool selection. Strips www."""
    if not url or not isinstance(url, str) or not url.strip():
        return None
    parsed = urlparse(url.strip())
    netloc = (parsed.netloc or "").strip().lower()
    if not netloc:
        return None
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc or None


async def resolve_to_session_id(value: Optional[str], domain: Optional[str] = None) -> str:
    """
    Resolve form value to a concrete browser session UUID.

    - pool:<uuid> -> pick session from pool (via pool_service), return that session_id.
    - session:<uuid> -> strip prefix and return the uuid.
    - None, empty, or other format -> raise ValueError (no raw UUID; total replace).

    Must be called from async context; pool_service is run in executor.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError("session_name is required; use session:<uuid> or pool:<uuid>")

    value = value.strip()

    if value.startswith(POOL_PREFIX):
        pool_id = value[len(POOL_PREFIX) :].strip()
        if not pool_id:
            raise ValueError("Invalid pool value: pool:id is required")
        from apps.browsersession.services.pool_service import pick_session_from_pool

        loop = asyncio.get_running_loop()
        session_id = await loop.run_in_executor(
            None,
            lambda: pick_session_from_pool(pool_id, domain=domain),
        )
        return session_id

    if value.startswith(SESSION_PREFIX):
        session_id = value[len(SESSION_PREFIX) :].strip()
        if not session_id:
            raise ValueError("Invalid session value: session:uuid is required")
        return session_id

    raise ValueError(
        "session_name must be session:<uuid> or pool:<uuid>; raw UUID is not supported"
    )
