"""
Research Memory Service (PRD §9.5) -- remembers research outputs:
reports, findings, evidence, citations. The full report/citations/
sources already persist via the Research API Platform's own
`ResearchSession` row and Research Artifact (S3) -- this service does
not duplicate that (PRD §3 Non-Goals: memory doesn't own report
generation). It instead lets a condensed, searchable finding/evidence
memory be recorded against a research session, consumed later via
`search()` (PRD §19: "Research Session -> Memory Search -> Previous
Reports -> Evidence -> Planner Context").

Postgres holds the canonical row; Qdrant holds the embedding used
purely for `search()` ranking -- see `VectorBackedMemoryService`.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.retrieval.query.dense_service import QueryEmbeddingService
from app.ai.memory.enums import MemoryType
from app.ai.memory.models import MemoryRecord
from app.ai.memory.storage.postgres_store import PostgresMemoryStore
from app.ai.memory.storage.vector_backed_service import VectorBackedMemoryService
from app.ai.memory.storage.vector_index import MemoryVectorIndex
from app.infrastructure.metrics.interfaces import MetricsRecorder

_RESEARCH_ID_KEY = "research_id"


class ResearchMemoryService(VectorBackedMemoryService):
    def __init__(
        self,
        store: PostgresMemoryStore,
        vector_index: MemoryVectorIndex,
        query_embedding_service: QueryEmbeddingService,
        *,
        embedding_provider: EmbeddingProvider = EmbeddingProvider.VOYAGE_AI,
        metrics: MetricsRecorder | None = None,
        score_threshold: float | None = None,
    ) -> None:
        super().__init__(
            store,
            vector_index,
            query_embedding_service,
            memory_type=MemoryType.RESEARCH,
            embedding_provider=embedding_provider,
            metrics=metrics,
            score_threshold=score_threshold,
        )

    async def remember_finding(
        self,
        *,
        owner_id: UUID,
        research_id: UUID,
        content: str,
        importance_score: float,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        """
        Convenience wrapper over `remember()` that stamps the owning
        `ResearchSession.id` into `metadata`, so a later `search()` hit
        can be traced back to the report it came from.
        """

        return await self.remember(
            owner_id=owner_id,
            content=content,
            importance_score=importance_score,
            metadata={**(metadata or {}), _RESEARCH_ID_KEY: str(research_id)},
        )
