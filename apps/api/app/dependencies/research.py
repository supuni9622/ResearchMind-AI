"""
Research API platform dependencies (research_api_prd.md).
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.artifacts.create import (
    create_research_artifact_writer,
    get_artifact_policy_service,
)
from app.ai.artifacts.policies.service import ArtifactPolicyService
from app.ai.artifacts.research.writers import ResearchArtifactWriter
from app.ai.knowledge.context.service import ContextBuilderService
from app.ai.knowledge.retrieval.service import RetrievalService
from app.ai.memory.extraction.service import MemoryExtractionService
from app.ai.memory.services.memory_service import MemoryService
from app.ai.research.service import ResearchService
from app.ai.runtime.generation.orchestration.orchestrator import GenerationRuntime
from app.ai.runtime.generation.streaming.service import StreamingService
from app.db.session import get_db
from app.dependencies.context import get_context_builder
from app.dependencies.generation import get_generation_runtime, get_streaming_service
from app.dependencies.memory import get_memory_extraction_service, get_memory_service
from app.dependencies.retrieval import get_retrieval_service
from app.repositories.research import ResearchRepository


@lru_cache
def get_research_artifact_writer() -> ResearchArtifactWriter:
    """
    Return singleton ResearchArtifactWriter -- stateless (S3-backed),
    like `get_conversation_artifact_writer`.
    """

    return create_research_artifact_writer()


@lru_cache
def get_artifact_policy_service_dependency() -> ArtifactPolicyService:
    """
    Thin FastAPI-`Depends`-compatible wrapper around the Artifact
    Platform's own `get_artifact_policy_service()` composition root.

    Duplicated from `app.dependencies.generation` rather than imported
    from it -- that module's version exists for the Chat/Streaming
    routes and importing across unrelated route dependency modules would
    couple them for no reason.
    """

    return get_artifact_policy_service()


def get_research_repository(
    session: AsyncSession = Depends(get_db),
) -> ResearchRepository:
    """
    Return a request-scoped ResearchRepository bound to this request's
    database session.
    """

    return ResearchRepository(session)


def get_research_service(
    session: AsyncSession = Depends(get_db),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    context_builder: ContextBuilderService = Depends(get_context_builder),
    generation_runtime: GenerationRuntime = Depends(get_generation_runtime),
    streaming_service: StreamingService = Depends(get_streaming_service),
    research_artifact_writer: ResearchArtifactWriter = Depends(get_research_artifact_writer),
    artifact_policy_service: ArtifactPolicyService = Depends(
        get_artifact_policy_service_dependency
    ),
    memory_service: MemoryService = Depends(get_memory_service),
    memory_extraction_service: MemoryExtractionService = Depends(get_memory_extraction_service),
) -> ResearchService:
    """
    Return a request-scoped ResearchService bound to this request's
    database session (unlike the singleton collaborators it composes,
    it carries per-request state and can't be cached).
    """

    return ResearchService(
        session=session,
        retrieval_service=retrieval_service,
        context_builder=context_builder,
        generation_runtime=generation_runtime,
        streaming_service=streaming_service,
        research_artifact_writer=research_artifact_writer,
        artifact_policy_service=artifact_policy_service,
        memory_service=memory_service,
        memory_extraction_service=memory_extraction_service,
    )
