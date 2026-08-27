"""
Shared remember/recall/search/update/forget flow for the two memory
types that keep both a Postgres row (CRUD/ownership) and a Qdrant
embedding (search ranking): SEMANTIC (PRD §9.4) and RESEARCH (PRD
§9.5). `SemanticMemoryService` and `ResearchMemoryService` differ only
in which `MemoryType` they're pinned to and what convenience methods
they expose on top -- this class holds everything else so that logic
isn't duplicated between them.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any
from uuid import UUID

from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.retrieval.query.dense_service import QueryEmbeddingService
from app.ai.memory.enums import MemoryScopeType, MemoryType
from app.ai.memory.models import MemoryRecord
from app.ai.memory.observability.metrics import EMBEDDING_LATENCY
from app.ai.memory.storage.postgres_store import PostgresMemoryStore
from app.ai.memory.storage.vector_index import MemoryVectorIndex
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.infrastructure.metrics.noop import NoOpMetricsRecorder


class VectorBackedMemoryService:
    def __init__(
        self,
        store: PostgresMemoryStore,
        vector_index: MemoryVectorIndex,
        query_embedding_service: QueryEmbeddingService,
        *,
        memory_type: MemoryType,
        embedding_provider: EmbeddingProvider = EmbeddingProvider.VOYAGE_AI,
        metrics: MetricsRecorder | None = None,
        score_threshold: float | None = None,
    ) -> None:
        self._store = store
        self._vector_index = vector_index
        self._embeddings = query_embedding_service
        self._memory_type = memory_type
        self._embedding_provider = embedding_provider
        self._metrics = metrics or NoOpMetricsRecorder()
        self._score_threshold = score_threshold
        """
        Minimum cosine similarity a memory must clear to be returned by
        `search()`. Without this, Qdrant always returns the nearest
        `top_k` neighbors regardless of how distant they actually are --
        with few memories stored, a topically unrelated memory can rank
        in the top_k and get surfaced as if it were relevant.
        """

    async def remember(
        self,
        *,
        owner_id: UUID,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        content: str,
        importance_score: float,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        record = await self._store.create(
            owner_id=owner_id,
            scope_type=scope_type,
            project_id=project_id,
            memory_type=self._memory_type,
            content=content,
            importance_score=importance_score,
            metadata=metadata,
        )

        await self._index(record)

        return record

    async def recall(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
    ) -> MemoryRecord | None:
        return await self._store.get(
            owner_id=owner_id,
            memory_id=memory_id,
            scope_type=scope_type,
            project_id=project_id,
        )

    async def search(
        self,
        *,
        owner_id: UUID,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        query: str,
        top_k: int = 10,
    ) -> list[MemoryRecord]:
        """PRD §18: embed query -> Qdrant search -> hydrate from Postgres."""

        vector = await self._embeddings.embed(query, self._embedding_provider)
        return await self.search_with_embedding(
            owner_id=owner_id,
            scope_type=scope_type,
            project_id=project_id,
            embedding=vector,
            top_k=top_k,
        )

    async def search_with_embedding(
        self,
        *,
        owner_id: UUID,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        embedding: list[float],
        top_k: int = 10,
    ) -> list[MemoryRecord]:
        """Search this memory type using an embedding obtained by the caller.

        `search()` remains the backward-compatible convenience API. Context
        assembly uses this method to share one query embedding across the
        semantic and research branches.
        """

        matched_ids = await self._vector_index.search(
            owner_id=owner_id,
            scope_type=scope_type,
            project_id=project_id,
            vector=embedding,
            memory_types=[self._memory_type],
            top_k=top_k,
            score_threshold=self._score_threshold,
        )

        return await self._hydrate(
            owner_id=owner_id,
            memory_ids=matched_ids,
            scope_type=scope_type,
            project_id=project_id,
        )

    async def embed_query(self, query: str) -> list[float]:
        """Expose the configured query embedding without exposing provider SDKs."""
        return await self._embeddings.embed(query, self._embedding_provider)

    async def find_exact_content(
        self,
        *,
        owner_id: UUID,
        content: str,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
    ) -> MemoryRecord | None:
        return await self._store.find_exact_content(
            owner_id=owner_id,
            memory_type=self._memory_type,
            content=content,
            scope_type=scope_type,
            project_id=project_id,
        )

    async def update(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
        importance_score: float | None = None,
    ) -> MemoryRecord | None:
        updated = await self._store.update(
            owner_id=owner_id,
            memory_id=memory_id,
            scope_type=scope_type,
            project_id=project_id,
            content=content,
            metadata=metadata,
            importance_score=importance_score,
        )

        if updated is None:
            return None

        if content is not None:
            await self._index(updated)

        return updated

    async def forget(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
    ) -> bool:
        deleted = await self._store.delete(
            owner_id=owner_id,
            memory_id=memory_id,
            scope_type=scope_type,
            project_id=project_id,
        )

        if deleted:
            await self._vector_index.delete(memory_id)

        return deleted

    async def _index(
        self,
        record: MemoryRecord,
    ) -> None:
        started = perf_counter()

        vector = await self._embeddings.embed(record.content, self._embedding_provider)

        self._metrics.record_duration(
            operation=EMBEDDING_LATENCY,
            duration_ms=(perf_counter() - started) * 1000,
        )

        await self._vector_index.upsert(
            memory_id=record.id,
            owner_id=record.owner_id,
            memory_type=record.type,
            scope_type=record.scope_type,
            project_id=record.project_id,
            vector=vector,
        )

    async def _hydrate(
        self,
        *,
        owner_id: UUID,
        memory_ids: list[UUID],
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
    ) -> list[MemoryRecord]:
        records = []

        for memory_id in memory_ids:
            record = await self._store.get(
                owner_id=owner_id,
                memory_id=memory_id,
                scope_type=scope_type,
                project_id=project_id,
            )

            if record is not None:
                records.append(record)

        return records
