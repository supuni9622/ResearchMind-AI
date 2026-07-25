"""Tavily provider  -- REST call via `httpx`, no SDK dependency
(mirrors this codebase's existing direct-`httpx` convention, e.g.
`app/services/auth.py`). Never exposes the raw Tavily payload or API key
past this module.
"""

from __future__ import annotations

from datetime import datetime
from time import perf_counter
from urllib.parse import urlsplit

import httpx
import structlog

from app.ai.tools.web_search.enums import WebSearchDepth
from app.ai.tools.web_search.exceptions import WebSearchProviderError, WebSearchTimeoutError
from app.ai.tools.web_search.interfaces import WebSearchProviderInterface
from app.ai.tools.web_search.models import WebSearchRequest, WebSearchResult, WebSearchResultItem

logger = structlog.get_logger()

_TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def _domain_of(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _parse_published_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class TavilyWebSearchProvider(WebSearchProviderInterface):
    def __init__(self, *, api_key: str, timeout_seconds: float = 20.0) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "tavily"

    async def search(self, request: WebSearchRequest) -> WebSearchResult:
        payload: dict[str, object] = {
            "api_key": self._api_key,
            "query": request.query,
            "max_results": request.max_results,
            "search_depth": (
                "advanced" if request.search_depth is WebSearchDepth.ADVANCED else "basic"
            ),
            "include_raw_content": request.include_raw_content,
        }
        if request.include_domains:
            payload["include_domains"] = request.include_domains
        if request.exclude_domains:
            payload["exclude_domains"] = request.exclude_domains

        started = perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(_TAVILY_SEARCH_URL, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise WebSearchTimeoutError("Tavily search timed out.") from exc
        except httpx.HTTPStatusError as exc:
            # Never include the request payload (carries the API key) in the
            # error -- only the status code is safe to surface.
            raise WebSearchProviderError(
                f"Tavily search failed with status {exc.response.status_code}."
            ) from None
        except httpx.HTTPError as exc:
            raise WebSearchProviderError("Tavily search request failed.") from exc

        duration_ms = (perf_counter() - started) * 1000
        results = data.get("results")
        if not isinstance(results, list):
            raise WebSearchProviderError("Tavily returned an unexpected response payload.")

        items = [
            WebSearchResultItem(
                title=str(result.get("title") or "Untitled"),
                url=str(result.get("url")),
                snippet=str(result.get("content") or ""),
                provider=self.name,
                domain=_domain_of(str(result.get("url") or "")),
                provider_score=(
                    float(result["score"]) if isinstance(result.get("score"), int | float) else None
                ),
                published_at=_parse_published_at(result.get("published_date")),
                raw_content=(
                    str(result["raw_content"]) if result.get("raw_content") is not None else None
                ),
            )
            for result in results
            if result.get("url")
        ]
        return WebSearchResult(
            query=request.query,
            items=items,
            provider=self.name,
            duration_ms=duration_ms,
            request_id=str(data["request_id"]) if data.get("request_id") else None,
        )
