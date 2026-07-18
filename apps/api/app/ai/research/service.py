"""
Research Service (research_api_prd.md §10) -- the orchestration layer
for `/research`, `/research/stream`, and `/research/citations`.

Composes the Retrieval, Context, Generation Runtime, and Streaming
platforms exactly as each already exists; this module adds no new
retrieval/context/generation logic of its own (PRD §4 Non-Goals).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.artifacts.enums import ArtifactCategory, ArtifactRuntime
from app.ai.artifacts.policies.service import ArtifactPolicyService
from app.ai.artifacts.research.builders import ResearchArtifactBuilder
from app.ai.artifacts.research.writers import ResearchArtifactWriter
from app.ai.knowledge.context.citations.models import Citation
from app.ai.knowledge.context.models import ContextResult
from app.ai.knowledge.context.service import ContextBuilderService
from app.ai.knowledge.retrieval.enums import RetrievalProvider
from app.ai.knowledge.retrieval.models import RetrievalQuery, RetrievalResult
from app.ai.knowledge.retrieval.service import RetrievalService
from app.ai.research.models import ResearchOutcome, ResearchSource
from app.ai.runtime.events.enums import CoreEventType, EventCategory
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.events.research.models import ResearchEventType
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import GenerationRequest, StreamEventType
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface
from app.ai.runtime.generation.routing.enums import RoutingStrategy
from app.ai.runtime.generation.streaming.service import StreamingService
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType
from app.models.research import ResearchSession
from app.repositories.research import ResearchRepository

logger = structlog.get_logger()


class ResearchService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        retrieval_service: RetrievalService,
        context_builder: ContextBuilderService,
        generation_runtime: GenerationRuntimeInterface,
        streaming_service: StreamingService,
        research_artifact_writer: ResearchArtifactWriter | None = None,
        artifact_policy_service: ArtifactPolicyService | None = None,
    ) -> None:
        self._session = session
        self._repository = ResearchRepository(session)
        self._retrieval = retrieval_service
        self._context_builder = context_builder
        self._generation_runtime = generation_runtime
        self._streaming_service = streaming_service
        self._artifact_writer = research_artifact_writer
        self._artifact_policy = artifact_policy_service

    async def research(
        self,
        *,
        query: str,
        top_k: int,
        filters: dict[str, Any],
        owner_id: UUID,
        provider: GenerationProvider | None = None,
        routing_strategy: RoutingStrategy | None = None,
    ) -> ResearchOutcome:
        """
        Full linear flow (PRD §17): retrieve -> build context -> generate
        through the Generation Runtime -> persist session + artifact.
        """

        research_id = uuid4()

        started = perf_counter()

        retrieval_result, context_result = await self._retrieve_and_build_context(
            query=query,
            top_k=top_k,
            filters=filters,
            owner_id=owner_id,
        )

        request = GenerationRequest(
            prompt_context=context_result.prompt_context,
            user_prompt=query,
            session_id=research_id,
            routing_strategy=routing_strategy,
            runtime=RuntimeType.RESEARCH,
            artifact_runtime=ArtifactRuntime.RESEARCH,
        )

        result = await self._generation_runtime.execute(request, provider=provider)

        duration_ms = (perf_counter() - started) * 1000

        sources = self._build_sources(context_result)
        citations = context_result.prompt_context.citations

        await self._persist_session(
            research_id=research_id,
            owner_id=owner_id,
            query=query,
            answer=result.content,
            citations=citations,
            sources=sources,
            runtime_metadata={
                "provider": result.provider.value,
                "model": result.model,
            },
        )

        await self._persist_artifact(
            research_id=research_id,
            owner_id=owner_id,
            retrieval_result=retrieval_result,
            citations=citations,
            answer=result.content,
            provider=result.provider.value,
            model=result.model,
        )

        return ResearchOutcome(
            research_id=research_id,
            query=query,
            answer=result.content,
            citations=citations,
            sources=sources,
            duration_ms=duration_ms,
        )

    async def stream_research(
        self,
        *,
        query: str,
        top_k: int,
        filters: dict[str, Any],
        owner_id: UUID,
        provider: GenerationProvider | None = None,
        routing_strategy: RoutingStrategy | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Streaming counterpart of `research()` (PRD §17). Generation goes
        through `StreamingService` directly rather than the Generation
        Runtime -- that's what the PRD's own `/research/stream` flow
        diagram specifies, distinct from `/research`.
        """

        research_id = uuid4()

        yield StreamEvent(
            category=EventCategory.RESEARCH,
            type=ResearchEventType.RESEARCH_STARTED.value,
            session_id=research_id,
        )
        yield StreamEvent(
            category=EventCategory.RESEARCH,
            type=ResearchEventType.RETRIEVAL_STARTED.value,
            session_id=research_id,
        )

        retrieval_result, context_result = await self._retrieve_and_build_context(
            query=query,
            top_k=top_k,
            filters=filters,
            owner_id=owner_id,
        )

        yield StreamEvent(
            category=EventCategory.RESEARCH,
            type=ResearchEventType.RETRIEVAL_COMPLETED.value,
            session_id=research_id,
            metadata={"chunk_count": len(retrieval_result.chunks)},
        )

        request = GenerationRequest(
            prompt_context=context_result.prompt_context,
            user_prompt=query,
            stream=True,
            session_id=research_id,
            routing_strategy=routing_strategy,
            runtime=RuntimeType.RESEARCH,
            artifact_runtime=ArtifactRuntime.RESEARCH,
        )

        content_parts: list[str] = []

        async for event in self._streaming_service.stream_generate(
            request=request,
            provider=provider,
        ):
            if event.type == CoreEventType.TOKEN.value and event.content:
                content_parts.append(event.content)

            yield event

            # `StreamingService.stream_generate()` emits `StreamEventType.
            # COMPLETED` ("completed") for a live provider stream and only
            # ever emits `CoreEventType.COMPLETE` ("complete") on its
            # cache-hit replay path -- both mean "generation finished" from
            # this caller's perspective, so both must be checked here.
            if event.type in (CoreEventType.COMPLETE.value, StreamEventType.COMPLETED.value):
                answer = "".join(content_parts)
                sources = self._build_sources(context_result)
                citations = context_result.prompt_context.citations

                await self._persist_session(
                    research_id=research_id,
                    owner_id=owner_id,
                    query=query,
                    answer=answer,
                    citations=citations,
                    sources=sources,
                    runtime_metadata={
                        # The provider actually resolved by StreamingService
                        # (when `provider` was left unset) isn't surfaced back
                        # through the StreamEvent generator today -- only the
                        # caller-supplied override is known here.
                        "requested_provider": provider.value if provider else None,
                    },
                )

                await self._persist_artifact(
                    research_id=research_id,
                    owner_id=owner_id,
                    retrieval_result=retrieval_result,
                    citations=citations,
                    answer=answer,
                    provider=provider.value if provider else None,
                    model=None,
                )

    async def citations_only(
        self,
        *,
        query: str,
        top_k: int,
        filters: dict[str, Any],
        owner_id: UUID,
    ) -> list[Citation]:
        """
        Citation-panel preview (PRD's `/research/citations`) -- retrieval
        and context building only, no generation and no persistence.
        """

        retrieval_result = await self._retrieval.search_hybrid(
            provider=RetrievalProvider.QDRANT,
            query=self._scoped_query(
                query=query,
                top_k=top_k,
                filters=filters,
                owner_id=owner_id,
            ),
        )

        context_result = await self._context_builder.build(retrieval_result, query=query)

        return context_result.prompt_context.citations

    # ==========================================================
    # Internal helpers
    # ==========================================================

    def _scoped_query(
        self,
        *,
        query: str,
        top_k: int,
        filters: dict[str, Any],
        owner_id: UUID,
    ) -> RetrievalQuery:
        """
        `owner_id` is always overridden by the authenticated caller, never
        trusted from request-supplied filters -- mirrors
        `api/v1/retrieval.py::_scoped_filters`.
        """

        return RetrievalQuery(
            query=query,
            top_k=top_k,
            filters={**filters, "owner_id": str(owner_id)},
        )

    async def _retrieve_and_build_context(
        self,
        *,
        query: str,
        top_k: int,
        filters: dict[str, Any],
        owner_id: UUID,
    ) -> tuple[RetrievalResult, ContextResult]:
        retrieval_result = await self._retrieval.search_hybrid(
            provider=RetrievalProvider.QDRANT,
            query=self._scoped_query(
                query=query,
                top_k=top_k,
                filters=filters,
                owner_id=owner_id,
            ),
        )

        context_result = await self._context_builder.build(retrieval_result, query=query)

        return retrieval_result, context_result

    @staticmethod
    def _build_sources(context_result: ContextResult) -> list[ResearchSource]:
        return [
            ResearchSource(
                document_id=chunk.document_id,
                filename=chunk.filename,
                chunk_id=chunk.chunk_id,
                score=chunk.score,
                page=chunk.page_numbers[0] if chunk.page_numbers else None,
            )
            for chunk in context_result.prompt_context.chunks
        ]

    async def _persist_session(
        self,
        *,
        research_id: UUID,
        owner_id: UUID,
        query: str,
        answer: str,
        citations: list[Citation],
        sources: list[ResearchSource],
        runtime_metadata: dict[str, Any],
    ) -> ResearchSession:
        research_session = await self._repository.create(
            ResearchSession(
                id=research_id,
                owner_id=owner_id,
                query=query,
                answer=answer,
                citations=[citation.model_dump(mode="json") for citation in citations],
                sources=[source.model_dump(mode="json") for source in sources],
                runtime_metadata=runtime_metadata,
            ),
        )

        await self._session.commit()

        return research_session

    async def _persist_artifact(
        self,
        *,
        research_id: UUID,
        owner_id: UUID,
        retrieval_result: RetrievalResult,
        citations: list[Citation],
        answer: str,
        provider: str | None,
        model: str | None,
    ) -> None:
        """
        Best-effort (Artifact Platform PRD §24), same pattern as
        `chat.py::_persist_on_complete` -- never blocks or fails the
        request/stream on a storage error.

        `plan`/`queries` are written empty: this milestone has no
        planning or decomposition (PRD §4 Non-Goals). The answer is
        folded into `report` rather than a separate `answer.md` file,
        since no endpoint contract needs a markdown export.
        """

        if self._artifact_writer is None:
            return

        if self._artifact_policy is not None and not self._artifact_policy.should_persist(
            ArtifactRuntime.RESEARCH,
            ArtifactCategory.RESEARCH,
        ):
            return

        try:
            artifact = ResearchArtifactBuilder().build(
                research_id=research_id,
                owner_id=owner_id,
                plan={},
                queries={},
                retrievals={
                    "chunks": [chunk.model_dump(mode="json") for chunk in retrieval_result.chunks],
                },
                citations={
                    "citations": [citation.model_dump(mode="json") for citation in citations],
                },
                report={"answer": answer, "provider": provider, "model": model},
            )

            await self._artifact_writer.write(artifact)
        except Exception as exc:
            logger.warning(
                "artifacts.research.persist_failed",
                research_id=str(research_id),
                reason="artifact_persistence_failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )
