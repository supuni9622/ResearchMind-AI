"""
Query embedding cache interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class QueryEmbeddingCache(ABC):
    """
    Cache for query embeddings.
    """

    @abstractmethod
    async def get(
        self,
        key: str,
    ) -> list[float] | None:
        """
        Return cached embedding.
        """

    @abstractmethod
    async def set(
        self,
        key: str,
        vector: list[float],
    ) -> None:
        """
        Store query embedding.
        """
