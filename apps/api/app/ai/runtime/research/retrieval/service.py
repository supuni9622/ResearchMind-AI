"""Reuse Retrieval and Context platforms for bounded, owner-scoped task execution."""

from __future__ import annotations

import asyncio
from uuid import UUID

import structlog

from app.ai.knowledge.context.interfaces import ContextBuilderInterface
from app.ai.knowledge.retrieval.enums import RetrievalProvider
from app.ai.knowledge.retrieval.models import RetrievalQuery
from app.ai.knowledge.retrieval.service import RetrievalService
from app.ai.runtime.research.planner.models import ResearchPlanTask
from app.ai.runtime.research.retrieval.models import (
    ResearchEvidenceReference,
    ResearchTaskResult,
    ResearchTaskStatus,
)

logger = structlog.get_logger()


class ResearchTaskRetrievalService:
    """Executes tasks from a validated dependency wave with bounded parallelism.

    This service deliberately retains only source identifiers and short excerpts;
    report generation later reloads any needed context through canonical services.

    LangGraph fans a wave out via `Send`, invoking `execute_task` once per task
    rather than calling a batch method, so the concurrency bound lives on this
    instance's shared semaphore rather than in a separate wave-level wrapper.
    """

    MAX_TASK_TOP_K = 8
    MAX_EVIDENCE_PER_TASK = 8
    MAX_EXCERPT_CHARACTERS = 500

    def __init__(
        self,
        *,
        retrieval_service: RetrievalService,
        context_builder: ContextBuilderInterface,
        max_concurrency: int = 3,
    ) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least one.")
        self._retrieval = retrieval_service
        self._context_builder = context_builder
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def execute_task(
        self,
        *,
        task: ResearchPlanTask,
        owner_id: UUID,
        filters: dict[str, object],
        top_k: int,
        project_id: UUID | None = None,
    ) -> ResearchTaskResult:
        """Run canonical retrieval/context construction for one task, fail as a partial result.

        `project_id=None` means personal documents only, not "every
        project" -- this is what makes a project's Deep Research run
        search that project's own documents.
        """

        async with self._semaphore:
            return await self._execute_task(
                task=task,
                owner_id=owner_id,
                filters=filters,
                top_k=top_k,
                project_id=project_id,
            )

    async def _execute_task(
        self,
        *,
        task: ResearchPlanTask,
        owner_id: UUID,
        filters: dict[str, object],
        top_k: int,
        project_id: UUID | None = None,
    ) -> ResearchTaskResult:
        try:
            retrieval = await self._retrieval.search_hybrid(
                provider=RetrievalProvider.QDRANT,
                query=RetrievalQuery(
                    query=task.question,
                    top_k=min(top_k, self.MAX_TASK_TOP_K),
                    filters=filters,
                    owner_id=str(owner_id),
                    project_id=str(project_id) if project_id else None,
                ),
            )
            context = await self._context_builder.build(retrieval, query=task.question)
            chunks = context.prompt_context.chunks[: self.MAX_EVIDENCE_PER_TASK]
            return ResearchTaskResult(
                task_id=task.task_id,
                status=ResearchTaskStatus.COMPLETED,
                retrieval_id=str(retrieval.retrieval_id),
                evidence=[
                    ResearchEvidenceReference(
                        document_id=str(chunk.document_id),
                        chunk_id=str(chunk.chunk_id),
                        filename=chunk.filename,
                        citation_id=chunk.citation_id,
                        score=chunk.score,
                        excerpt=chunk.content[: self.MAX_EXCERPT_CHARACTERS],
                    )
                    for chunk in chunks
                ],
                citation_ids=[
                    citation.citation_id
                    for citation in context.prompt_context.citations[: self.MAX_EVIDENCE_PER_TASK]
                ],
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "research_runtime.retrieval.task_failed",
                task_id=task.task_id,
                owner_id=str(owner_id),
                error_type=type(exc).__name__,
            )
            return ResearchTaskResult(
                task_id=task.task_id,
                status=ResearchTaskStatus.FAILED,
                error_type=type(exc).__name__,
            )
