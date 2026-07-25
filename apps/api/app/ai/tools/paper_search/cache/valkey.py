"""Valkey-backed paper search result cache.

Stores each cached `PaperSearchResult` as JSON under a namespaced key with a
configurable expiration. Cache reads and writes fail open: if Valkey is
unreachable or returns an error, the failure is logged and treated as a full
cache miss rather than propagated -- paper search must never depend on the
cache being available (mirrors
`app.ai.knowledge.cache.query_embeddings.valkey.ValkeyQueryEmbeddingCache`).
"""

from __future__ import annotations

import structlog
from redis.asyncio import Redis

from app.ai.tools.paper_search.cache.interfaces import PaperSearchCache
from app.ai.tools.paper_search.models import PaperSearchResult

logger = structlog.get_logger()


class ValkeyPaperSearchCache(PaperSearchCache):
    def __init__(self, client: Redis, *, ttl_seconds: int) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    async def get(self, key: str) -> PaperSearchResult | None:
        try:
            raw_value = await self._client.get(key)
        except Exception:
            logger.exception("paper_search.cache.read_failed", key=key)
            return None

        if raw_value is None:
            return None

        try:
            return PaperSearchResult.model_validate_json(raw_value)
        except ValueError:
            logger.warning("paper_search.cache.corrupt_entry", key=key)
            return None

    async def set(self, key: str, result: PaperSearchResult) -> None:
        try:
            await self._client.set(
                key,
                result.model_dump_json(),
                ex=self._ttl_seconds,
            )
        except Exception:
            logger.exception("paper_search.cache.write_failed", key=key)
