"""`PaperSearchService` -- validate, authorize, cache, and execute a paper
search. Framework-independent: callers (Chat, the Research Runtime graph)
depend on this, never on a provider SDK directly (mirrors
`app.ai.tools.web_search.service.WebSearchService`).
"""

from __future__ import annotations

import structlog

from app.ai.tools.paper_search.cache.interfaces import PaperSearchCache
from app.ai.tools.paper_search.cache.key import build_paper_search_cache_key
from app.ai.tools.paper_search.exceptions import (
    PaperSearchPolicyError,
    PaperSearchProviderUnavailableError,
)
from app.ai.tools.paper_search.models import PaperSearchRequest, PaperSearchResult
from app.ai.tools.paper_search.policies import PaperSearchPolicy
from app.ai.tools.paper_search.registry import PaperSearchProviderRegistry

logger = structlog.get_logger()


class PaperSearchService:
    def __init__(
        self,
        *,
        registry: PaperSearchProviderRegistry,
        policy: PaperSearchPolicy,
        default_provider: str,
        cache: PaperSearchCache,
    ) -> None:
        self._registry = registry
        self._policy = policy
        self._default_provider = default_provider
        self._cache = cache

    @property
    def policy(self) -> PaperSearchPolicy:
        return self._policy

    @property
    def available(self) -> bool:
        """False when the platform is disabled or no provider is configured
        (e.g. a missing server URL) -- callers must treat this as "paper
        search is inert here", never raise."""

        return self._policy.enabled and self._registry.has(self._default_provider)

    async def search(self, request: PaperSearchRequest) -> PaperSearchResult:
        if not self._policy.enabled:
            raise PaperSearchPolicyError("Paper search is disabled by policy.")
        if not self._registry.has(self._default_provider):
            raise PaperSearchProviderUnavailableError(
                f"Paper search provider '{self._default_provider}' is not configured."
            )

        bounded_max_results = min(request.max_results, self._policy.max_results_per_call)
        cache_key = build_paper_search_cache_key(
            query=request.query, max_results=bounded_max_results
        )

        cached = await self._cache.get(cache_key)
        if cached is not None:
            logger.info(
                "paper_search.service.cache_hit",
                provider=cached.provider,
                result_count=len(cached.items),
            )
            return cached

        provider = self._registry.get(self._default_provider)
        bounded_request = request.model_copy(update={"max_results": bounded_max_results})
        result = await provider.search(bounded_request)

        logger.info(
            "paper_search.service.search_completed",
            provider=result.provider,
            result_count=len(result.items),
            duration_ms=result.duration_ms,
        )

        await self._cache.set(cache_key, result)
        return result
