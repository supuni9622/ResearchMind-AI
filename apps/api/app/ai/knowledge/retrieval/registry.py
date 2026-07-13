"""
Retrieval provider registry.

The registry maintains all retrieval provider implementations and allows
the RetrievalService to remain independent from concrete providers.
"""

from __future__ import annotations

from app.ai.knowledge.retrieval.enums import (
    RetrievalProvider,
)
from app.ai.knowledge.retrieval.exceptions import (
    RetrievalProviderNotFoundError,
)
from app.ai.knowledge.retrieval.interfaces import (
    RetrievalProviderInterface,
)


class RetrievalRegistry:
    """
    Registry of retrieval providers.
    """

    def __init__(
        self,
        providers: list[RetrievalProviderInterface],
    ) -> None:
        self._providers: dict[
            RetrievalProvider,
            RetrievalProviderInterface,
        ] = {provider.provider: provider for provider in providers}

    def get(
        self,
        provider: RetrievalProvider,
    ) -> RetrievalProviderInterface:
        """
        Resolve a retrieval provider.

        Raises:
            RetrievalProviderNotFoundError
        """

        retrieval_provider = self._providers.get(provider)

        if retrieval_provider is None:
            raise RetrievalProviderNotFoundError(
                f"Retrieval provider '{provider}' is not registered."
            )

        return retrieval_provider

    def has(
        self,
        provider: RetrievalProvider,
    ) -> bool:
        """
        Determine whether a provider is registered.
        """

        return provider in self._providers

    @property
    def providers(
        self,
    ) -> list[RetrievalProvider]:
        """
        Return all registered providers.
        """

        return list(self._providers.keys())
