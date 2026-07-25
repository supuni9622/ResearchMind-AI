"""Provider registry for the Web Search Tool Platform (PRD §11.3)."""

from __future__ import annotations

import structlog

from app.ai.tools.web_search.exceptions import WebSearchProviderUnavailableError
from app.ai.tools.web_search.interfaces import WebSearchProviderInterface

logger = structlog.get_logger()


class WebSearchProviderRegistry:
    def __init__(self, providers: list[WebSearchProviderInterface] | None = None) -> None:
        self._providers = {provider.name: provider for provider in providers or []}

    def get(self, name: str) -> WebSearchProviderInterface:
        provider = self._providers.get(name)
        if provider is None:
            logger.warning(
                "web_search.registry.provider_not_found",
                provider=name,
                available_providers=list(self._providers),
            )
            raise WebSearchProviderUnavailableError(
                f"Web search provider '{name}' is not registered."
            )
        return provider

    def has(self, name: str) -> bool:
        return name in self._providers

    @property
    def providers(self) -> list[str]:
        return list(self._providers)
