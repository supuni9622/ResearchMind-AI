"""
Unit tests for ValkeyPaperSearchCache and build_paper_search_cache_key.

Covers:
- get decodes a hit and returns None for a miss
- get fails open (returns None) when Redis raises or the entry is corrupt
- set writes the JSON-encoded result through with the configured TTL
- set fails open (swallows errors) when Redis raises
- key builder is deterministic and query/max_results sensitive
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from app.ai.tools.paper_search.cache.key import build_paper_search_cache_key
from app.ai.tools.paper_search.cache.valkey import ValkeyPaperSearchCache
from app.ai.tools.paper_search.models import PaperSearchResult, PaperSearchResultItem


def _result() -> PaperSearchResult:
    return PaperSearchResult(
        query="retrieval augmented generation",
        items=[PaperSearchResultItem(title="A Paper", authors=["A. Author"])],
        provider="research_intelligence_mcp",
        duration_ms=12.5,
    )


async def test_get_returns_decoded_result_for_a_hit() -> None:
    client = AsyncMock()
    result = _result()
    client.get = AsyncMock(return_value=result.model_dump_json())
    cache = ValkeyPaperSearchCache(client=client, ttl_seconds=60)

    cached = await cache.get("key-1")

    assert cached == result
    client.get.assert_awaited_once_with("key-1")


async def test_get_returns_none_for_a_miss() -> None:
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    cache = ValkeyPaperSearchCache(client=client, ttl_seconds=60)

    assert await cache.get("key-1") is None


async def test_get_returns_none_when_client_raises() -> None:
    client = AsyncMock()
    client.get = AsyncMock(side_effect=ConnectionError("down"))
    cache = ValkeyPaperSearchCache(client=client, ttl_seconds=60)

    assert await cache.get("key-1") is None


async def test_get_returns_none_for_a_corrupt_entry() -> None:
    client = AsyncMock()
    client.get = AsyncMock(return_value="not-json")
    cache = ValkeyPaperSearchCache(client=client, ttl_seconds=60)

    assert await cache.get("key-1") is None


async def test_set_writes_the_result_with_ttl() -> None:
    client = AsyncMock()
    client.set = AsyncMock()
    cache = ValkeyPaperSearchCache(client=client, ttl_seconds=3600)
    result = _result()

    await cache.set("key-1", result)

    client.set.assert_awaited_once_with("key-1", result.model_dump_json(), ex=3600)


async def test_set_swallows_errors() -> None:
    client = AsyncMock()
    client.set = AsyncMock(side_effect=ConnectionError("down"))
    cache = ValkeyPaperSearchCache(client=client, ttl_seconds=60)

    await cache.set("key-1", _result())


def test_key_builder_is_deterministic() -> None:
    key_a = build_paper_search_cache_key(query="retrieval augmented generation", max_results=5)
    key_b = build_paper_search_cache_key(query="retrieval augmented generation", max_results=5)
    assert key_a == key_b
    assert key_a.startswith("paper_search:")


def test_key_builder_distinguishes_query_and_max_results() -> None:
    base = build_paper_search_cache_key(query="retrieval augmented generation", max_results=5)
    different_query = build_paper_search_cache_key(query="hybrid retrieval", max_results=5)
    different_limit = build_paper_search_cache_key(
        query="retrieval augmented generation", max_results=10
    )
    assert base != different_query
    assert base != different_limit


def test_key_builder_distinguishes_year_ranges() -> None:
    recent = build_paper_search_cache_key(
        query="earthquakes", max_results=5, year_from=2025, year_to=2026
    )
    historical = build_paper_search_cache_key(
        query="earthquakes", max_results=5, year_from=2010, year_to=2015
    )
    assert recent != historical
