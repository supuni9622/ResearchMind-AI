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

import structlog
from app.ai.knowledge.retrieval.base import (
    BaseRetrievalProvider,
)
from app.ai.knowledge.retrieval.config import (
    QdrantRetrievalConfig,
)
from app.ai.knowledge.retrieval.enums import (
    RetrievalProvider,
)
from app.ai.knowledge.retrieval.exceptions import (
    RetrievalExecutionError,
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
    Condition,
    FieldCondition,
    Filter,
    IsNullCondition,
    MatchValue,
    PayloadField,
)

logger = structlog.get_logger()


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
            owner_id=query.owner_id,
            project_id=query.project_id,
            filters=query.filters,
        )

        try:
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
        except Exception as exc:
            logger.exception(
                "retrieval.qdrant.search.failed",
                collection=self._config.collection_name,
                owner_id=query.owner_id,
            )
            raise RetrievalExecutionError("Dense retrieval failed.") from exc

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

    async def search_metadata(
        self,
        query: RetrievalQuery,
    ) -> RetrievalResult:
        """
        Execute metadata-filtered retrieval.

        Uses Qdrant's `scroll()` to return chunks matching structured
        filters only -- no vector similarity is involved. `owner_id` is
        always present on `query`, so the built filter always scopes to
        the tenant even when no additional filters are supplied.
        """

        # Owner scoping is mandatory access control, not a metadata match.
        # Scrolling with only owner_id returns arbitrary chunks in storage
        # order and gives them an undeserved third vote during RRF fusion.
        # Only run this retrieval branch when the caller supplied an actual
        # document metadata constraint.
        if not query.filters:
            return RetrievalResult(
                query=query,
                execution=RetrievalExecution(completed_at=datetime.now(UTC)),
                chunks=[],
            )

        search_filter = self._build_filter(
            owner_id=query.owner_id,
            project_id=query.project_id,
            filters=query.filters,
        )

        try:
            points, _next_offset = await self._client.scroll(
                collection_name=self._config.collection_name,
                scroll_filter=search_filter,
                limit=query.top_k,
                with_payload=self._config.with_payload,
                with_vectors=False,
            )
        except Exception as exc:
            logger.exception(
                "retrieval.qdrant.search_metadata.failed",
                collection=self._config.collection_name,
                owner_id=query.owner_id,
            )
            raise RetrievalExecutionError("Metadata-filtered retrieval failed.") from exc

        return RetrievalResult(
            query=query,
            execution=RetrievalExecution(
                completed_at=datetime.now(
                    UTC,
                ),
            ),
            #
            # Metadata matches have no similarity score -- they are
            # exact structural matches, so a flat score is assigned.
            # RRF fusion ranks by list position, not this value.
            #
            chunks=self._map_points(
                points,
                default_score=1.0,
            ),
        )

    @staticmethod
    def _map_points(
        points: list,
        *,
        default_score: float | None = None,
    ) -> list[RetrievedChunk]:
        """
        Map Qdrant points into canonical RetrievedChunk models.

        `default_score` is used for point types that carry no
        similarity score (e.g. `scroll()` records from metadata-only
        retrieval, which has no vector to rank against).

        A payload missing a required field (chunk_id/document_id)
        indicates a corrupted or partially-indexed record -- rather
        than silently producing a bad chunk, this fails fast. It's
        raised as RetrievalExecutionError (not a raw KeyError) so it
        gets the same structured logging and meaningful API response
        as every other failure in this provider, instead of escaping
        as an opaque 500.
        """

        chunks: list[RetrievedChunk] = []

        for point in points:
            payload = point.payload or {}

            try:
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
                    score=(default_score if default_score is not None else float(point.score)),
                    metadata=payload.get(
                        "additional_metadata",
                        {},
                    ),
                )
            except KeyError as exc:
                logger.exception(
                    "retrieval.qdrant.map_points.malformed_payload",
                    point_id=str(getattr(point, "id", "")),
                    missing_field=str(exc),
                )
                raise RetrievalExecutionError(
                    "A retrieved chunk is missing required indexed fields; "
                    "the index may be corrupted."
                ) from exc

            chunks.append(chunk)

        return chunks

    def _build_filter(
        self,
        *,
        owner_id: str,
        project_id: str | None = None,
        filters: dict,
    ) -> Filter:
        """
        Build Qdrant metadata filters.

        `owner_id`/`project_id` are required, separate parameters (not
        read out of `filters`) so a caller can never smuggle a different
        owner or project in through the filters dict -- they always scope
        to the caller's own tenant/workspace. `project_id=None` means
        personal documents only (`project_id` absent from the chunk's
        payload), not "every project" -- same omit=personal-only contract
        used throughout the Project workspace feature. Additional
        supported filters:

        - document_id
        - filename
        - language
        """

        must_conditions: list[Condition] = [
            FieldCondition(
                key="owner_id",
                match=MatchValue(
                    value=owner_id,
                ),
            )
        ]

        if project_id is not None:
            must_conditions.append(
                FieldCondition(
                    key="project_id",
                    match=MatchValue(value=project_id),
                )
            )
        else:
            must_conditions.append(IsNullCondition(is_null=PayloadField(key="project_id")))

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

        try:
            response = await self._client.query_points(
                collection_name=self._config.collection_name,
                query=qdrant.SparseVector(
                    indices=sparse_query.indices,
                    values=sparse_query.values,
                ),
                using=SPARSE_VECTOR_NAME,
                query_filter=self._build_filter(
                    owner_id=query.owner_id,
                    project_id=query.project_id,
                    filters=query.filters,
                ),
                limit=query.top_k,
                with_payload=self._config.with_payload,
                with_vectors=False,
            )
        except Exception as exc:
            logger.exception(
                "retrieval.qdrant.search_sparse.failed",
                collection=self._config.collection_name,
                owner_id=query.owner_id,
            )
            raise RetrievalExecutionError("Sparse retrieval failed.") from exc

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
