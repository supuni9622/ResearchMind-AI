"""
Chunking provider registry.

This registry is the central extension point of the Chunking Platform.

It allows providers such as:

- Fixed Chunker
- Recursive Chunker
- Markdown Chunker
- Hierarchical Chunker
- Semantic Chunker
- LLM Chunker
- Adaptive Chunker

to register themselves behind a single lookup interface.

The ChunkingService depends only on this registry rather than concrete
provider implementations, allowing new chunking strategies to be added
without modifying application code.
"""

from __future__ import annotations

from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.chunking.exceptions import ChunkingProviderNotFoundError
from app.ai.knowledge.chunking.interfaces import ChunkingProvider


class ChunkingRegistry:
    """
    Registry of available chunking providers.
    """

    def __init__(self) -> None:
        self._providers: dict[
            ChunkingStrategy,
            ChunkingProvider,
        ] = {}

    def register(
        self,
        provider: ChunkingProvider,
    ) -> None:
        """
        Register a chunking provider.

        Raises:
            ValueError:
                If a provider for the strategy is already registered.
        """

        strategy = provider.strategy

        if strategy in self._providers:
            raise ValueError(
                f"Chunking provider '{strategy}' is already registered.",
            )

        self._providers[strategy] = provider

    def get(
        self,
        strategy: ChunkingStrategy,
    ) -> ChunkingProvider:
        """
        Resolve a registered chunking provider.

        Raises:
            ChunkingProviderNotFoundError:
                If no provider is registered for the requested strategy.
        """

        try:
            return self._providers[strategy]
        except KeyError:
            raise ChunkingProviderNotFoundError(
                f"No chunking provider registered for strategy '{strategy}'.",
            ) from None

    def exists(
        self,
        strategy: ChunkingStrategy,
    ) -> bool:
        """
        Check whether a provider exists for the given strategy.
        """

        return strategy in self._providers

    def unregister(
        self,
        strategy: ChunkingStrategy,
    ) -> None:
        """
        Remove a registered provider.

        Does nothing if the provider does not exist.
        """

        self._providers.pop(strategy, None)

    def clear(self) -> None:
        """
        Remove all registered providers.
        """

        self._providers.clear()

    @property
    def providers(
        self,
    ) -> dict[ChunkingStrategy, ChunkingProvider]:
        """
        Registered providers.

        Returns a shallow copy to prevent external mutation.
        """

        return self._providers.copy()

    @property
    def supported_strategies(
        self,
    ) -> list[ChunkingStrategy]:
        """
        Return all registered chunking strategies.
        """

        return list(self._providers.keys())
