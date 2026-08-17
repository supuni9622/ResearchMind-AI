"""
Qdrant-backed search index for SEMANTIC and RESEARCH memory (PRD §6.3/
§6.4) -- a dedicated collection, separate from the Knowledge Platform's
document-chunk collection (`VectorStoreService`/`QdrantVectorStoreProvider`),
since memory payloads (owner_id, type) don't fit that platform's
document/chunk-shaped `VectorPayload`.

This index is search-only: Postgres (`Memory` ORM model /
`MemoryRepository`) remains the single source of truth for CRUD. A
point's payload carries just enough (`owner_id`, `type`) to filter a
search; matched point ids are hydrated back to full `MemoryRecord`s by
the caller.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qdrant

from app.ai.memory.enums import MemoryScopeType, MemoryType

logger = structlog.get_logger()


class MemoryVectorIndex:
    def __init__(
        self,
        client: AsyncQdrantClient,
        *,
        collection_name: str,
        dimensions: int,
    ) -> None:
        self._client = client
        self._collection_name = collection_name
        self._dimensions = dimensions
        self._collection_ready = False

    async def ensure_collection(self) -> None:
        """
        Idempotent, on-demand collection creation -- mirrors the
        Knowledge Platform's `create_collection_if_missing` flow
        (`IndexingService`). Called from `upsert()`/`search()` rather
        than at app startup so the composition root stays synchronous.
        """

        if self._collection_ready:
            return

        if await self._client.collection_exists(self._collection_name):
            self._collection_ready = True
            return

        logger.info(
            "memory.vector_index.create_collection.started",
            collection=self._collection_name,
            dimensions=self._dimensions,
        )

        await self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=qdrant.VectorParams(
                size=self._dimensions,
                distance=qdrant.Distance.COSINE,
            ),
        )

    async def upsert(
        self,
        *,
        memory_id: UUID,
        owner_id: UUID,
        memory_type: MemoryType,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        vector: list[float],
    ) -> bool:
        await self.ensure_collection()

        try:
            await self._client.upsert(
                collection_name=self._collection_name,
                points=[
                    qdrant.PointStruct(
                        id=str(memory_id),
                        vector=vector,
                        payload={
                            "owner_id": str(owner_id),
                            "type": memory_type.value,
                            "scope_type": scope_type.value,
                            "project_id": str(project_id) if project_id else None,
                        },
                    )
                ],
                wait=True,
            )
            return True
        except Exception:
            logger.exception(
                "memory.vector_index.upsert_failed",
                memory_id=str(memory_id),
            )
            return False

    async def search(
        self,
        *,
        owner_id: UUID,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        vector: list[float],
        memory_types: list[MemoryType],
        top_k: int,
        score_threshold: float | None = None,
    ) -> list[UUID]:
        await self.ensure_collection()

        must_conditions: list[qdrant.Condition] = [
            qdrant.FieldCondition(
                key="owner_id",
                match=qdrant.MatchValue(value=str(owner_id)),
            ),
            qdrant.FieldCondition(
                key="type",
                match=qdrant.MatchAny(any=[t.value for t in memory_types]),
            ),
        ]
        should_conditions: list[qdrant.Condition] | None = None
        if scope_type == MemoryScopeType.PROJECT:
            must_conditions.extend(
                [
                    qdrant.FieldCondition(
                        key="scope_type",
                        match=qdrant.MatchValue(value=scope_type.value),
                    ),
                    qdrant.FieldCondition(
                        key="project_id",
                        match=qdrant.MatchValue(value=str(project_id)),
                    ),
                ]
            )
        else:
            # Points created before M5 have no scope payload; all legacy SQL
            # rows are reversibly backfilled as personal by the migration.
            should_conditions = [
                qdrant.FieldCondition(
                    key="scope_type",
                    match=qdrant.MatchValue(value=MemoryScopeType.PERSONAL.value),
                ),
                qdrant.IsNullCondition(is_null=qdrant.PayloadField(key="scope_type")),
            ]

        query_filter = qdrant.Filter(must=must_conditions, should=should_conditions)

        try:
            response = await self._client.query_points(
                collection_name=self._collection_name,
                query=vector,
                query_filter=query_filter,
                limit=top_k,
                score_threshold=score_threshold,
            )
        except Exception:
            logger.exception(
                "memory.vector_index.search_failed",
                owner_id=str(owner_id),
            )
            return []

        return [UUID(str(point.id)) for point in response.points]

    async def delete(
        self,
        memory_id: UUID,
    ) -> bool:
        try:
            await self._client.delete(
                collection_name=self._collection_name,
                points_selector=qdrant.PointIdsList(points=[str(memory_id)]),
                wait=True,
            )
            return True
        except Exception:
            logger.exception(
                "memory.vector_index.delete_failed",
                memory_id=str(memory_id),
            )
            return False
