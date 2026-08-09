from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.ai.tools.paper_search.exceptions import PaperSearchProviderError
from app.ai.tools.paper_search.models import PaperSearchRequest
from app.ai.tools.paper_search.providers.mcp_client import ResearchIntelligenceMCPProvider


def _transport_context() -> MagicMock:
    """Mocks the `async with streamablehttp_client(...) as (read, write, _):`
    call site -- an async context manager yielding a 3-tuple."""

    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock(), MagicMock()))
    context.__aexit__ = AsyncMock(return_value=False)
    return context


def _session_context(call_tool_result: MagicMock) -> tuple[MagicMock, AsyncMock]:
    """Mocks `async with ClientSession(read, write) as session:`."""

    session = AsyncMock()
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock(return_value=call_tool_result)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)
    return context, session


def _call_tool_result(*, is_error: bool = False, structured: dict | None = None) -> MagicMock:
    result = MagicMock()
    result.isError = is_error
    result.structuredContent = structured
    return result


@pytest.mark.asyncio
async def test_search_maps_structured_content_into_canonical_items() -> None:
    """Shape confirmed against a live Research Intelligence MCP server
    (2026-07-25): locator/id fields are nested under `access`/`identifiers`,
    not flat -- `url` was silently coming back `None` in production before
    this was fixed to match reality rather than a guessed flat shape."""

    call_result = _call_tool_result(
        structured={
            "papers": [
                {
                    "title": "Retrieval Augmented Generation",
                    "authors": [{"name": "A. Author"}, "B. Author"],
                    "year": 2024,
                    "venue": "NeurIPS",
                    "abstract": "An abstract.",
                    "identifiers": {
                        "doi": "10.1/abc",
                        "semantic_scholar_id": "abc123",
                        "arxiv_id": None,
                        "corpus_id": None,
                        "pmid": None,
                    },
                    "access": {
                        "status": "open_access",
                        "landing_page_url": "https://example.com/paper",
                        "pdf_url": "https://example.com/paper.pdf",
                        "license": None,
                        "repository": None,
                    },
                },
                {"no_title": "dropped"},
            ]
        }
    )
    session_context, session = _session_context(call_result)

    with (
        patch(
            "app.ai.tools.paper_search.providers.mcp_client.streamablehttp_client",
            return_value=_transport_context(),
        ),
        patch(
            "app.ai.tools.paper_search.providers.mcp_client.ClientSession",
            return_value=session_context,
        ),
    ):
        provider = ResearchIntelligenceMCPProvider(server_url="http://127.0.0.1:8080/mcp")
        result = await provider.search(
            PaperSearchRequest(query="retrieval augmented generation", year_from=2025, year_to=2026)
        )

    assert result.provider == "research_intelligence_mcp"
    assert len(result.items) == 1
    item = result.items[0]
    assert item.title == "Retrieval Augmented Generation"
    assert item.authors == ["A. Author", "B. Author"]
    assert item.year == 2024
    assert item.url == "https://example.com/paper"
    assert item.doi == "10.1/abc"
    assert item.external_id == "abc123"

    session.initialize.assert_awaited_once()
    session.call_tool.assert_awaited_once_with(
        "search_papers",
        {
            "query": "retrieval augmented generation",
            "limit": 5,
            "year_from": 2025,
            "year_to": 2026,
        },
    )


@pytest.mark.asyncio
async def test_search_falls_back_to_flat_fields_for_a_different_provider_shape() -> None:
    """Defensive fallback -- not the confirmed live shape, but keeps parsing
    resilient if a future/alternate provider returns flat fields instead."""

    call_result = _call_tool_result(
        structured={
            "papers": [
                {
                    "title": "Flat Shape Paper",
                    "authors": ["C. Author"],
                    "url": "https://example.com/flat",
                    "doi": "10.2/flat",
                    "paperId": "flat123",
                }
            ]
        }
    )
    session_context, _ = _session_context(call_result)

    with (
        patch(
            "app.ai.tools.paper_search.providers.mcp_client.streamablehttp_client",
            return_value=_transport_context(),
        ),
        patch(
            "app.ai.tools.paper_search.providers.mcp_client.ClientSession",
            return_value=session_context,
        ),
    ):
        provider = ResearchIntelligenceMCPProvider(server_url="http://127.0.0.1:8080/mcp")
        result = await provider.search(PaperSearchRequest(query="retrieval augmented generation"))

    item = result.items[0]
    assert item.url == "https://example.com/flat"
    assert item.doi == "10.2/flat"
    assert item.external_id == "flat123"


@pytest.mark.asyncio
async def test_error_result_raises_provider_error() -> None:
    call_result = _call_tool_result(is_error=True, structured={})
    session_context, _ = _session_context(call_result)

    with (
        patch(
            "app.ai.tools.paper_search.providers.mcp_client.streamablehttp_client",
            return_value=_transport_context(),
        ),
        patch(
            "app.ai.tools.paper_search.providers.mcp_client.ClientSession",
            return_value=session_context,
        ),
    ):
        provider = ResearchIntelligenceMCPProvider(server_url="http://127.0.0.1:8080/mcp")
        with pytest.raises(PaperSearchProviderError):
            await provider.search(PaperSearchRequest(query="retrieval augmented generation"))


@pytest.mark.asyncio
async def test_missing_structured_content_raises_provider_error() -> None:
    call_result = _call_tool_result(is_error=False, structured=None)
    session_context, _ = _session_context(call_result)

    with (
        patch(
            "app.ai.tools.paper_search.providers.mcp_client.streamablehttp_client",
            return_value=_transport_context(),
        ),
        patch(
            "app.ai.tools.paper_search.providers.mcp_client.ClientSession",
            return_value=session_context,
        ),
    ):
        provider = ResearchIntelligenceMCPProvider(server_url="http://127.0.0.1:8080/mcp")
        with pytest.raises(PaperSearchProviderError):
            await provider.search(PaperSearchRequest(query="retrieval augmented generation"))


@pytest.mark.asyncio
async def test_transport_failure_never_leaks_auth_token() -> None:
    with patch(
        "app.ai.tools.paper_search.providers.mcp_client.streamablehttp_client",
        side_effect=ConnectionError("connection reset by super-secret-token-holder"),
    ):
        provider = ResearchIntelligenceMCPProvider(
            server_url="http://127.0.0.1:8080/mcp", auth_token="super-secret-token"
        )
        with pytest.raises(PaperSearchProviderError) as exc_info:
            await provider.search(PaperSearchRequest(query="retrieval augmented generation"))

    assert "super-secret-token" not in str(exc_info.value)
