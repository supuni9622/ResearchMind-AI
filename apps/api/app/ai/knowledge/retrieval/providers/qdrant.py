"""
Qdrant Retrieval Provider.

Implements dense semantic retrieval against Qdrant.

Responsibilities

- execute vector search
- map Qdrant responses into canonical models

The provider intentionally contains no orchestration logic.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.ai.knowledge.retrieval.base import (
    BaseRetrievalProvider,
)
from app.ai.knowledge.retrieval.config import (
    QdrantRetrievalConfig,
)
from app.ai.knowledge.retrieval.enums import (
    RetrievalProvider,
)
from app.ai.knowledge.retrieval.models import (
    RetrievalExecution,
    RetrievalQuery,
    RetrievalResult,
    RetrievedChunk,
)
from app.ai.knowledge.retrieval.query.models import (
    SparseQueryEmbedding,
)
from app.ai.knowledge.vectorstores.providers.qdrant import (
    DENSE_VECTOR_NAME,
    SPARSE_VECTOR_NAME,
)
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qdrant
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
)


class QdrantRetrievalProvider(
    BaseRetrievalProvider[QdrantRetrievalConfig],
):
    """
    Dense retrieval implementation using Qdrant.
    """

    def __init__(
        self,
        *,
        client: AsyncQdrantClient,
        config: QdrantRetrievalConfig,
    ) -> None:
        super().__init__(config)

        self._client = client

    @property
    def provider(self) -> RetrievalProvider:
        return RetrievalProvider.QDRANT

    async def search(
        self,
        query: RetrievalQuery,
        query_vector: list[float],
    ) -> RetrievalResult:
        """
        Execute semantic retrieval.
        """

        search_filter = self._build_filter(
            query.filters,
        )

        response = await self._client.query_points(
            collection_name=self._config.collection_name,
            query=query_vector,
            using=DENSE_VECTOR_NAME,
            query_filter=search_filter,
            limit=query.top_k,
            with_payload=self._config.with_payload,
            with_vectors=self._config.with_vectors,
            score_threshold=self._config.score_threshold,
        )

        return RetrievalResult(
            query=query,
            execution=RetrievalExecution(
                completed_at=datetime.now(
                    UTC,
                ),
            ),
            chunks=self._map_points(
                response.points,
            ),
        )

    @staticmethod
    def _map_points(
        points: list,
    ) -> list[RetrievedChunk]:
        """
        Map Qdrant points into canonical RetrievedChunk models.
        """

        chunks: list[RetrievedChunk] = []

        for point in points:
            payload = point.payload or {}

            chunk = RetrievedChunk(
                chunk_id=UUID(str(payload["chunk_id"])),
                document_id=UUID(str(payload["document_id"])),
                filename=payload.get(
                    "filename",
                    "",
                ),
                owner_id=payload.get(
                    "owner_id",
                    "",
                ),
                chunk_index=payload.get(
                    "chunk_index",
                    0,
                ),
                content=payload.get(
                    "content",
                    "",
                ),
                score=float(point.score),
                metadata=payload.get(
                    "additional_metadata",
                    {},
                ),
            )

            chunks.append(chunk)

        return chunks

    def _build_filter(
        self,
        filters: dict,
    ) -> Filter | None:
        """
        Build Qdrant metadata filters.

        Supported filters:

        - owner_id
        - document_id
        - filename
        - language
        """

        if not filters:
            return None

        must_conditions = []

        owner_id = filters.get(
            "owner_id",
        )

        if owner_id:
            must_conditions.append(
                FieldCondition(
                    key="owner_id",
                    match=MatchValue(
                        value=owner_id,
                    ),
                )
            )

        document_id = filters.get(
            "document_id",
        )

        if document_id:
            must_conditions.append(
                FieldCondition(
                    key="document_id",
                    match=MatchValue(
                        value=str(document_id),
                    ),
                )
            )

        filename = filters.get(
            "filename",
        )

        if filename:
            must_conditions.append(
                FieldCondition(
                    key="filename",
                    match=MatchValue(
                        value=filename,
                    ),
                )
            )

        language = filters.get(
            "language",
        )

        if language:
            must_conditions.append(
                FieldCondition(
                    key="language",
                    match=MatchValue(
                        value=language,
                    ),
                )
            )

        if not must_conditions:
            return None

        return Filter(
            must=must_conditions,
        )

    async def search_sparse(
        self,
        query: RetrievalQuery,
        sparse_query: SparseQueryEmbedding,
    ) -> RetrievalResult:
        """
        Execute sparse retrieval.

        Uses SPLADE sparse vectors stored in Qdrant.
        """

        response = await self._client.query_points(
            collection_name=self._config.collection_name,
            query=qdrant.SparseVector(
                indices=sparse_query.indices,
                values=sparse_query.values,
            ),
            using=SPARSE_VECTOR_NAME,
            query_filter=self._build_filter(
                query.filters,
            ),
            limit=query.top_k,
            with_payload=self._config.with_payload,
            with_vectors=False,
        )

        return RetrievalResult(
            query=query,
            execution=RetrievalExecution(
                completed_at=datetime.now(
                    UTC,
                ),
            ),
            chunks=self._map_points(
                response.points,
            ),
        )
