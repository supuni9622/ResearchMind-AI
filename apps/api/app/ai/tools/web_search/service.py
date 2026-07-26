"""`WebSearchService` -- validate, authorize, execute, and normalize a web search
(PRD §13). Framework-independent: callers (e.g. the Research Runtime graph)
depend on this, never on a provider SDK directly.
"""

from __future__ import annotations

from time import perf_counter
from urllib.parse import urlsplit

import structlog

from app.ai.tools.web_search.exceptions import (
    WebSearchPolicyError,
    WebSearchProviderUnavailableError,
)
from app.ai.tools.web_search.models import WebSearchRequest, WebSearchResult, WebSearchResultItem
from app.ai.tools.web_search.policies import WebSearchPolicy
from app.ai.tools.web_search.registry import WebSearchProviderRegistry
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.infrastructure.metrics.noop import NoOpMetricsRecorder
from app.infrastructure.metrics.web_search import (
    WEB_SEARCH_DURATION,
    WEB_SEARCH_FAILURES_TOTAL,
    WEB_SEARCH_REQUESTS_TOTAL,
    WEB_SEARCH_RESULTS_TOTAL,
    WEB_SEARCH_SELECTED_RESULTS_TOTAL,
)

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
        metrics: MetricsRecorder | None = None,
    ) -> None:
        self._registry = registry
        self._policy = policy
        self._default_provider = default_provider
        self._metrics = metrics or NoOpMetricsRecorder()

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

        provider_name = self._default_provider
        started = perf_counter()

        try:
            provider = self._registry.get(provider_name)
            bounded_request = request.model_copy(
                update={
                    "max_results": min(request.max_results, self._policy.max_results_per_call),
                }
            )
            result = await provider.search(bounded_request)
        except Exception as exc:
            self._metrics.increment(
                metric=WEB_SEARCH_REQUESTS_TOTAL,
                labels={"provider": provider_name, "status": "failure"},
            )
            self._metrics.increment(
                metric=WEB_SEARCH_FAILURES_TOTAL,
                labels={"provider": provider_name, "failure_type": type(exc).__name__},
            )
            self._metrics.record_duration(
                operation=WEB_SEARCH_DURATION,
                duration_ms=(perf_counter() - started) * 1000,
                labels={"provider": provider_name},
            )
            raise

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

        self._metrics.increment(
            metric=WEB_SEARCH_REQUESTS_TOTAL,
            labels={"provider": result.provider, "status": "success"},
        )
        self._metrics.increment(
            metric=WEB_SEARCH_RESULTS_TOTAL,
            value=len(result.items),
            labels={"provider": result.provider},
        )
        self._metrics.increment(
            metric=WEB_SEARCH_SELECTED_RESULTS_TOTAL,
            value=len(filtered),
            labels={"provider": result.provider},
        )
        self._metrics.record_duration(
            operation=WEB_SEARCH_DURATION,
            duration_ms=result.duration_ms,
            labels={"provider": result.provider},
        )

        logger.info(
            "web_search.service.search_completed",
            provider=result.provider,
            result_count=len(result.items),
            filtered_count=len(filtered),
            duration_ms=result.duration_ms,
        )
        return result.model_copy(update={"items": filtered})
