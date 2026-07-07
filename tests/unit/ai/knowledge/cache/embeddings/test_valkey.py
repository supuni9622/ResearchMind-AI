"""
Unit tests for ValkeyEmbeddingCache.

Covers:
- get_many decodes hits and skips misses/corrupt entries
- get_many/set_many short-circuit on empty input without touching Redis
- get_many/set_many fail open (swallow errors) when Redis raises
- set_many writes every entry through a pipeline with the configured TTL
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from app.ai.knowledge.cache.embeddings.valkey import ValkeyEmbeddingCache


def _make_client() -> AsyncMock:
    return AsyncMock()


async def test_get_many_returns_decoded_vectors_for_hits() -> None:
    client = _make_client()
    client.mget = AsyncMock(return_value=[json.dumps([0.1, 0.2]), None])
    cache = ValkeyEmbeddingCache(client=client, ttl_seconds=60)

    result = await cache.get_many(["key-1", "key-2"])

    assert result == {"key-1": [0.1, 0.2]}
    client.mget.assert_awaited_once_with(["key-1", "key-2"])


async def test_get_many_with_empty_keys_skips_client_call() -> None:
    client = _make_client()
    cache = ValkeyEmbeddingCache(client=client, ttl_seconds=60)

    result = await cache.get_many([])

    assert result == {}
    client.mget.assert_not_called()


async def test_get_many_returns_empty_dict_when_client_raises() -> None:
    client = _make_client()
    client.mget = AsyncMock(side_effect=ConnectionError("down"))
    cache = ValkeyEmbeddingCache(client=client, ttl_seconds=60)

    result = await cache.get_many(["key-1"])

    assert result == {}


async def test_get_many_skips_corrupt_entries() -> None:
    client = _make_client()
    client.mget = AsyncMock(return_value=["not-json"])
    cache = ValkeyEmbeddingCache(client=client, ttl_seconds=60)

    result = await cache.get_many(["key-1"])

    assert result == {}


async def test_set_many_writes_each_entry_with_ttl() -> None:
    client = _make_client()
    pipeline = MagicMock()
    pipeline.execute = AsyncMock()
    client.pipeline = MagicMock(return_value=pipeline)

    cache = ValkeyEmbeddingCache(client=client, ttl_seconds=3600)

    await cache.set_many({"key-1": [0.1, 0.2], "key-2": [0.3]})

    client.pipeline.assert_called_once_with(transaction=False)
    assert pipeline.set.call_count == 2
    pipeline.set.assert_any_call("key-1", json.dumps([0.1, 0.2]), ex=3600)
    pipeline.set.assert_any_call("key-2", json.dumps([0.3]), ex=3600)
    pipeline.execute.assert_awaited_once()


async def test_set_many_with_empty_entries_skips_client_call() -> None:
    client = _make_client()
    cache = ValkeyEmbeddingCache(client=client, ttl_seconds=60)

    await cache.set_many({})

    client.pipeline.assert_not_called()


async def test_set_many_swallows_errors() -> None:
    client = _make_client()
    client.pipeline = MagicMock(side_effect=ConnectionError("down"))
    cache = ValkeyEmbeddingCache(client=client, ttl_seconds=60)

    await cache.set_many({"key-1": [0.1]})
