"""
Memory Platform composition root.

Builds the stateless, singleton collaborators every memory type needs
(Valkey session store, Qdrant vector index, embedding service,
artifact writer). Postgres-backed pieces (`PostgresMemoryStore`,
`UserMemoryService`, `SemanticMemoryService`, `ResearchMemoryService`,
and `MemoryService` itself) carry a request-scoped `AsyncSession` and
are therefore composed per-request in `app.dependencies.memory`
instead -- mirrors `research/service.py` + `dependencies/research.py`.
"""

from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.knowledge.retrieval.create import create_query_embedding_service
from app.ai.knowledge.retrieval.query.dense_service import QueryEmbeddingService
from app.ai.knowledge.vectorstores.create import create_qdrant_client
from app.ai.memory.artifacts.writers import MemoryArtifactWriter
from app.ai.memory.extraction.service import MemoryExtractionService
from app.ai.memory.profile.service import UserMemoryService
from app.ai.memory.research.service import ResearchMemoryService
from app.ai.memory.semantic.service import SemanticMemoryService
from app.ai.memory.services.memory_service import MemoryService
from app.ai.memory.session.service import SessionMemoryService
from app.ai.memory.storage.postgres_store import PostgresMemoryStore
from app.ai.memory.storage.valkey_store import ValkeySessionStore
from app.ai.memory.storage.vector_index import MemoryVectorIndex
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.orchestration.create import create_generation_runtime
from app.core.settings import settings
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.infrastructure.metrics.noop import NoOpMetricsRecorder
from app.infrastructure.storage import create_storage


@lru_cache
def create_valkey_session_store() -> ValkeySessionStore:
    client = Redis.from_url(
        settings.valkey_url,
        decode_responses=True,
    )

    return ValkeySessionStore(
        client=client,
        ttl_seconds=settings.memory_session_ttl_seconds,
    )


@lru_cache
def create_session_memory_service() -> SessionMemoryService:
    return SessionMemoryService(
        create_valkey_session_store(),
    )


@lru_cache
def create_memory_vector_index() -> MemoryVectorIndex:
    return MemoryVectorIndex(
        client=create_qdrant_client(),
        collection_name=settings.memory_qdrant_collection_name,
        dimensions=settings.memory_vector_dimensions,
    )


@lru_cache
def create_memory_query_embedding_service() -> QueryEmbeddingService:
    """
    Reuses the Retrieval Platform's query embedding composition (PRD
    §24: "reuse existing embedding platform") rather than building a
    second one.
    """

    return create_query_embedding_service()


@lru_cache
def create_memory_artifact_writer() -> MemoryArtifactWriter:
    return MemoryArtifactWriter(
        storage_provider=create_storage(settings),
    )


@lru_cache
def get_memory_metrics() -> MetricsRecorder:
    return NoOpMetricsRecorder()


def build_memory_service(
    session: AsyncSession,
) -> MemoryService:
    """
    Plain-Python composition of a full `MemoryService` bound to
    `session`, for callers outside FastAPI's `Depends` graph -- e.g.
    the chat WebSocket route, which manually opens its own session
    (mirrors `ConversationService(session)` there). `app.dependencies.
    memory.get_memory_service` is the `Depends`-based equivalent for
    HTTP routes; this exists so that composition isn't duplicated for
    the one caller that can't use it.
    """

    store = PostgresMemoryStore(session)
    vector_index = create_memory_vector_index()
    embeddings = create_memory_query_embedding_service()
    metrics = get_memory_metrics()

    return MemoryService(
        session_memory=create_session_memory_service(),
        user_memory=UserMemoryService(store),
        semantic_memory=SemanticMemoryService(
            store,
            vector_index,
            embeddings,
            metrics=metrics,
            score_threshold=settings.memory_search_score_threshold,
        ),
        research_memory=ResearchMemoryService(
            store,
            vector_index,
            embeddings,
            metrics=metrics,
            score_threshold=settings.memory_search_score_threshold,
        ),
        artifact_writer=create_memory_artifact_writer(),
        metrics=metrics,
        importance_threshold=settings.memory_importance_threshold,
    )


@lru_cache
def build_memory_extraction_service() -> MemoryExtractionService:
    provider = (
        GenerationProvider.GROQ
        if settings.groq_api_key
        else GenerationProvider.OPENAI
        if settings.openai_api_key
        else None
    )
    fallback_provider = (
        GenerationProvider.OPENAI if settings.groq_api_key and settings.openai_api_key else None
    )
    return MemoryExtractionService(
        create_generation_runtime(),
        provider=provider,
        fallback_provider=fallback_provider,
    )
