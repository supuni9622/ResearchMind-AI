from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from app.ai.tools.web_search.exceptions import WebSearchProviderError, WebSearchTimeoutError
from app.ai.tools.web_search.models import WebSearchRequest
from app.ai.tools.web_search.providers.tavily import TavilyWebSearchProvider


def _mock_client(response: MagicMock) -> MagicMock:
    client = AsyncMock()
    client.post.return_value = response
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=False)
    return context


@pytest.mark.asyncio
async def test_search_maps_canonical_request_and_normalizes_response() -> None:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "results": [
            {
                "title": "Recent article",
                "url": "https://example.com/a",
                "content": "Some extracted content.",
                "score": 0.87,
                "published_date": "2026-07-01T00:00:00",
            },
            {"title": "No URL", "content": "dropped"},
        ],
        "request_id": "req-123",
    }

    with patch(
        "app.ai.tools.web_search.providers.tavily.httpx.AsyncClient",
        return_value=_mock_client(response),
    ) as client_cls:
        provider = TavilyWebSearchProvider(api_key="secret-key")
        result = await provider.search(
            WebSearchRequest(query="latest ai news", max_results=5, include_domains=["example.com"])
        )

    assert result.provider == "tavily"
    assert result.request_id == "req-123"
    assert len(result.items) == 1
    item = result.items[0]
    assert item.url == "https://example.com/a"
    assert item.domain == "example.com"
    assert item.provider_score == 0.87
    assert item.published_at is not None

    sent_client = client_cls.return_value.__aenter__.return_value
    payload = sent_client.post.await_args.kwargs["json"]
    assert payload["query"] == "latest ai news"
    assert payload["include_domains"] == ["example.com"]
    assert payload["api_key"] == "secret-key"


@pytest.mark.asyncio
async def test_missing_optional_fields_are_handled() -> None:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"results": [{"url": "https://example.com/a"}]}

    with patch(
        "app.ai.tools.web_search.providers.tavily.httpx.AsyncClient",
        return_value=_mock_client(response),
    ):
        provider = TavilyWebSearchProvider(api_key="secret-key")
        result = await provider.search(WebSearchRequest(query="q about topic"))

    assert result.items[0].title == "Untitled"
    assert result.items[0].snippet == ""
    assert result.items[0].provider_score is None


@pytest.mark.asyncio
async def test_timeout_maps_to_canonical_error() -> None:
    client = AsyncMock()
    client.post.side_effect = httpx.TimeoutException("boom")
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=False)

    with patch("app.ai.tools.web_search.providers.tavily.httpx.AsyncClient", return_value=context):
        provider = TavilyWebSearchProvider(api_key="secret-key")
        with pytest.raises(WebSearchTimeoutError):
            await provider.search(WebSearchRequest(query="q about topic"))


@pytest.mark.asyncio
async def test_auth_failure_maps_cleanly_without_leaking_the_key() -> None:
    request = httpx.Request("POST", "https://api.tavily.com/search")
    error_response = httpx.Response(status_code=401, request=request)
    client = AsyncMock()

    post_response = MagicMock()
    post_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Unauthorized", request=request, response=error_response
    )
    client.post.return_value = post_response
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=False)

    with patch("app.ai.tools.web_search.providers.tavily.httpx.AsyncClient", return_value=context):
        provider = TavilyWebSearchProvider(api_key="super-secret")
        with pytest.raises(WebSearchProviderError) as exc_info:
            await provider.search(WebSearchRequest(query="q about topic"))

    assert "super-secret" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_invalid_payload_fails_safely() -> None:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"unexpected": "shape"}

    with patch(
        "app.ai.tools.web_search.providers.tavily.httpx.AsyncClient",
        return_value=_mock_client(response),
    ):
        provider = TavilyWebSearchProvider(api_key="secret-key")
        with pytest.raises(WebSearchProviderError):
            await provider.search(WebSearchRequest(query="q about topic"))
