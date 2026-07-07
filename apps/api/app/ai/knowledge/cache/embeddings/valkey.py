"""
Valkey-backed embedding cache.

Stores each cached vector as a JSON-encoded list under a namespaced key,
with a configurable expiration so the cache does not grow unbounded.

Cache reads and writes fail open: if Valkey is unreachable or returns an
error, the failure is logged and treated as a full cache miss rather
than propagated. Embedding generation must never depend on the cache
being available.
"""

from __future__ import annotations

import json

import structlog
from redis.asyncio import Redis

from app.ai.knowledge.cache.embeddings.interfaces import EmbeddingCache

logger = structlog.get_logger()


class ValkeyEmbeddingCache(EmbeddingCache):
    """
    Embedding cache backed by Valkey (Redis-compatible).
    """

    def __init__(
        self,
        client: Redis,
        *,
        ttl_seconds: int,
    ) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    async def get_many(
        self,
        keys: list[str],
    ) -> dict[str, list[float]]:
        if not keys:
            return {}

        try:
            raw_values = await self._client.mget(keys)
        except Exception:
            logger.exception(
                "embedding.cache.read_failed",
                key_count=len(keys),
            )
            return {}

        vectors: dict[str, list[float]] = {}

        for key, raw_value in zip(keys, raw_values, strict=True):
            if raw_value is None:
                continue

            try:
                vectors[key] = json.loads(raw_value)
            except (TypeError, ValueError):
                logger.warning(
                    "embedding.cache.corrupt_entry",
                    key=key,
                )

        return vectors

    async def set_many(
        self,
        entries: dict[str, list[float]],
    ) -> None:
        if not entries:
            return

        try:
            pipeline = self._client.pipeline(transaction=False)

            for key, vector in entries.items():
                pipeline.set(
                    key,
                    json.dumps(vector),
                    ex=self._ttl_seconds,
                )

            await pipeline.execute()
        except Exception:
            logger.exception(
                "embedding.cache.write_failed",
                key_count=len(entries),
            )
