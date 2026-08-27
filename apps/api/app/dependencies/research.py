"""
Research API platform dependencies (research_api_prd.md).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
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
from app.ai.memory.session.state_updater import SessionStateUpdaterService
from app.ai.observability.prometheus.create import get_metrics_recorder
from app.ai.research.service import ResearchService
from app.ai.runtime.chat.paper_query import (
    PaperQueryExtractionService,
    create_paper_query_extraction_service,
)
from app.ai.runtime.generation.orchestration.orchestrator import GenerationRuntime
from app.ai.runtime.generation.streaming.service import StreamingService
from app.ai.runtime.research.draft_inspection import ResearchDraftInspectionService
from app.ai.runtime.research.execution import ResearchRuntimeExecutionService
from app.ai.runtime.research.plan_inspection import ResearchPlanInspectionService
from app.ai.runtime.research.proposal_service import ResearchProposalService
from app.ai.runtime.research.report_download import ResearchReportDownloadService
from app.ai.runtime.research.run_service import ResearchRunService
from app.ai.runtime.research.web_search.create import create_web_search_necessity_service
from app.ai.runtime.research.web_search.necessity import WebSearchNecessityService
from app.ai.runtime.research.web_search_inspection import ResearchWebSearchInspectionService
from app.ai.tools.paper_search.create import create_paper_search_service
from app.ai.tools.paper_search.service import PaperSearchService
from app.ai.tools.web_search.create import create_web_search_service
from app.ai.tools.web_search.service import WebSearchService
from app.core.settings import settings
from app.db.session import SessionFactory, get_db
from app.dependencies.context import get_context_builder
from app.dependencies.generation import get_generation_runtime, get_streaming_service
from app.dependencies.generation_usage import get_generation_usage_repository
from app.dependencies.memory import (
    get_memory_extraction_service,
    get_memory_service,
    get_session_state_updater_service,
)
from app.dependencies.retrieval import get_retrieval_service
from app.dependencies.upload import get_document_storage
from app.infrastructure.storage.interfaces import DocumentStorage
from app.repositories.generation_usage import GenerationUsageRepository
from app.repositories.research import ResearchRepository
from app.repositories.research_proposal import ResearchProposalRepository
from app.repositories.research_run import ResearchRunRepository
from app.repositories.research_run_event import ResearchRunEventRepository
from app.services.research_conversation import ResearchConversationService


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


def get_research_conversation_service(
    session: AsyncSession = Depends(get_db),
) -> ResearchConversationService:
    """
    Return a request-scoped ResearchConversationService bound to this
    request's database session -- mirrors `get_conversation_service`
    (Chat's equivalent), for the `/research/conversations` routes which
    don't need the rest of `ResearchService`'s collaborators.
    """

    return ResearchConversationService(session)


def get_research_run_repository(
    session: AsyncSession = Depends(get_db),
) -> ResearchRunRepository:
    """Return a request-scoped, owner-scoped runtime-run repository."""

    return ResearchRunRepository(session)


def get_research_proposal_repository(
    session: AsyncSession = Depends(get_db),
) -> ResearchProposalRepository:
    """Return a request-scoped proposal repository (plan lookups, e.g. for
    conversation replay's Deep Research turns)."""

    return ResearchProposalRepository(session)


def get_research_run_event_repository(
    session: AsyncSession = Depends(get_db),
) -> ResearchRunEventRepository:
    return ResearchRunEventRepository(session)


def get_research_run_service(
    session: AsyncSession = Depends(get_db),
) -> ResearchRunService:
    """Return a request-scoped service for lifecycle actions (e.g. cancellation)."""

    return ResearchRunService(session)


def get_research_proposal_service(
    session: AsyncSession = Depends(get_db),
    generation_runtime: GenerationRuntime = Depends(get_generation_runtime),
    memory_service: MemoryService = Depends(get_memory_service),
) -> ResearchProposalService:
    return ResearchProposalService(
        session=session,
        generation_runtime=generation_runtime,
        memory_service=memory_service,
    )


def get_research_draft_inspection_service() -> ResearchDraftInspectionService:
    """Stateless (just holds the database URL) -- new per request like the
    other lightweight collaborators here, not worth `@lru_cache`-ing."""

    return ResearchDraftInspectionService(database_url=settings.database_url)


def get_research_plan_inspection_service() -> ResearchPlanInspectionService:
    """Stateless, mirrors `get_research_draft_inspection_service`."""

    return ResearchPlanInspectionService(database_url=settings.database_url)


def get_research_web_search_inspection_service() -> ResearchWebSearchInspectionService:
    """Stateless, mirrors `get_research_plan_inspection_service`."""

    return ResearchWebSearchInspectionService(database_url=settings.database_url)


@lru_cache
def get_web_search_service() -> WebSearchService:
    return create_web_search_service()


@lru_cache
def get_web_search_necessity_service() -> WebSearchNecessityService:
    return create_web_search_necessity_service()


@lru_cache
def get_paper_search_service() -> PaperSearchService:
    return create_paper_search_service()


@lru_cache
def get_paper_query_extraction_service() -> PaperQueryExtractionService:
    return create_paper_query_extraction_service()


def get_research_report_download_service(
    runs: ResearchRunRepository = Depends(get_research_run_repository),
    generation_usage: GenerationUsageRepository = Depends(get_generation_usage_repository),
    storage: DocumentStorage = Depends(get_document_storage),
) -> ResearchReportDownloadService:
    """Authorize short-lived download URLs without exposing storage keys."""

    return ResearchReportDownloadService(
        runs=runs, generation_usage=generation_usage, storage=storage
    )


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
    session_state_updater: SessionStateUpdaterService = Depends(get_session_state_updater_service),
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
        session_state_updater=session_state_updater,
        memory_service=memory_service,
        memory_extraction_service=memory_extraction_service,
        metrics=get_metrics_recorder(),
    )


async def get_research_runtime_execution_service(
    research_service: ResearchService = Depends(get_research_service),
    generation_runtime: GenerationRuntime = Depends(get_generation_runtime),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    context_builder: ContextBuilderService = Depends(get_context_builder),
    storage: DocumentStorage = Depends(get_document_storage),
    memory_service: MemoryService = Depends(get_memory_service),
    web_search: WebSearchService = Depends(get_web_search_service),
    web_search_necessity: WebSearchNecessityService = Depends(get_web_search_necessity_service),
    paper_search: PaperSearchService = Depends(get_paper_search_service),
    paper_query_extraction: PaperQueryExtractionService = Depends(
        get_paper_query_extraction_service
    ),
) -> AsyncGenerator[ResearchRuntimeExecutionService | None, None]:
    """Construct the bridge only for the explicitly enabled durable path."""

    if not (
        settings.research_runtime_enabled
        and settings.research_runtime_postgres_checkpointing_enabled
    ):
        yield None
        return

    async with SessionFactory() as session:
        yield ResearchRuntimeExecutionService(
            session=session,
            research_service=research_service,
            database_url=settings.database_url,
            generation_runtime=generation_runtime,
            retrieval_service=retrieval_service,
            context_builder=context_builder,
            storage=storage,
            v1_graph_enabled=settings.research_runtime_v1_graph_enabled,
            memory_service=memory_service,
            web_search=web_search,
            web_search_necessity=web_search_necessity,
            paper_search=paper_search,
            paper_query_extraction=paper_query_extraction,
            metrics=get_metrics_recorder(),
        )
