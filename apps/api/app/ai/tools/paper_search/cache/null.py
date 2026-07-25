"""No-op paper search cache (mirrors
`app.ai.knowledge.cache.query_embeddings.null`)."""

from __future__ import annotations

from app.ai.tools.paper_search.cache.interfaces import PaperSearchCache
from app.ai.tools.paper_search.models import PaperSearchResult


class NullPaperSearchCache(PaperSearchCache):
    async def get(self, key: str) -> PaperSearchResult | None:
        return None

    async def set(self, key: str, result: PaperSearchResult) -> None:
        return None
