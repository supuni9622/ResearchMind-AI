"""Paper search result cache interface (mirrors
`app.ai.knowledge.cache.query_embeddings.interfaces`)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.tools.paper_search.models import PaperSearchResult


class PaperSearchCache(ABC):
    @abstractmethod
    async def get(self, key: str) -> PaperSearchResult | None:
        """Return a cached result, or None on a miss."""

    @abstractmethod
    async def set(self, key: str, result: PaperSearchResult) -> None:
        """Store a result."""
