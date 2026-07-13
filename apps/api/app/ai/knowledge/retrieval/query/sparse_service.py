"""
Sparse Query Embedding Service.
"""

from __future__ import annotations

import structlog
from app.ai.knowledge.indexing.providers.fastembed import (
    FastEmbedSparseEmbeddingProvider,
)
from app.ai.knowledge.retrieval.query.models import (
    SparseQueryEmbedding,
)

logger = structlog.get_logger()


class SparseQueryEmbeddingService:
    """
    Generates sparse query embeddings.
    """

    def __init__(
        self,
        provider: FastEmbedSparseEmbeddingProvider,
    ) -> None:
        self._provider = provider

    async def embed(
        self,
        query: str,
    ) -> SparseQueryEmbedding:
        logger.info(
            "retrieval.sparse_embedding.started",
        )

        vectors = await self._provider.embed(
            [query],
        )

        vector = vectors[0]

        logger.info(
            "retrieval.sparse_embedding.completed",
            dimensions=len(
                vector.indices,
            ),
        )

        return SparseQueryEmbedding(
            indices=vector.indices,
            values=vector.values,
        )
