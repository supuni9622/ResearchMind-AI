from __future__ import annotations

import pytest
from app.ai.tools.web_search.exceptions import (
    WebSearchPolicyError,
    WebSearchProviderUnavailableError,
)
from app.ai.tools.web_search.models import WebSearchRequest
from app.ai.tools.web_search.policies import WebSearchPolicy
from app.ai.tools.web_search.providers.fake import FakeWebSearchProvider
from app.ai.tools.web_search.registry import WebSearchProviderRegistry
from app.ai.tools.web_search.service import WebSearchService


def _service(
    *, enabled: bool = True, provider: FakeWebSearchProvider | None = None, **policy_kwargs
):
    fake = provider if provider is not None else FakeWebSearchProvider()
    registry = WebSearchProviderRegistry([fake])
    policy = WebSearchPolicy(enabled=enabled, **policy_kwargs)
    return WebSearchService(registry=registry, policy=policy, default_provider="fake"), fake


@pytest.mark.asyncio
async def test_search_returns_canonical_result() -> None:
    service, fake = _service()
    result = await service.search(WebSearchRequest(query="latest ai news"))
    assert result.provider == "fake"
    assert len(result.items) == 1
    assert fake.calls[0].query == "latest ai news"


@pytest.mark.asyncio
async def test_disabled_policy_raises_policy_error() -> None:
    service, _ = _service(enabled=False)
    with pytest.raises(WebSearchPolicyError):
        await service.search(WebSearchRequest(query="latest ai news"))


@pytest.mark.asyncio
async def test_unconfigured_provider_raises_unavailable_error() -> None:
    registry = WebSearchProviderRegistry([])
    policy = WebSearchPolicy(enabled=True)
    service = WebSearchService(registry=registry, policy=policy, default_provider="tavily")
    with pytest.raises(WebSearchProviderUnavailableError):
        await service.search(WebSearchRequest(query="latest ai news"))


def test_available_reflects_policy_and_registry() -> None:
    service, _ = _service(enabled=True)
    assert service.available is True

    disabled_service, _ = _service(enabled=False)
    assert disabled_service.available is False

    empty_registry_service = WebSearchService(
        registry=WebSearchProviderRegistry([]),
        policy=WebSearchPolicy(enabled=True),
        default_provider="tavily",
    )
    assert empty_registry_service.available is False


@pytest.mark.asyncio
async def test_duplicate_and_blocked_domains_are_filtered() -> None:
    from app.ai.tools.web_search.models import WebSearchResultItem

    fake = FakeWebSearchProvider(
        items=[
            WebSearchResultItem(
                title="A",
                url="https://good.com/page",
                snippet="s",
                provider="fake",
                domain="good.com",
            ),
            WebSearchResultItem(
                title="A dup",
                url="https://good.com/page/",
                snippet="s",
                provider="fake",
                domain="good.com",
            ),
            WebSearchResultItem(
                title="Blocked",
                url="https://blocked.com/page",
                snippet="s",
                provider="fake",
                domain="blocked.com",
            ),
        ]
    )
    service, _ = _service(provider=fake, blocked_domains=["blocked.com"])
    result = await service.search(WebSearchRequest(query="query text", max_results=10))
    assert [item.domain for item in result.items] == ["good.com"]


@pytest.mark.asyncio
async def test_max_results_per_call_bounds_the_request() -> None:
    service, fake = _service(max_results_per_call=2)
    await service.search(WebSearchRequest(query="query text", max_results=20))
    assert fake.calls[0].max_results == 2
