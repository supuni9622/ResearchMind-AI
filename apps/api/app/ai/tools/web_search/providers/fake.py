"""Deterministic fake provider for tests -- never makes a network call."""

from __future__ import annotations

from app.ai.tools.web_search.interfaces import WebSearchProviderInterface
from app.ai.tools.web_search.models import WebSearchRequest, WebSearchResult, WebSearchResultItem


class FakeWebSearchProvider(WebSearchProviderInterface):
    def __init__(self, *, items: list[WebSearchResultItem] | None = None) -> None:
        self._items = items
        self.calls: list[WebSearchRequest] = []

    @property
    def name(self) -> str:
        return "fake"

    async def search(self, request: WebSearchRequest) -> WebSearchResult:
        self.calls.append(request)
        items = (
            self._items
            if self._items is not None
            else [
                WebSearchResultItem(
                    title=f"Result for {request.query}",
                    url="https://example.com/article",
                    snippet="A fake search result snippet.",
                    provider=self.name,
                    domain="example.com",
                    provider_score=0.9,
                )
            ]
        )
        return WebSearchResult(
            query=request.query,
            items=items[: request.max_results],
            provider=self.name,
            duration_ms=1.0,
        )
