"""
Unit tests for NullEmbeddingCache.

Covers:
- get_many always reports a full miss
- set_many is a no-op
"""

from __future__ import annotations

from app.ai.knowledge.cache.embeddings.null import NullEmbeddingCache


async def test_get_many_always_misses() -> None:
    cache = NullEmbeddingCache()

    result = await cache.get_many(["key-1", "key-2"])

    assert result == {}


async def test_set_many_does_not_raise() -> None:
    cache = NullEmbeddingCache()

    await cache.set_many({"key-1": [0.1, 0.2]})
