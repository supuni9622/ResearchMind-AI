from __future__ import annotations

import structlog
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.exceptions import (
    GenerationProviderNotFoundError,
)
from app.ai.runtime.generation.interfaces import (
    GenerationProviderInterface,
)

logger = structlog.get_logger()


class GenerationRegistry:
    def __init__(
        self,
        providers: list[GenerationProviderInterface],
    ):
        self._providers = {provider.provider: provider for provider in providers}

    def get(
        self,
        provider: GenerationProvider,
    ) -> GenerationProviderInterface:

        generation_provider = self._providers.get(provider)

        if generation_provider is None:
            logger.warning(
                "generation.registry.provider_not_found",
                provider=provider.value,
                available_providers=[p.value for p in self._providers],
            )
            raise (GenerationProviderNotFoundError(f"Provider '{provider}' is not registered."))

        return generation_provider

    def has(
        self,
        provider: GenerationProvider,
    ) -> bool:
        return provider in self._providers

    @property
    def providers(
        self,
    ) -> list[GenerationProvider]:
        return list(self._providers.keys())
