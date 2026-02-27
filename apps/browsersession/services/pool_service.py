"""
Pool service: pick a session from a pool (per-domain least-used or global fallback).
All functions are sync so they can be run via run_in_executor from async context.
"""

import random
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


def pick_session_from_pool(pool_id: str, domain: Optional[str] = None) -> str:
    """
    Pick one session from the pool. When domain is provided, pick the session
    least used for that domain; if tied, choose randomly. When domain is None,
    use global usage_count on BrowserPoolSession (fallback).

    Returns:
        session_id (str) of the chosen session.
    Raises:
        ValueError: if pool has no sessions.
    """
    from apps.browsersession.models import (
        BrowserPool,
        BrowserPoolSession,
        BrowserPoolSessionDomainUsage,
    )

    pool_sessions = list(
        BrowserPoolSession.objects.filter(pool_id=pool_id).select_related("session")
    )
    if not pool_sessions:
        raise ValueError(f"Pool {pool_id} has no sessions")

    if domain:
        return _pick_by_domain(pool_id, domain, pool_sessions)
    return _pick_by_global_usage(pool_sessions)


def _pick_by_domain(pool_id: str, domain: str, pool_sessions: list) -> str:
    """Pick session least used for this domain; if tied, random. Increment usage."""
    from apps.browsersession.models import BrowserPoolSessionDomainUsage

    domain = (domain or "").strip().lower()
    if not domain:
        return _pick_by_global_usage(pool_sessions)

    # Get usage count per (pool, session) for this domain
    session_ids = [ps.session_id for ps in pool_sessions]
    usages = {
        row["session_id"]: row["usage_count"]
        for row in BrowserPoolSessionDomainUsage.objects.filter(
            pool_id=pool_id, session_id__in=session_ids, domain=domain
        ).values("session_id", "usage_count")
    }
    counts = [(ps.session_id, usages.get(ps.session_id, 0)) for ps in pool_sessions]
    min_count = min(c for _, c in counts)
    candidates = [sid for sid, c in counts if c == min_count]
    chosen_session_id = random.choice(candidates)

    # Increment usage for (pool, session, domain)
    obj, created = BrowserPoolSessionDomainUsage.objects.get_or_create(
        pool_id=pool_id,
        session_id=chosen_session_id,
        domain=domain,
        defaults={"usage_count": 0},
    )
    obj.usage_count += 1
    obj.save(update_fields=["usage_count", "updated_at"])

    logger.debug(
        "Picked session from pool by domain",
        pool_id=pool_id,
        domain=domain,
        session_id=str(chosen_session_id),
        usage_after=obj.usage_count,
    )
    return str(chosen_session_id)


def _pick_by_global_usage(pool_sessions: list) -> str:
    """Pick session with minimum usage_count; if tied, random. Increment usage."""
    min_count = min(ps.usage_count for ps in pool_sessions)
    candidates = [ps for ps in pool_sessions if ps.usage_count == min_count]
    chosen = random.choice(candidates)
    chosen.usage_count += 1
    chosen.save(update_fields=["usage_count", "updated_at"])
    logger.debug(
        "Picked session from pool by global usage",
        pool_id=str(chosen.pool_id),
        session_id=str(chosen.session_id),
        usage_after=chosen.usage_count,
    )
    return str(chosen.session_id)
