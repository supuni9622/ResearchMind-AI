"""
Semantic Memory Service (PRD §9.4) -- embeddings, similarity search,
long-term facts ("user likes markdown reports", "user frequently
researches climate papers"). Postgres holds the canonical row
(CRUD/ownership); Qdrant holds the embedding used purely for
`search()` ranking (PRD §6.4/§18) -- see `VectorBackedMemoryService`
for the shared implementation.
"""

from __future__ import annotations

from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.retrieval.query.dense_service import QueryEmbeddingService
from app.ai.memory.enums import MemoryType
from app.ai.memory.storage.postgres_store import PostgresMemoryStore
from app.ai.memory.storage.vector_backed_service import VectorBackedMemoryService
from app.ai.memory.storage.vector_index import MemoryVectorIndex
from app.infrastructure.metrics.interfaces import MetricsRecorder


class SemanticMemoryService(VectorBackedMemoryService):
    def __init__(
        self,
        store: PostgresMemoryStore,
        vector_index: MemoryVectorIndex,
        query_embedding_service: QueryEmbeddingService,
        *,
        embedding_provider: EmbeddingProvider = EmbeddingProvider.VOYAGE_AI,
        metrics: MetricsRecorder | None = None,
    ) -> None:
        super().__init__(
            store,
            vector_index,
            query_embedding_service,
            memory_type=MemoryType.SEMANTIC,
            embedding_provider=embedding_provider,
            metrics=metrics,
        )
