"""Research Intelligence MCP (paper search) Tool Platform composition root.

Registers the MCP provider only when `mcp_papers_server_url` is configured --
an absent URL degrades `PaperSearchService.available` to `False` rather than
raising, so a deployment without the MCP server configured never crashes
Chat or Deep Research (mirrors `app.ai.tools.web_search.create`'s
"register only if configured" pattern).
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.observability.prometheus.create import get_metrics_recorder
from app.ai.tools.paper_search.cache.create import create_paper_search_cache
from app.ai.tools.paper_search.interfaces import PaperSearchProviderInterface
from app.ai.tools.paper_search.policies import PaperSearchPolicy
from app.ai.tools.paper_search.providers.mcp_client import ResearchIntelligenceMCPProvider
from app.ai.tools.paper_search.registry import PaperSearchProviderRegistry
from app.ai.tools.paper_search.service import PaperSearchService
from app.core.settings import settings
from app.infrastructure.metrics.mcp import MCP_SERVER_HEALTH

DEFAULT_PROVIDER = "research_intelligence_mcp"


@lru_cache
def create_paper_search_service() -> PaperSearchService:
    providers: list[PaperSearchProviderInterface] = []
    if settings.mcp_papers_server_url:
        providers.append(
            ResearchIntelligenceMCPProvider(
                server_url=settings.mcp_papers_server_url,
                auth_token=settings.mcp_papers_auth_token,
                timeout_seconds=settings.mcp_papers_timeout_seconds,
            )
        )

    registry = PaperSearchProviderRegistry(providers)
    policy = PaperSearchPolicy(
        enabled=settings.mcp_papers_enabled,
        max_results_per_call=settings.mcp_papers_max_results_per_call,
        timeout_seconds=settings.mcp_papers_timeout_seconds,
    )
    metrics = get_metrics_recorder()
    service = PaperSearchService(
        registry=registry,
        policy=policy,
        default_provider=DEFAULT_PROVIDER,
        cache=create_paper_search_cache(),
        metrics=metrics,
    )

    metrics.set_gauge(
        metric=MCP_SERVER_HEALTH,
        value=1.0 if service.available else 0.0,
        labels={"server": DEFAULT_PROVIDER},
    )

    return service
