"""
Statistics provider registry.

The registry is responsible for registering statistics providers and
returning the providers participating in the statistics enrichment
pipeline.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.ai.knowledge.processing.statistics.interfaces import (
    StatisticsProvider,
)


class StatisticsRegistry:
    """
    Registry for statistics provider implementations.
    """

    def __init__(
        self,
        providers: Iterable[StatisticsProvider] | None = None,
    ) -> None:
        self._providers: list[StatisticsProvider] = []

        if providers:
            for provider in providers:
                self.register(provider)

    def register(
        self,
        provider: StatisticsProvider,
    ) -> None:
        """
        Register a statistics provider.
        """

        self._providers.append(provider)

    @property
    def providers(self) -> tuple[StatisticsProvider, ...]:
        """
        Return all registered statistics providers.
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
