"""Web Search Tool Platform composition root.

Registers Tavily only when `TAVILY_API_KEY` is configured -- an absent key
degrades `WebSearchService.available` to `False` rather than raising, so a
deployment without web search configured never crashes a research run
(mirrors `create_generation_registry`'s "register only if configured"
pattern in `app.ai.runtime.generation.create`).
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.tools.web_search.interfaces import WebSearchProviderInterface
from app.ai.tools.web_search.policies import WebSearchPolicy
from app.ai.tools.web_search.providers.tavily import TavilyWebSearchProvider
from app.ai.tools.web_search.registry import WebSearchProviderRegistry
from app.ai.tools.web_search.service import WebSearchService
from app.core.settings import settings

DEFAULT_PROVIDER = "tavily"


@lru_cache
def create_web_search_service() -> WebSearchService:
    providers: list[WebSearchProviderInterface] = []
    if settings.tavily_api_key:
        providers.append(
            TavilyWebSearchProvider(
                api_key=settings.tavily_api_key,
                timeout_seconds=settings.web_search_timeout_seconds,
            )
        )

    registry = WebSearchProviderRegistry(providers)
    policy = WebSearchPolicy(
        enabled=settings.web_search_enabled,
        max_search_calls_per_run=settings.web_search_max_calls_per_run,
        max_results_per_call=settings.web_search_max_results_per_call,
        timeout_seconds=settings.web_search_timeout_seconds,
    )
    return WebSearchService(
        registry=registry,
        policy=policy,
        default_provider=DEFAULT_PROVIDER,
    )
