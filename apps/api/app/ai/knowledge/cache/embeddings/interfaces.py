"""
Embedding cache interface.

The Embedding Cache sits between the EmbeddingService and concrete
embedding providers. Identical chunk text, embedded with the same
provider, model, and configuration, resolves to the same cache key —
so re-embedding the same paragraph across different documents becomes
a cache lookup instead of a provider call.

Only the raw vector is cached. Provenance (document/chunk identifiers)
and statistics are always derived fresh from the current chunk via
EmbeddingFactory, since those are per-instance rather than per-content.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingCache(ABC):
    """
    Base interface for embedding cache backends.
    """

    @abstractmethod
    async def get_many(
        self,
        keys: list[str],
    ) -> dict[str, list[float]]:
        """
        Resolve cached vectors for the given cache keys.

        Args:
            keys:
                Cache keys to look up.

        Returns:
            Mapping of cache key to vector, containing only the keys
            that were found. Missing keys are simply absent from the
            result.
        """

    @abstractmethod
    async def set_many(
        self,
        entries: dict[str, list[float]],
    ) -> None:
        """
        Store vectors for the given cache keys.

        Args:
            entries:
                Mapping of cache key to vector to store.
        """
