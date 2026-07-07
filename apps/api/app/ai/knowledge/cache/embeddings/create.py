"""
Embedding cache composition root.

Selects and constructs the configured EmbeddingCache implementation.
"""

from __future__ import annotations

from redis.asyncio import Redis

from app.ai.knowledge.cache.embeddings.interfaces import EmbeddingCache
from app.ai.knowledge.cache.embeddings.null import NullEmbeddingCache
from app.ai.knowledge.cache.embeddings.valkey import ValkeyEmbeddingCache
from app.core.settings import settings


def create_embedding_cache() -> EmbeddingCache:
    """
    Create the configured EmbeddingCache.

    Returns a NullEmbeddingCache (fully disabling caching) when
    ``settings.embedding_cache_enabled`` is False.
    """

    if not settings.embedding_cache_enabled:
        return NullEmbeddingCache()

    client = Redis.from_url(
        settings.valkey_url,
        decode_responses=True,
    )

    return ValkeyEmbeddingCache(
        client=client,
        ttl_seconds=settings.embedding_cache_ttl_seconds,
    )
