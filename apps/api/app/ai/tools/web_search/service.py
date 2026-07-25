"""`WebSearchService` -- validate, authorize, execute, and normalize a web search
(PRD §13). Framework-independent: callers (e.g. the Research Runtime graph)
depend on this, never on a provider SDK directly.
"""

from __future__ import annotations

from urllib.parse import urlsplit

import structlog

from app.ai.tools.web_search.exceptions import (
    WebSearchPolicyError,
    WebSearchProviderUnavailableError,
)
from app.ai.tools.web_search.models import WebSearchRequest, WebSearchResult, WebSearchResultItem
from app.ai.tools.web_search.policies import WebSearchPolicy
from app.ai.tools.web_search.registry import WebSearchProviderRegistry

logger = structlog.get_logger()


def _domain_of(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _canonical_url(url: str) -> str:
    """Strip a trailing slash and fragment so obviously-duplicate URLs
    (`/page` vs `/page/`) dedupe; deliberately not a full canonicalizer."""

    split = urlsplit(url)
    path = split.path.rstrip("/") or "/"
    return f"{split.scheme}://{split.netloc}{path}"


class WebSearchService:
    def __init__(
        self,
        *,
        registry: WebSearchProviderRegistry,
        policy: WebSearchPolicy,
        default_provider: str,
    ) -> None:
        self._registry = registry
        self._policy = policy
        self._default_provider = default_provider

    @property
    def policy(self) -> WebSearchPolicy:
        return self._policy

    @property
    def available(self) -> bool:
        """False when the platform is disabled or no provider is configured
        (e.g. a missing API key) -- callers must treat this as "web search
        is inert here", never raise."""

        return self._policy.enabled and self._registry.has(self._default_provider)

    async def search(self, request: WebSearchRequest) -> WebSearchResult:
        if not self._policy.enabled:
            raise WebSearchPolicyError("Web search is disabled by policy.")
        if not self._registry.has(self._default_provider):
            raise WebSearchProviderUnavailableError(
                f"Web search provider '{self._default_provider}' is not configured."
            )

        provider = self._registry.get(self._default_provider)
        bounded_request = request.model_copy(
            update={
                "max_results": min(request.max_results, self._policy.max_results_per_call),
            }
        )
        result = await provider.search(bounded_request)

        seen_urls: set[str] = set()
        filtered: list[WebSearchResultItem] = []
        for item in result.items:
            domain = item.domain or _domain_of(item.url)
            if not self._policy.domain_allowed(domain):
                continue
            canonical = _canonical_url(item.url)
            if canonical in seen_urls:
                continue
            seen_urls.add(canonical)
            filtered.append(item)

        logger.info(
            "web_search.service.search_completed",
            provider=result.provider,
            result_count=len(result.items),
            filtered_count=len(filtered),
            duration_ms=result.duration_ms,
        )
        return result.model_copy(update={"items": filtered})
