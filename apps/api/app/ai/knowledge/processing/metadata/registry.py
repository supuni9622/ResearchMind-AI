"""
Metadata provider registry.

The registry is responsible for registering metadata providers and
returning the providers participating in the metadata enrichment
pipeline.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.ai.knowledge.processing.metadata.interfaces import (
    MetadataProvider,
)


class MetadataRegistry:
    """
    Registry for metadata provider implementations.
    """

    def __init__(
        self,
        providers: Iterable[MetadataProvider] | None = None,
    ) -> None:
        self._providers: list[MetadataProvider] = []

        if providers:
            for provider in providers:
                self.register(provider)

    def register(
        self,
        provider: MetadataProvider,
    ) -> None:
        """
        Register a metadata provider.
        """

        self._providers.append(provider)

    @property
    def providers(self) -> tuple[MetadataProvider, ...]:
        """
        Return all registered metadata providers.
        """

        return tuple(self._providers)

    def __iter__(self):
        """
        Iterate over registered providers.
        """

        return iter(self._providers)

    def __len__(self) -> int:
        """
        Return the number of registered providers.
        """

        return len(self._providers)
