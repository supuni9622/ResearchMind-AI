"""
Valkey-backed L1 Exact Cache.

Stores each cached `GenerationResult` as JSON under its deterministic
`CacheKey.redis_key()`. Mirrors `knowledge/cache/embeddings/valkey.py`'s
fail-open contract: a Valkey error is logged and treated as a miss /
no-op rather than propagated — the cache must never fail generation.
"""

from __future__ import annotations

import structlog
from app.ai.runtime.generation.caching.interfaces import (
    ExactCacheProviderInterface,
)
from app.ai.runtime.generation.caching.models import (
    CacheKey,
)
from app.ai.runtime.generation.models import (
    GenerationResult,
)
from redis.asyncio import Redis

logger = structlog.get_logger()


class ValkeyExactCacheProvider(
    ExactCacheProviderInterface,
):
    def __init__(
        self,
        client: Redis,
    ) -> None:
        self._client = client

    async def get(
        self,
        key: CacheKey,
    ) -> GenerationResult | None:

        try:
            raw_value = await self._client.get(
                key.redis_key(),
            )
        except Exception:
            logger.exception(
                "caching.exact.read_failed",
            )
            return None

        if raw_value is None:
            return None

        try:
            return GenerationResult.model_validate_json(
                raw_value,
            )
        except Exception:
            logger.warning(
                "caching.exact.corrupt_entry",
                key=key.redis_key(),
            )
            return None

    async def set(
        self,
        key: CacheKey,
        result: GenerationResult,
        *,
        ttl_seconds: int | None,
    ) -> None:

        try:
            await self._client.set(
                key.redis_key(),
                result.model_dump_json(),
                ex=ttl_seconds,
            )
        except Exception:
            logger.exception(
                "caching.exact.write_failed",
                key=key.redis_key(),
            )
