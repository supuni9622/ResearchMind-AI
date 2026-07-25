"""Paper search cache composition root (mirrors
`app.ai.knowledge.cache.query_embeddings.create`)."""

from __future__ import annotations

from redis.asyncio import Redis

from app.ai.tools.paper_search.cache.interfaces import PaperSearchCache
from app.ai.tools.paper_search.cache.null import NullPaperSearchCache
from app.ai.tools.paper_search.cache.valkey import ValkeyPaperSearchCache
from app.core.settings import settings


def create_paper_search_cache() -> PaperSearchCache:
    """Return a NullPaperSearchCache (fully disabling caching) when
    `settings.mcp_papers_cache_enabled` is False."""

    if not settings.mcp_papers_cache_enabled:
        return NullPaperSearchCache()

    client = Redis.from_url(settings.valkey_url, decode_responses=True)
    return ValkeyPaperSearchCache(client=client, ttl_seconds=settings.mcp_papers_cache_ttl_seconds)
