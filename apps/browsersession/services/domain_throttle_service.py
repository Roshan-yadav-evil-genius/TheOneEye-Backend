"""
Domain throttle service: wait before navigating to a URL when the session has
a throttle rule for that URL's domain, so requests to the domain are spaced
by the configured delay.
"""

import asyncio
import concurrent.futures
import time
from typing import Dict, List, Tuple
from urllib.parse import urlparse
import structlog

logger = structlog.get_logger(__name__)

# In-memory: (session_id, domain) -> last request time (monotonic)
_last_request_time: Dict[Tuple[str, str], float] = {}
# Serialize throttle check/sleep/update per (session_id, domain) so parallel URLs respect delay
_domain_locks: Dict[Tuple[str, str], asyncio.Lock] = {}


def _extract_domain(url: str) -> str:
    """Extract domain (host) from URL."""
    parsed = urlparse(url)
    return (parsed.netloc or "").strip().lower()


def _is_throttle_enabled_sync(session_id: str) -> bool:
    """Load session and return domain_throttle_enabled. Run in executor."""
    from apps.browsersession.models import BrowserSession

    try:
        session = BrowserSession.objects.get(id=session_id)
        return getattr(session, "domain_throttle_enabled", True)
    except BrowserSession.DoesNotExist:
        return False


def _load_rules_sync(session_id: str) -> List[Tuple[str, float]]:
    """Load (domain, delay_seconds) for enabled rules only. Run in executor."""
    from apps.browsersession.models import DomainThrottleRule

    rules = DomainThrottleRule.objects.filter(
        session_id=session_id, enabled=True
    ).values_list("domain", "delay_seconds")
    return [(d, float(delay)) for d, delay in rules]


async def wait_before_request(session_id: str, url: str) -> None:
    """
    If the session has a throttle rule for the URL's domain, wait until at least
    delay_seconds have passed since the last request to that domain for this session.
    Must be called from the same event loop that runs browser nodes (e.g. shared loop).
    """
    domain = _extract_domain(url)
    if not domain:
        return

    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        enabled = await loop.run_in_executor(executor, _is_throttle_enabled_sync, session_id)
        if not enabled:
            return
        rules = await loop.run_in_executor(executor, _load_rules_sync, session_id)

    delay_by_domain = {d: delay for d, delay in rules}
    delay_seconds = delay_by_domain.get(domain)
    if delay_seconds is None or delay_seconds <= 0:
        return

    key = (session_id, domain)
    if key not in _domain_locks:
        _domain_locks[key] = asyncio.Lock()
    async with _domain_locks[key]:
        now = time.monotonic()
        last = _last_request_time.get(key)
        if last is not None:
            elapsed = now - last
            if elapsed < delay_seconds:
                sleep_time = delay_seconds - elapsed
                logger.debug(
                    "Domain throttle: sleeping before request",
                    session_id=session_id,
                    domain=domain,
                    sleep_seconds=round(sleep_time, 2),
                )
                await asyncio.sleep(sleep_time)
        _last_request_time[key] = time.monotonic()
