"""Deterministic fake provider for tests -- never makes a network call
(mirrors `app.ai.tools.web_search.providers.fake`)."""

from __future__ import annotations

from app.ai.tools.paper_search.interfaces import PaperSearchProviderInterface
from app.ai.tools.paper_search.models import (
    PaperSearchRequest,
    PaperSearchResult,
    PaperSearchResultItem,
)


class FakePaperSearchProvider(PaperSearchProviderInterface):
    def __init__(self, *, items: list[PaperSearchResultItem] | None = None) -> None:
        self._items = items
        self.calls: list[PaperSearchRequest] = []

    @property
    def name(self) -> str:
        return "fake"

    async def search(self, request: PaperSearchRequest) -> PaperSearchResult:
        self.calls.append(request)
        items = (
            self._items
            if self._items is not None
            else [
                PaperSearchResultItem(
                    title=f"Paper about {request.query}",
                    authors=["A. Researcher"],
                    year=2025,
                    venue="Fake Venue",
                    url="https://example.com/paper",
                    doi=None,
                    abstract="A fake paper abstract.",
                    external_id="fake-1",
                )
            ]
        )
        return PaperSearchResult(
            query=request.query,
            items=items[: request.max_results],
            provider=self.name,
            duration_ms=1.0,
        )
