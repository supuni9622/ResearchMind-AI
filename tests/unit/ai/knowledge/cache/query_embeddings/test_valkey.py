"""
Unit tests for ValkeyQueryEmbeddingCache.

Covers:
- get decodes a hit and returns None for a miss
- get fails open (returns None) when Redis raises or the entry is corrupt
- set writes the vector through with the configured TTL
- set fails open (swallows errors) when Redis raises
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

from app.ai.knowledge.cache.query_embeddings.valkey import ValkeyQueryEmbeddingCache


def _make_client() -> AsyncMock:
    return AsyncMock()


async def test_get_returns_decoded_vector_for_a_hit() -> None:
    client = _make_client()
    client.get = AsyncMock(return_value=json.dumps([0.1, 0.2]))
    cache = ValkeyQueryEmbeddingCache(client=client, ttl_seconds=60)

    result = await cache.get("key-1")

    assert result == [0.1, 0.2]
    client.get.assert_awaited_once_with("key-1")


async def test_get_returns_none_for_a_miss() -> None:
    client = _make_client()
    client.get = AsyncMock(return_value=None)
    cache = ValkeyQueryEmbeddingCache(client=client, ttl_seconds=60)

    result = await cache.get("key-1")

    assert result is None


async def test_get_returns_none_when_client_raises() -> None:
    client = _make_client()
    client.get = AsyncMock(side_effect=ConnectionError("down"))
    cache = ValkeyQueryEmbeddingCache(client=client, ttl_seconds=60)

    result = await cache.get("key-1")

    assert result is None


async def test_get_returns_none_for_a_corrupt_entry() -> None:
    client = _make_client()
    client.get = AsyncMock(return_value="not-json")
    cache = ValkeyQueryEmbeddingCache(client=client, ttl_seconds=60)

    result = await cache.get("key-1")

    assert result is None


async def test_set_writes_the_vector_with_ttl() -> None:
    client = _make_client()
    client.set = AsyncMock()
    cache = ValkeyQueryEmbeddingCache(client=client, ttl_seconds=3600)

    await cache.set("key-1", [0.1, 0.2])

    client.set.assert_awaited_once_with("key-1", json.dumps([0.1, 0.2]), ex=3600)


async def test_set_swallows_errors() -> None:
    client = _make_client()
    client.set = AsyncMock(side_effect=ConnectionError("down"))
    cache = ValkeyQueryEmbeddingCache(client=client, ttl_seconds=60)

    await cache.set("key-1", [0.1])
