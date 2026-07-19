"""
Memory Platform dependencies (memory_platform_prd.md).
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory.artifacts.writers import MemoryArtifactWriter
from app.ai.memory.create import (
    create_memory_artifact_writer,
    create_memory_query_embedding_service,
    create_memory_vector_index,
    create_session_memory_service,
    get_memory_metrics,
)
from app.ai.memory.extraction.service import MemoryExtractionService
from app.ai.memory.lifecycle.service import MemoryLifecycleService
from app.ai.memory.profile.service import UserMemoryService
from app.ai.memory.research.service import ResearchMemoryService
from app.ai.memory.semantic.service import SemanticMemoryService
from app.ai.memory.services.memory_service import MemoryService
from app.ai.memory.session.service import SessionMemoryService
from app.ai.memory.storage.postgres_store import PostgresMemoryStore
from app.ai.memory.storage.vector_index import MemoryVectorIndex
from app.ai.runtime.generation.orchestration.orchestrator import GenerationRuntime
from app.core.settings import settings
from app.db.session import get_db
from app.dependencies.generation import get_generation_runtime
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.repositories.memory import MemoryRepository


def get_session_memory_service() -> SessionMemoryService:
    return create_session_memory_service()


def get_postgres_memory_store(
    session: AsyncSession = Depends(get_db),
) -> PostgresMemoryStore:
    return PostgresMemoryStore(session)


def get_user_memory_service(
    store: PostgresMemoryStore = Depends(get_postgres_memory_store),
) -> UserMemoryService:
    return UserMemoryService(store)


def get_semantic_memory_service(
    store: PostgresMemoryStore = Depends(get_postgres_memory_store),
    vector_index: MemoryVectorIndex = Depends(create_memory_vector_index),
    metrics: MetricsRecorder = Depends(get_memory_metrics),
) -> SemanticMemoryService:
    return SemanticMemoryService(
        store,
        vector_index,
        create_memory_query_embedding_service(),
        metrics=metrics,
        score_threshold=settings.memory_search_score_threshold,
    )


def get_research_memory_service(
    store: PostgresMemoryStore = Depends(get_postgres_memory_store),
    vector_index: MemoryVectorIndex = Depends(create_memory_vector_index),
    metrics: MetricsRecorder = Depends(get_memory_metrics),
) -> ResearchMemoryService:
    return ResearchMemoryService(
        store,
        vector_index,
        create_memory_query_embedding_service(),
        metrics=metrics,
        score_threshold=settings.memory_search_score_threshold,
    )


def get_memory_artifact_writer() -> MemoryArtifactWriter:
    return create_memory_artifact_writer()


def get_memory_extraction_service(
    generation_runtime: GenerationRuntime = Depends(get_generation_runtime),
) -> MemoryExtractionService:
    return MemoryExtractionService(generation_runtime)


def get_memory_lifecycle_service(
    session: AsyncSession = Depends(get_db),
    vector_index: MemoryVectorIndex = Depends(create_memory_vector_index),
) -> MemoryLifecycleService:
    """
    Not wired to any HTTP route or scheduler -- an operator-invoked
    (or future cron-invoked) sweep, not a user-facing action. See
    `MemoryLifecycleService`'s module docstring.
    """

    return MemoryLifecycleService(MemoryRepository(session), vector_index)


def get_memory_service(
    session_memory: SessionMemoryService = Depends(get_session_memory_service),
    user_memory: UserMemoryService = Depends(get_user_memory_service),
    semantic_memory: SemanticMemoryService = Depends(get_semantic_memory_service),
    research_memory: ResearchMemoryService = Depends(get_research_memory_service),
    artifact_writer: MemoryArtifactWriter = Depends(get_memory_artifact_writer),
    metrics: MetricsRecorder = Depends(get_memory_metrics),
) -> MemoryService:
    """
    Request-scoped `MemoryService` (carries a request-scoped
    `AsyncSession` via its Postgres-backed collaborators, so unlike
    those collaborators' own singleton pieces, it can't be cached).
    """

    return MemoryService(
        session_memory=session_memory,
        user_memory=user_memory,
        semantic_memory=semantic_memory,
        research_memory=research_memory,
        artifact_writer=artifact_writer,
        metrics=metrics,
        importance_threshold=settings.memory_importance_threshold,
    )
