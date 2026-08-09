from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.ai.tools.paper_search.cache.interfaces import PaperSearchCache
from app.ai.tools.paper_search.exceptions import (
    PaperSearchPolicyError,
    PaperSearchProviderUnavailableError,
)
from app.ai.tools.paper_search.models import PaperSearchRequest, PaperSearchResult
from app.ai.tools.paper_search.policies import PaperSearchPolicy
from app.ai.tools.paper_search.providers.fake import FakePaperSearchProvider
from app.ai.tools.paper_search.registry import PaperSearchProviderRegistry
from app.ai.tools.paper_search.service import PaperSearchService


class _InMemoryCache(PaperSearchCache):
    def __init__(self) -> None:
        self.store: dict[str, PaperSearchResult] = {}
        self.gets = 0
        self.sets = 0

    async def get(self, key: str) -> PaperSearchResult | None:
        self.gets += 1
        return self.store.get(key)

    async def set(self, key: str, result: PaperSearchResult) -> None:
        self.sets += 1
        self.store[key] = result


class _AlwaysMissCache(PaperSearchCache):
    async def get(self, key: str) -> PaperSearchResult | None:
        return None

    async def set(self, key: str, result: PaperSearchResult) -> None:
        return None


def _service(
    *,
    enabled: bool = True,
    provider: FakePaperSearchProvider | None = None,
    cache: PaperSearchCache | None = None,
    **policy_kwargs,
):
    fake = provider if provider is not None else FakePaperSearchProvider()
    registry = PaperSearchProviderRegistry([fake])
    policy = PaperSearchPolicy(enabled=enabled, **policy_kwargs)
    service = PaperSearchService(
        registry=registry,
        policy=policy,
        default_provider="fake",
        cache=cache if cache is not None else _AlwaysMissCache(),
    )
    return service, fake


@pytest.mark.asyncio
async def test_search_returns_canonical_result() -> None:
    service, fake = _service()
    result = await service.search(PaperSearchRequest(query="retrieval augmented generation"))
    assert result.provider == "fake"
    assert len(result.items) == 1
    assert fake.calls[0].query == "retrieval augmented generation"
    assert fake.calls[0].year_from == datetime.now(UTC).year - 1
    assert fake.calls[0].year_to == datetime.now(UTC).year


@pytest.mark.asyncio
async def test_explicit_year_range_overrides_recent_two_year_default() -> None:
    service, fake = _service()
    await service.search(
        PaperSearchRequest(query="retrieval augmented generation", year_from=2018, year_to=2020)
    )
    assert fake.calls[0].year_from == 2018
    assert fake.calls[0].year_to == 2020


@pytest.mark.asyncio
async def test_disabled_policy_raises_policy_error() -> None:
    service, _ = _service(enabled=False)
    with pytest.raises(PaperSearchPolicyError):
        await service.search(PaperSearchRequest(query="retrieval augmented generation"))


@pytest.mark.asyncio
async def test_unconfigured_provider_raises_unavailable_error() -> None:
    registry = PaperSearchProviderRegistry([])
    policy = PaperSearchPolicy(enabled=True)
    service = PaperSearchService(
        registry=registry,
        policy=policy,
        default_provider="research_intelligence_mcp",
        cache=_AlwaysMissCache(),
    )
    with pytest.raises(PaperSearchProviderUnavailableError):
        await service.search(PaperSearchRequest(query="retrieval augmented generation"))


def test_available_reflects_policy_and_registry() -> None:
    service, _ = _service(enabled=True)
    assert service.available is True

    disabled_service, _ = _service(enabled=False)
    assert disabled_service.available is False

    empty_registry_service = PaperSearchService(
        registry=PaperSearchProviderRegistry([]),
        policy=PaperSearchPolicy(enabled=True),
        default_provider="research_intelligence_mcp",
        cache=_AlwaysMissCache(),
    )
    assert empty_registry_service.available is False


@pytest.mark.asyncio
async def test_max_results_per_call_bounds_the_request() -> None:
    service, fake = _service(max_results_per_call=2)
    await service.search(PaperSearchRequest(query="retrieval augmented generation", max_results=20))
    assert fake.calls[0].max_results == 2


@pytest.mark.asyncio
async def test_cache_hit_skips_the_provider_call() -> None:
    cache = _InMemoryCache()
    service, fake = _service(cache=cache)

    first = await service.search(PaperSearchRequest(query="retrieval augmented generation"))
    second = await service.search(PaperSearchRequest(query="retrieval augmented generation"))

    assert len(fake.calls) == 1
    assert second == first
    assert cache.sets == 1


@pytest.mark.asyncio
async def test_different_queries_do_not_share_a_cache_entry() -> None:
    cache = _InMemoryCache()
    service, fake = _service(cache=cache)

    await service.search(PaperSearchRequest(query="retrieval augmented generation"))
    await service.search(PaperSearchRequest(query="hybrid retrieval"))

    assert len(fake.calls) == 2


@pytest.mark.asyncio
async def test_empty_results_are_not_cached() -> None:
    cache = _InMemoryCache()
    provider = FakePaperSearchProvider(items=[])
    service, fake = _service(provider=provider, cache=cache)

    await service.search(PaperSearchRequest(query="large language models"))
    await service.search(PaperSearchRequest(query="large language models"))

    assert len(fake.calls) == 2
    assert cache.sets == 0
