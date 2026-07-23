"""Fixed-window request rate limiting, backed by Valkey.

MVP scope: a per-key fixed-window counter (`INCR` + `EXPIRE`), not a
sliding window or token bucket. This means a burst spanning a window
boundary can briefly allow up to ~2x `limit` in the worst case -- an
accepted tradeoff for the simplicity of one atomic `INCR` per check,
matching the accuracy this platform needs for basic per-user abuse/cost
protection rather than precise traffic shaping.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from redis.asyncio import Redis


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int


class ValkeyRateLimiter:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def check(self, *, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        """Increment `key`'s counter for the current fixed window and compare to `limit`.

        The window bucket is folded into the Valkey key itself
        (`{key}:{window_start}`) so each window's counter expires on its
        own rather than needing a separate reset step.
        """

        window_start = int(time.time()) // window_seconds
        redis_key = f"{key}:{window_start}"

        count = await self._redis.incr(redis_key)
        if count == 1:
            await self._redis.expire(redis_key, window_seconds)

        if count <= limit:
            return RateLimitResult(allowed=True, retry_after_seconds=0)

        ttl = await self._redis.ttl(redis_key)
        return RateLimitResult(
            allowed=False,
            retry_after_seconds=ttl if ttl and ttl > 0 else window_seconds,
        )
