"""
Unit tests for NullQueryEmbeddingCache.

Covers:
- get always reports a miss
- set is a no-op
"""

from __future__ import annotations

from app.ai.knowledge.cache.query_embeddings.null import NullQueryEmbeddingCache


async def test_get_always_misses() -> None:
    cache = NullQueryEmbeddingCache()

    result = await cache.get("key-1")

    assert result is None


async def test_set_does_not_raise() -> None:
    cache = NullQueryEmbeddingCache()

    await cache.set("key-1", [0.1, 0.2])
