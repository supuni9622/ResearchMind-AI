from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.infrastructure.rate_limiting import ValkeyRateLimiter


@pytest.mark.asyncio
async def test_check_allows_the_first_request_in_a_window_and_sets_expiry() -> None:
    redis = AsyncMock()
    redis.incr.return_value = 1
    limiter = ValkeyRateLimiter(redis)

    result = await limiter.check(key="chat:owner", limit=5, window_seconds=60)

    assert result.allowed is True
    assert result.retry_after_seconds == 0
    redis.expire.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_allows_requests_up_to_the_limit_without_resetting_expiry() -> None:
    redis = AsyncMock()
    redis.incr.return_value = 5
    limiter = ValkeyRateLimiter(redis)

    result = await limiter.check(key="chat:owner", limit=5, window_seconds=60)

    assert result.allowed is True
    redis.expire.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_blocks_once_the_limit_is_exceeded_and_reports_retry_after() -> None:
    redis = AsyncMock()
    redis.incr.return_value = 6
    redis.ttl.return_value = 17
    limiter = ValkeyRateLimiter(redis)

    result = await limiter.check(key="chat:owner", limit=5, window_seconds=60)

    assert result.allowed is False
    assert result.retry_after_seconds == 17


@pytest.mark.asyncio
async def test_check_falls_back_to_the_full_window_when_ttl_is_unavailable() -> None:
    redis = AsyncMock()
    redis.incr.return_value = 6
    redis.ttl.return_value = -1
    limiter = ValkeyRateLimiter(redis)

    result = await limiter.check(key="chat:owner", limit=5, window_seconds=60)

    assert result.allowed is False
    assert result.retry_after_seconds == 60


@pytest.mark.asyncio
async def test_check_scopes_the_window_bucket_into_the_redis_key() -> None:
    redis = AsyncMock()
    redis.incr.return_value = 1
    limiter = ValkeyRateLimiter(redis)

    await limiter.check(key="chat:owner", limit=5, window_seconds=60)

    (called_key,), _kwargs = redis.incr.await_args
    assert called_key.startswith("chat:owner:")
