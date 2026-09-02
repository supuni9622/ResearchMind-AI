"""
Application composition root.

This module constructs object graphs that are shared between
multiple application entry points (API, workers, CLI, etc.).
"""

from __future__ import annotations

from app.ai.artifacts.generation.readers import GenerationArtifactReader
from app.ai.knowledge.chunking.artifacts.builder import ChunkArtifactBuilder
from app.ai.knowledge.chunking.artifacts.writer import ChunkArtifactWriter
from app.ai.knowledge.chunking.factory import create_chunking_service
from app.ai.knowledge.embeddings.artifacts.builder import (
    EmbeddingArtifactBuilder,
)
from app.ai.knowledge.embeddings.artifacts.writer import (
    EmbeddingArtifactWriter,
)
from app.ai.knowledge.embeddings.create import (
    create_embedding_service,
)
from app.ai.knowledge.indexing.artifacts.builder import (
    IndexingArtifactBuilder,
)
from app.ai.knowledge.indexing.artifacts.writer import (
    IndexingArtifactWriter,
)
from app.ai.knowledge.indexing.create import (
    create_indexing_service,
)
from app.ai.knowledge.processing.artifact_builder import ArtifactBuilder
from app.ai.knowledge.processing.artifact_writer import ArtifactWriter
from app.ai.knowledge.processing.metadata.providers.language import (
    LanguageMetadataProvider,
)
from app.ai.knowledge.processing.metadata.providers.pdf import (
    PDFMetadataProvider,
)
from app.ai.knowledge.processing.metadata.registry import MetadataRegistry
from app.ai.knowledge.processing.metadata.service import (
    MetadataEnrichmentService,
)
from app.ai.knowledge.processing.parsers import DoclingParser
from app.ai.knowledge.processing.registry import ParserRegistry
from app.ai.knowledge.processing.service import ProcessingService
from app.ai.knowledge.processing.statistics.providers.pdf import (
    PDFStatisticsProvider,
)
from app.ai.knowledge.processing.statistics.registry import (
    StatisticsRegistry,
)
from app.ai.knowledge.processing.statistics.service import (
    StatisticsEnrichmentService,
)
from app.ai.knowledge.processing.temporary_file_manager import (
    TemporaryFileManager,
)
from app.ai.memory.create import (
    build_memory_extraction_service,
    build_memory_service,
    build_session_state_updater_service,
)
from app.ai.observability.create import get_observability_service
from app.ai.observability.prometheus.create import get_metrics_recorder
from app.ai.research.service import ResearchService
from app.ai.runtime.chat.paper_query import create_paper_query_extraction_service
from app.ai.runtime.generation.online_scoring.job import OnlineScoringJob, ScoreGenerationFn
from app.ai.runtime.generation.online_scoring.sampling import OnlineScoringConfig
from app.ai.runtime.research.charts.create import create_chart_generation_service
from app.ai.runtime.research.execution import ResearchRuntimeExecutionService
from app.ai.runtime.research.run_service import ResearchRunService
from app.ai.runtime.research.web_search.create import create_web_search_necessity_service
from app.ai.tools.paper_search.create import create_paper_search_service
from app.ai.tools.web_search.create import create_web_search_service
from app.core.settings import settings
from app.dependencies.context import get_context_builder
from app.dependencies.generation import (
    get_artifact_policy_service_dependency,
    get_generation_runtime,
    get_streaming_service,
)
from app.dependencies.research import get_research_artifact_writer
from app.dependencies.retrieval import get_retrieval_service
from app.infrastructure.queue.factory import create_processing_queue
from app.infrastructure.storage import create_storage
from app.repositories.document import DocumentRepository
from app.repositories.eval_score import EvalScoreRepository
from app.repositories.generation_usage import GenerationUsageRepository
from app.repositories.research_run import ResearchRunRepository
from app.repositories.research_run_dispatch import ResearchRunDispatchRepository
from app.services.document_processing_service import (
    DocumentProcessingService,
)
from app.services.queued_document_processing_service import (
    QueuedDocumentProcessingService,
)
from sqlalchemy.ext.asyncio import AsyncSession

from apps.worker.eval_scoring_worker import EvalScoringWorker
from apps.worker.processing_worker import ProcessingWorker
from apps.worker.research_runtime_worker import ResearchRuntimeWorker


def create_processing_worker(
    *,
    session: AsyncSession,
) -> ProcessingWorker:
    """
    Construct the processing worker object graph.
    """

    storage = create_storage(settings)

    parser_registry = ParserRegistry(
        parsers=[
            DoclingParser(),
        ],
    )

    metadata_registry = MetadataRegistry()
    metadata_registry.register(PDFMetadataProvider())
    metadata_registry.register(LanguageMetadataProvider())

    statistics_registry = StatisticsRegistry()
    statistics_registry.register(PDFStatisticsProvider())

    processing_service = ProcessingService(
        storage=storage,
        temporary_file_manager=TemporaryFileManager(),
        parser_registry=parser_registry,
        metadata_service=MetadataEnrichmentService(
            registry=metadata_registry,
        ),
        statistics_service=StatisticsEnrichmentService(
            registry=statistics_registry,
        ),
        artifact_builder=ArtifactBuilder(),
        artifact_writer=ArtifactWriter(storage),
        chunking_service=create_chunking_service(),
        chunk_artifact_builder=ChunkArtifactBuilder(),
        chunk_artifact_writer=ChunkArtifactWriter(storage),
        embedding_service=create_embedding_service(),
        embedding_artifact_builder=EmbeddingArtifactBuilder(),
        embedding_artifact_writer=EmbeddingArtifactWriter(storage),
        indexing_service=create_indexing_service(),
        indexing_artifact_builder=IndexingArtifactBuilder(),
        indexing_artifact_writer=IndexingArtifactWriter(storage),
        observability_service=get_observability_service(),
    )

    repository = DocumentRepository(session)

    document_processing_service = DocumentProcessingService(
        processing_service=processing_service,
        document_repository=repository,
        session=session,
    )

    queued_document_processing_service = QueuedDocumentProcessingService(
        document_processing_service=document_processing_service,
        document_repository=repository,
    )

    return ProcessingWorker(
        queue=create_processing_queue(settings),
        queued_document_processing_service=(queued_document_processing_service),
    )


def create_research_runtime_worker(*, session: AsyncSession) -> ResearchRuntimeWorker:
    """Compose the isolated worker that executes only approved research runs."""

    storage = create_storage(settings)
    memory_service = build_memory_service(session)
    research_service = ResearchService(
        session=session,
        retrieval_service=get_retrieval_service(),
        context_builder=get_context_builder(),
        generation_runtime=get_generation_runtime(),
        streaming_service=get_streaming_service(),
        research_artifact_writer=get_research_artifact_writer(),
        artifact_policy_service=get_artifact_policy_service_dependency(),
        memory_service=memory_service,
        memory_extraction_service=build_memory_extraction_service(),
        session_state_updater=build_session_state_updater_service(),
        metrics=get_metrics_recorder(),
    )
    execution = ResearchRuntimeExecutionService(
        session=session,
        research_service=research_service,
        database_url=settings.database_url,
        generation_runtime=get_generation_runtime(),
        retrieval_service=get_retrieval_service(),
        context_builder=get_context_builder(),
        storage=storage,
        v1_graph_enabled=settings.research_runtime_v1_graph_enabled,
        memory_service=memory_service,
        web_search=create_web_search_service(),
        web_search_necessity=create_web_search_necessity_service(),
        paper_search=create_paper_search_service(),
        paper_query_extraction=create_paper_query_extraction_service(),
        metrics=get_metrics_recorder(),
        chart_generation=create_chart_generation_service(),
    )
    runs = ResearchRunService(session)
    return ResearchRuntimeWorker(
        dispatches=ResearchRunDispatchRepository(session),
        execute_run=lambda run_id: execution.execute_approved_run(run_id=run_id),
        commit=session.commit,
        rollback=session.rollback,
        expire_stale_awaiting_approval=runs.expire_stale_awaiting_approval,
    )


def create_eval_scoring_worker(*, session: AsyncSession) -> EvalScoringWorker:
    """
    Compose the online scoring worker (E5, EVALUATION_PLAN.md §14).

    The Ragas judge (`benchmarks.generation.ragas_judge.
    build_openai_ragas_judge`) and its scoring function
    (`benchmarks.generation.ragas_scoring.score_generation`) are imported
    here, not by `OnlineScoringJob` itself -- this composition root is
    allowed to cross the app/`benchmarks` boundary the way it already
    wires other concrete infrastructure; `OnlineScoringJob` stays
    decoupled from repo-root tooling (see `online_scoring/job.py`'s
    module docstring). No key configured -> `judge=None`, and the job
    degrades gracefully to citation-only scoring rather than failing to
    start.

    E16 follow-up: the rubric judge (`benchmarks.generation.rubric_judge.
    build_rubric_judge`) is wired the same way, but additionally gated on
    `settings.eval_online_rubric_judge_enabled` (default off) -- a real,
    ongoing LLM-call cost an operator opts into deliberately, not just
    "OpenAI is configured at all."
    """

    storage = create_storage(settings)
    judge: object | None = None
    rubric_judge: object | None = None
    memory_utility_judge = None
    score_generation_fn: ScoreGenerationFn | None = None
    if settings.openai_api_key:
        from benchmarks.generation.ragas_judge import build_openai_ragas_judge
        from benchmarks.generation.ragas_scoring import score_generation

        judge = build_openai_ragas_judge()
        score_generation_fn = score_generation

        if settings.eval_online_rubric_judge_enabled:
            from benchmarks.generation.rubric_judge import build_rubric_judge

            rubric_judge = build_rubric_judge()

        if settings.memory_online_utility_judge_enabled:
            from app.ai.runtime.generation.online_scoring.memory_utility import (
                OpenAIMemoryUtilityJudge,
            )
            from openai import AsyncOpenAI

            memory_utility_judge = OpenAIMemoryUtilityJudge(
                client=AsyncOpenAI(api_key=settings.openai_api_key)
            )

    job = OnlineScoringJob(
        generation_usage_repository=GenerationUsageRepository(session),
        eval_score_repository=EvalScoreRepository(session),
        research_run_repository=ResearchRunRepository(session),
        artifact_reader=GenerationArtifactReader(storage),
        config=OnlineScoringConfig(
            baseline_sample_rate=settings.eval_online_baseline_sample_rate,
            canary_oversample_rate=settings.eval_online_canary_oversample_rate,
            canary_prompt_version=settings.eval_online_canary_prompt_version,
        ),
        commit=session.commit,
        rollback=session.rollback,
        score_generation_fn=score_generation_fn,
        judge=judge,
        rubric_judge=rubric_judge,
        memory_utility_judge=memory_utility_judge,
        batch_size=settings.eval_online_batch_size,
        lookback_hours=settings.eval_online_lookback_hours,
    )
    return EvalScoringWorker(
        job=job,
        poll_interval_seconds=settings.eval_online_poll_interval_seconds,
    )
