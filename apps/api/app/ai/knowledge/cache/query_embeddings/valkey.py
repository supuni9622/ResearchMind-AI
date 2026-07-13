"""
Valkey-backed query embedding cache.

Stores each cached vector as a JSON-encoded list under a namespaced key,
with a configurable expiration so the cache does not grow unbounded.

Cache reads and writes fail open: if Valkey is unreachable or returns an
error, the failure is logged and treated as a full cache miss rather
than propagated. Query embedding generation must never depend on the
cache being available.
"""

from __future__ import annotations

import json

import structlog
from redis.asyncio import Redis

from app.ai.knowledge.cache.query_embeddings.interfaces import (
    QueryEmbeddingCache,
)

logger = structlog.get_logger()


class ValkeyQueryEmbeddingCache(QueryEmbeddingCache):
    """
    Query embedding cache backed by Valkey (Redis-compatible).
    """

    def __init__(
        self,
        client: Redis,
        *,
        ttl_seconds: int,
    ) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    async def get(
        self,
        key: str,
    ) -> list[float] | None:
        try:
            raw_value = await self._client.get(key)
        except Exception:
            logger.exception(
                "query_embedding.cache.read_failed",
                key=key,
            )
            return None

        if raw_value is None:
            return None

        try:
            vector: list[float] = json.loads(raw_value)
            return vector
        except (TypeError, ValueError):
            logger.warning(
                "query_embedding.cache.corrupt_entry",
                key=key,
            )
            return None

    async def set(
        self,
        key: str,
        vector: list[float],
    ) -> None:
        try:
            await self._client.set(
                key,
                json.dumps(vector),
                ex=self._ttl_seconds,
            )
        except Exception:
            logger.exception(
                "query_embedding.cache.write_failed",
                key=key,
            )
