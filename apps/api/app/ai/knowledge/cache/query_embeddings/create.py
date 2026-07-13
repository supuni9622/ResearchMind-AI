"""
Query embedding cache composition root.

Selects and constructs the configured QueryEmbeddingCache implementation.
"""

from __future__ import annotations

from redis.asyncio import Redis

from app.ai.knowledge.cache.query_embeddings.interfaces import (
    QueryEmbeddingCache,
)
from app.ai.knowledge.cache.query_embeddings.null import (
    NullQueryEmbeddingCache,
)
from app.ai.knowledge.cache.query_embeddings.valkey import (
    ValkeyQueryEmbeddingCache,
)
from app.core.settings import settings


def create_query_embedding_cache() -> QueryEmbeddingCache:
    """
    Create the configured QueryEmbeddingCache.

    Returns a NullQueryEmbeddingCache (fully disabling caching) when
    ``settings.query_embedding_cache_enabled`` is False.
    """

    if not settings.query_embedding_cache_enabled:
        return NullQueryEmbeddingCache()

    client = Redis.from_url(
        settings.valkey_url,
        decode_responses=True,
    )

    return ValkeyQueryEmbeddingCache(
        client=client,
        ttl_seconds=settings.query_embedding_cache_ttl_seconds,
    )
