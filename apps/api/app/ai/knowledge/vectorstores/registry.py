"""
Vector Store provider registry.

This registry is the central extension point of the Vector Store
Platform.

It allows providers such as:

- Qdrant
- ChromaDB
- pgvector
- Pinecone
- Weaviate

to register themselves behind a single lookup interface.

The VectorStoreService depends only on this registry rather than
concrete provider implementations, allowing new vector store providers
to be added without modifying application code.
"""

from __future__ import annotations

from app.ai.knowledge.vectorstores.enums import VectorStoreProvider
from app.ai.knowledge.vectorstores.exceptions import (
    VectorStoreProviderNotFoundError,
)
from app.ai.knowledge.vectorstores.interfaces import (
    VectorStoreProviderInterface,
)


class VectorStoreRegistry:
    """
    Registry of available vector store providers.
    """

    def __init__(self) -> None:
        self._providers: dict[
            VectorStoreProvider,
            VectorStoreProviderInterface,
        ] = {}

    def register(
        self,
        provider: VectorStoreProviderInterface,
    ) -> None:
        """
        Register a vector store provider.

        Raises:
            ValueError:
                If a provider with the same identifier has already been
                registered.
        """

        provider_name = provider.provider

        if provider_name in self._providers:
            raise ValueError(
                f"Vector store provider '{provider_name}' is already registered.",
            )

        self._providers[provider_name] = provider

    def get(
        self,
        provider: VectorStoreProvider,
    ) -> VectorStoreProviderInterface:
        """
        Resolve a registered vector store provider.

        Raises:
            VectorStoreProviderNotFoundError:
                If the requested provider is not registered.
        """

        try:
            return self._providers[provider]
        except KeyError:
            raise VectorStoreProviderNotFoundError(
                f"No vector store provider registered for '{provider}'.",
            ) from None

    def exists(
        self,
        provider: VectorStoreProvider,
    ) -> bool:
        """
        Check whether a provider has been registered.
        """

        return provider in self._providers

    def unregister(
        self,
        provider: VectorStoreProvider,
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
        VectorStoreProvider,
        VectorStoreProviderInterface,
    ]:
        """
        Registered providers.

        Returns a shallow copy to prevent external mutation.
        """

        return self._providers.copy()

    @property
    def supported_providers(
        self,
    ) -> list[VectorStoreProvider]:
        """
        Return all registered vector store providers.
        """

        return list(self._providers.keys())
