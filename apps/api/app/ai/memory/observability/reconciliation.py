"""Periodic Postgres/Qdrant drift repair with canonical Postgres authority."""

from __future__ import annotations

from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.retrieval.query.dense_service import QueryEmbeddingService
from app.ai.memory.enums import MemoryScopeType, MemoryType
from app.ai.memory.storage.vector_index import MemoryVectorIndex
from app.repositories.memory import MemoryRepository


class MemoryVectorReconciliationService:
    def __init__(
        self,
        repository: MemoryRepository,
        vector_index: MemoryVectorIndex,
        embeddings: QueryEmbeddingService,
        provider: EmbeddingProvider = EmbeddingProvider.VOYAGE_AI,
    ) -> None:
        self._repository = repository
        self._vector_index = vector_index
        self._embeddings = embeddings
        self._provider = provider

    async def repair(self) -> dict[str, int]:
        canonical_ids = await self._repository.list_vector_memory_ids()
        indexed_ids = await self._vector_index.list_point_ids()
        missing = canonical_ids - indexed_ids
        orphaned = indexed_ids - canonical_ids
        repaired_missing = 0
        repaired_orphans = 0
        for memory_id in orphaned:
            if await self._vector_index.delete(memory_id):
                repaired_orphans += 1
        for row in await self._repository.list_by_ids_admin(missing):
            vector = await self._embeddings.embed(row.content, self._provider)
            if await self._vector_index.upsert(
                memory_id=row.id,
                owner_id=row.owner_id,
                memory_type=MemoryType(row.type),
                scope_type=MemoryScopeType(row.scope_type),
                project_id=row.project_id,
                vector=vector,
            ):
                repaired_missing += 1
        return {
            "missing_found": len(missing),
            "orphaned_found": len(orphaned),
            "missing_repaired": repaired_missing,
            "orphaned_repaired": repaired_orphans,
        }
