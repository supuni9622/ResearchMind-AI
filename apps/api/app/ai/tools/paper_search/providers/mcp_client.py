"""Research Intelligence MCP provider -- calls the `search_papers` tool of an
external MCP server over `streamable-http` (prds/3. mcp_server_setup.md,
Path B). Opens a fresh session per call (mirrors the setup guide's B.2/B.3
examples) rather than holding a persistent connection -- simplest, safest
default for a call that happens at most once per Chat turn / Deep Research
run, and `PaperSearchService`'s cache absorbs repeat queries.

Deliberately the lean scope: a single tool (`search_papers`), an optional
static bearer token (no service-token provider/JWT refresh), no
retry-with-backoff -- callers (`run_chat_paper_search`,
`suggest_related_papers`) are already best-effort and degrade on any
exception. Never exposes the raw MCP result object or the bearer token past
this module (mirrors `app.ai.tools.web_search.providers.tavily`).
"""

from __future__ import annotations

from time import perf_counter
from typing import Any

import structlog
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult

from app.ai.tools.paper_search.exceptions import PaperSearchProviderError, PaperSearchTimeoutError
from app.ai.tools.paper_search.interfaces import PaperSearchProviderInterface
from app.ai.tools.paper_search.models import (
    PaperSearchRequest,
    PaperSearchResult,
    PaperSearchResultItem,
)

logger = structlog.get_logger()

_SEARCH_TOOL_NAME = "search_papers"
# Candidate keys the MCP server's `search_papers` structured output might use
# for the list of papers -- no published schema exists in this repo yet, so
# this stays deliberately lenient rather than pinned to one exact shape.
_RESULT_LIST_KEYS = ("papers", "results", "items")


def _first_list(payload: dict[str, Any]) -> list[Any]:
    for key in _RESULT_LIST_KEYS:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    raise PaperSearchProviderError(
        "Research Intelligence MCP returned an unexpected search_papers payload shape."
    )


def _item_from_payload(item: dict[str, Any]) -> PaperSearchResultItem | None:
    title = item.get("title")
    if not title:
        return None
    authors_raw = item.get("authors") or []
    authors = [str(a.get("name")) if isinstance(a, dict) else str(a) for a in authors_raw if a]

    # The Research Intelligence MCP server nests locator/id fields rather
    # than exposing them flat (confirmed against a live server, 2026-07-25):
    # `access.{landing_page_url,pdf_url}` for the URL, `identifiers.*` for
    # doi/arxiv/semantic-scholar/corpus ids. A few flat fallbacks are kept
    # for robustness against a future/alternate provider shape.
    access_raw = item.get("access")
    access: dict[str, Any] = access_raw if isinstance(access_raw, dict) else {}
    identifiers_raw = item.get("identifiers")
    identifiers: dict[str, Any] = identifiers_raw if isinstance(identifiers_raw, dict) else {}

    url = (
        access.get("landing_page_url")
        or access.get("pdf_url")
        or item.get("url")
        or item.get("landing_page_url")
    )
    doi = identifiers.get("doi") or item.get("doi")
    external_id = (
        identifiers.get("semantic_scholar_id")
        or identifiers.get("corpus_id")
        or identifiers.get("arxiv_id")
        or item.get("paperId")
        or item.get("paper_id")
        or item.get("id")
    )

    return PaperSearchResultItem(
        title=str(title),
        authors=authors,
        year=item.get("year") if isinstance(item.get("year"), int) else None,
        venue=str(item["venue"]) if item.get("venue") else None,
        url=str(url) if url else None,
        doi=str(doi) if doi else None,
        abstract=str(item["abstract"]) if item.get("abstract") else None,
        external_id=str(external_id) if external_id else None,
    )


def _parse_structured_content(structured: dict[str, Any]) -> list[PaperSearchResultItem]:
    raw_items = _first_list(structured)
    items: list[PaperSearchResultItem] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        item = _item_from_payload(raw)
        if item is not None:
            items.append(item)
    return items


class ResearchIntelligenceMCPProvider(PaperSearchProviderInterface):
    def __init__(
        self,
        *,
        server_url: str,
        auth_token: str | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._server_url = server_url
        self._auth_token = auth_token
        self._timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "research_intelligence_mcp"

    async def search(self, request: PaperSearchRequest) -> PaperSearchResult:
        headers = {"Authorization": f"Bearer {self._auth_token}"} if self._auth_token else None

        started = perf_counter()
        try:
            async with (
                streamablehttp_client(
                    self._server_url,
                    headers=headers,
                    timeout=self._timeout_seconds,
                ) as (read, write, _get_session_id),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                result: CallToolResult = await session.call_tool(
                    _SEARCH_TOOL_NAME,
                    {"query": request.query, "limit": request.max_results},
                )
        except TimeoutError as exc:
            raise PaperSearchTimeoutError("Research Intelligence MCP search timed out.") from exc
        except PaperSearchProviderError:
            raise
        except Exception as exc:
            # Never surface the raw exception (may embed the server URL/token
            # in a connection-error message) -- only the type crosses this
            # boundary, mirroring `TavilyWebSearchProvider`'s error handling.
            raise PaperSearchProviderError(
                f"Research Intelligence MCP search_papers call failed: {type(exc).__name__}"
            ) from None

        duration_ms = (perf_counter() - started) * 1000

        if result.isError:
            raise PaperSearchProviderError(
                "Research Intelligence MCP search_papers returned an error."
            )

        structured = result.structuredContent
        if not isinstance(structured, dict):
            raise PaperSearchProviderError(
                "Research Intelligence MCP search_papers returned no structured content."
            )

        items = _parse_structured_content(structured)
        return PaperSearchResult(
            query=request.query,
            items=items[: request.max_results],
            provider=self.name,
            duration_ms=duration_ms,
        )
