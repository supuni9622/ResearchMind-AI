"""
Null query embedding cache.
"""

from __future__ import annotations

from app.ai.knowledge.cache.query_embeddings.interfaces import (
    QueryEmbeddingCache,
)


class NullQueryEmbeddingCache(
    QueryEmbeddingCache,
):
    """
    No-op cache implementation.
    """

    async def get(
        self,
        key: str,
    ) -> list[float] | None:
        return None

    async def set(
        self,
        key: str,
        vector: list[float],
    ) -> None:
        return None
