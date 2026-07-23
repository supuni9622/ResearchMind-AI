"""Rate limiting dependencies -- Valkey-backed, see `infrastructure/rate_limiting.py`."""

from __future__ import annotations

from functools import lru_cache
from uuid import UUID

from redis.asyncio import Redis

from app.core.settings import settings
from app.exceptions.base import RateLimitExceededException
from app.infrastructure.rate_limiting import ValkeyRateLimiter


@lru_cache
def _rate_limit_redis_client() -> Redis:
    return Redis.from_url(settings.valkey_url, decode_responses=True)


@lru_cache
def get_rate_limiter() -> ValkeyRateLimiter:
    """One shared limiter instance -- `check()` is fully parameterized per
    call (`key`/`limit`/`window_seconds`), so every rate-limited route
    reuses this same Valkey-backed instance rather than each owning one."""

    return ValkeyRateLimiter(_rate_limit_redis_client())


async def enforce_rate_limit(
    rate_limiter: ValkeyRateLimiter,
    *,
    scope: str,
    owner_id: UUID,
    limit: int,
    window_seconds: int,
) -> None:
    """Raise `RateLimitExceededException` if `owner_id` has exceeded `limit`
    requests in the current window for `scope` (e.g. "chat", "research",
    "deep_research_proposal"). Callers should call this before any real
    work (DB writes, retrieval, generation) starts."""

    decision = await rate_limiter.check(
        key=f"{scope}:{owner_id}",
        limit=limit,
        window_seconds=window_seconds,
    )
    if not decision.allowed:
        raise RateLimitExceededException(retry_after_seconds=decision.retry_after_seconds)
