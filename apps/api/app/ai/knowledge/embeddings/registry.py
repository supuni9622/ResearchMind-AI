"""
Embedding provider registry.

This registry is the central extension point of the Embedding Platform.

It allows providers such as:

- Sentence Transformers
- Voyage AI
- OpenAI
- BGE
- Instructor
- Nomic

to register themselves behind a single lookup interface.

The EmbeddingService depends only on this registry rather than concrete
provider implementations, allowing new embedding providers to be added
without modifying application code.
"""

from __future__ import annotations

from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.exceptions import (
    EmbeddingProviderNotFoundError,
)
from app.ai.knowledge.embeddings.interfaces import (
    EmbeddingProvider as EmbeddingProviderInterface,
)


class EmbeddingRegistry:
    """
    Registry of available embedding providers.
    """

    def __init__(self) -> None:
        self._providers: dict[
            EmbeddingProvider,
            EmbeddingProviderInterface,
        ] = {}

    def register(
        self,
        provider: EmbeddingProviderInterface,
    ) -> None:
        """
        Register an embedding provider.

        Raises:
            ValueError:
                If a provider for the provider identifier is already registered.
        """

        provider_name = provider.provider

        if provider_name in self._providers:
            raise ValueError(
                f"Embedding provider '{provider_name}' is already registered.",
            )

        self._providers[provider_name] = provider

    def get(
        self,
        provider: EmbeddingProvider,
    ) -> EmbeddingProviderInterface:
        """
        Resolve a registered embedding provider.

        Raises:
            EmbeddingProviderNotFoundError:
                If no provider is registered for the requested provider.
        """

        try:
            return self._providers[provider]
        except KeyError:
            raise EmbeddingProviderNotFoundError(
                f"No embedding provider registered for '{provider}'.",
            ) from None

    def exists(
        self,
        provider: EmbeddingProvider,
    ) -> bool:
        """
        Check whether a provider exists.
        """

        return provider in self._providers

    def unregister(
        self,
        provider: EmbeddingProvider,
    ) -> None:
        """
        Remove a registered provider.

        Does nothing if the provider does not exist.
        """

        self._providers.pop(provider, None)

    def clear(self) -> None:
        """
        Remove all registered providers.
        """

        self._providers.clear()

    @property
    def providers(
        self,
    ) -> dict[
        EmbeddingProvider,
        EmbeddingProviderInterface,
    ]:
        """
        Registered providers.

        Returns a shallow copy to prevent external mutation.
        """

        return self._providers.copy()

    @property
    def supported_providers(
        self,
    ) -> list[EmbeddingProvider]:
        """
        Return all registered embedding providers.
        """

        return list(self._providers.keys())
