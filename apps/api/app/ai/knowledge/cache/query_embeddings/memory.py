"""
In-memory query embedding cache.
"""

from __future__ import annotations

from app.ai.knowledge.cache.query_embeddings.interfaces import (
    QueryEmbeddingCache,
)


class InMemoryQueryEmbeddingCache(
    QueryEmbeddingCache,
):
    """
    Simple in-memory cache.

    Intended only for local development
    and early milestones.
    """

    def __init__(self) -> None:
        self._cache: dict[
            str,
            list[float],
        ] = {}

    async def get(
        self,
        key: str,
    ) -> list[float] | None:
        return self._cache.get(key)

    async def set(
        self,
        key: str,
        vector: list[float],
    ) -> None:
        self._cache[key] = vector
