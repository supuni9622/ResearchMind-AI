"""Provider registry for the Research Intelligence MCP paper-search platform
(mirrors `app.ai.tools.web_search.registry`)."""

from __future__ import annotations

import structlog

from app.ai.tools.paper_search.exceptions import PaperSearchProviderUnavailableError
from app.ai.tools.paper_search.interfaces import PaperSearchProviderInterface

logger = structlog.get_logger()


class PaperSearchProviderRegistry:
    def __init__(self, providers: list[PaperSearchProviderInterface] | None = None) -> None:
        self._providers = {provider.name: provider for provider in providers or []}

    def get(self, name: str) -> PaperSearchProviderInterface:
        provider = self._providers.get(name)
        if provider is None:
            logger.warning(
                "paper_search.registry.provider_not_found",
                provider=name,
                available_providers=list(self._providers),
            )
            raise PaperSearchProviderUnavailableError(
                f"Paper search provider '{name}' is not registered."
            )
        return provider

    def has(self, name: str) -> bool:
        return name in self._providers

    @property
    def providers(self) -> list[str]:
        return list(self._providers)
