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
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import structlog
from langchain_core.messages import BaseMessage, HumanMessage
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
from app.ai.memory.create import create_memory_availability_client, get_memory_metrics
from app.ai.memory.enums import MemoryType
from app.ai.memory.extraction.orchestrator import MemoryExtractionOrchestrator
from app.ai.memory.extraction.service import MemoryExtractionService
from app.ai.memory.policy.models import MemoryTurnEvent
from app.ai.memory.services.formatting import (
    FormattedMemoryContext,
    format_memory_context_with_ids,
    with_memory_context,
)
from app.ai.memory.services.memory_service import MemoryService
from app.ai.memory.session.state_updater import (
    SessionStateUpdaterService,
    distill_and_upsert_session_state,
)
from app.ai.research.models import ResearchOutcome, ResearchSource
from app.ai.runtime.events.enums import CoreEventType, EventCategory
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.events.research.models import ResearchEventType
from app.ai.runtime.generation.caching.enums import CacheRuntime
from app.ai.runtime.generation.config_fingerprint import config_fingerprint_kwargs
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import GenerationRequest, StreamEventType
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface
from app.ai.runtime.generation.routing.enums import RoutingStrategy
from app.ai.runtime.generation.streaming.service import StreamingService
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.synthesis.models import ResearchDraft
from app.core.settings import settings
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.infrastructure.metrics.noop import NoOpMetricsRecorder
from app.infrastructure.metrics.research import (
    RESEARCH_DURATION,
    RESEARCH_RUNS_COMPLETED_TOTAL,
    RESEARCH_RUNS_FAILED_TOTAL,
    RESEARCH_RUNS_TOTAL,
)
from app.models.research import ResearchSession
from app.repositories.research import ResearchRepository
from app.services.research_conversation import ResearchConversationService

logger = structlog.get_logger()

_SOURCE_MODE = "linear"


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
        memory_service: MemoryService | None = None,
        memory_extraction_service: MemoryExtractionService | None = None,
        session_state_updater: SessionStateUpdaterService | None = None,
        metrics: MetricsRecorder | None = None,
    ) -> None:
        self._metrics = metrics or NoOpMetricsRecorder()
        self._session = session
        self._repository = ResearchRepository(session)
        self._conversations = ResearchConversationService(session, self._repository)
        self._retrieval = retrieval_service
        self._context_builder = context_builder
        self._generation_runtime = generation_runtime
        self._streaming_service = streaming_service
        self._artifact_writer = research_artifact_writer
        self._artifact_policy = artifact_policy_service
        self._memory = memory_service
        """
        Optional (Runtime Memory Injection Pipeline). When set,
        `research()`/`stream_research()` prepend a Memory Context block
        (session/semantic/research memories) to the prompt before
        generation and, best-effort, extract + store new memories from
        the completed turn afterward. `None` skips both -- matches how
        every other optional collaborator on this service degrades.
        """
        self._memory_extraction = memory_extraction_service
        self._session_state_updater = session_state_updater

    async def research(
        self,
        *,
        query: str,
        top_k: int,
        filters: dict[str, Any],
        owner_id: UUID,
        provider: GenerationProvider | None = None,
        routing_strategy: RoutingStrategy | None = None,
        conversation_id: UUID | None = None,
    ) -> ResearchOutcome:
        """
        Full linear flow (PRD §17, extended with the Memory Platform's
        Runtime Memory Injection Pipeline and conversation threading):
        get-or-create conversation -> memory retrieval -> retrieve ->
        build context -> generate through the Generation Runtime ->
        persist session + artifact -> memory extraction.

        `conversation_id` lets a caller link multiple `/research` calls
        into one continuing thread -- omit it for a fresh, single-turn
        thread (mirrors `chat.py`'s `ConversationService.get_or_create()`
        pattern). The conversation's own id doubles as the session-memory
        boundary, replacing the old default of "a fresh session per call"
        that made SESSION memory a no-op across turns.
        """

        conversation = await self._conversations.get_or_create(
            conversation_id=conversation_id,
            owner_id=owner_id,
        )
        await self._conversations.set_title_from_first_query(
            conversation=conversation,
            query=query,
        )

        research_id = uuid4()
        session_id = conversation.id

        started = perf_counter()

        self._metrics.increment(
            metric=RESEARCH_RUNS_TOTAL,
            labels={"source_mode": _SOURCE_MODE},
        )

        try:
            history = await self._conversations.load_history(
                conversation_id=conversation.id,
                owner_id=owner_id,
            )

            memory_context = await self._retrieve_memory_context(
                owner_id=owner_id,
                session_id=session_id,
                query=query,
                transcript="\n".join(str(message.content) for message in history),
            )

            retrieval_result, context_result = await self._retrieve_and_build_context(
                query=query,
                top_k=top_k,
                filters=filters,
                owner_id=owner_id,
            )

            request = GenerationRequest(
                prompt_context=with_memory_context(
                    context_result.prompt_context,
                    memory_context.text,
                ),
                user_prompt=self._format_transcript(history, query),
                owner_id=owner_id,
                conversation_id=conversation.id,
                session_id=research_id,
                routing_strategy=routing_strategy,
                cache_runtime=CacheRuntime.RESEARCH,
                runtime=RuntimeType.RESEARCH,
                artifact_runtime=ArtifactRuntime.RESEARCH,
                metadata={"injected_memory_ids": [str(item) for item in memory_context.memory_ids]}
                if memory_context.memory_ids
                else {},
                **config_fingerprint_kwargs(
                    surface="linear_research", prompt_version="linear-research-v1"
                ),
            )

            result = await self._generation_runtime.execute(request, provider=provider)

            duration_ms = (perf_counter() - started) * 1000

            sources = self._build_sources(context_result)
            citations = context_result.prompt_context.citations

            await self._persist_session(
                research_id=research_id,
                conversation_id=conversation.id,
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

            await self._extract_and_store_memory(
                owner_id=owner_id,
                session_id=session_id,
                research_id=research_id,
                query=query,
                answer=result.content,
            )
        except Exception as exc:
            self._metrics.increment(
                metric=RESEARCH_RUNS_FAILED_TOTAL,
                labels={"source_mode": _SOURCE_MODE, "failure_type": type(exc).__name__},
            )
            self._metrics.record_duration(
                operation=RESEARCH_DURATION,
                duration_ms=(perf_counter() - started) * 1000,
                labels={"source_mode": _SOURCE_MODE},
            )
            raise

        self._metrics.increment(
            metric=RESEARCH_RUNS_COMPLETED_TOTAL,
            labels={"source_mode": _SOURCE_MODE},
        )
        self._metrics.record_duration(
            operation=RESEARCH_DURATION,
            duration_ms=duration_ms,
            labels={"source_mode": _SOURCE_MODE},
        )

        return ResearchOutcome(
            research_id=research_id,
            conversation_id=conversation.id,
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
        conversation_id: UUID | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Streaming counterpart of `research()` (PRD §17), extended with
        the same Runtime Memory Injection Pipeline and conversation
        threading -- see `research()`'s docstring. Generation goes
        through `StreamingService` directly rather than the Generation
        Runtime -- that's what the PRD's own `/research/stream` flow
        diagram specifies, distinct from `/research`.
        """

        conversation = await self._conversations.get_or_create(
            conversation_id=conversation_id,
            owner_id=owner_id,
        )
        await self._conversations.set_title_from_first_query(
            conversation=conversation,
            query=query,
        )

        research_id = uuid4()
        session_id = conversation.id

        # `session_id` here stays `research_id`, not `conversation.id` --
        # the frontend (`use-research.ts`) reads the first event's
        # `session_id` as the turn's own `research_id` for `GET
        # /research/{id}` replay, unchanged wire shape. `conversation_id`
        # rides in `metadata` instead so existing consumers aren't broken.
        yield StreamEvent(
            category=EventCategory.RESEARCH,
            type=ResearchEventType.RESEARCH_STARTED.value,
            session_id=research_id,
            metadata={"conversation_id": str(conversation.id)},
        )

        history = await self._conversations.load_history(
            conversation_id=conversation.id,
            owner_id=owner_id,
        )

        memory_context = await self._retrieve_memory_context(
            owner_id=owner_id,
            session_id=session_id,
            query=query,
            transcript="\n".join(str(message.content) for message in history),
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
            prompt_context=with_memory_context(
                context_result.prompt_context,
                memory_context.text,
            ),
            user_prompt=self._format_transcript(history, query),
            stream=True,
            owner_id=owner_id,
            conversation_id=conversation.id,
            session_id=research_id,
            routing_strategy=routing_strategy,
            cache_runtime=CacheRuntime.RESEARCH,
            runtime=RuntimeType.RESEARCH,
            artifact_runtime=ArtifactRuntime.RESEARCH,
            metadata={"injected_memory_ids": [str(item) for item in memory_context.memory_ids]}
            if memory_context.memory_ids
            else {},
            **config_fingerprint_kwargs(
                surface="linear_research", prompt_version="linear-research-v1"
            ),
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
                    conversation_id=conversation.id,
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

                await self._extract_and_store_memory(
                    owner_id=owner_id,
                    session_id=session_id,
                    research_id=research_id,
                    query=query,
                    answer=answer,
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

    async def publish_runtime_report(
        self,
        *,
        query: str,
        draft: ResearchDraft,
        evidence: ResearchEvidenceBundle,
        owner_id: UUID,
        conversation_id: UUID | None,
        duration_ms: float,
        memory_used: bool = False,
    ) -> ResearchOutcome:
        """Persist a reviewed runtime draft before invoking memory extraction.

        This is intentionally the only handoff from the graph to durable user
        state. Planner, retrieval, reviewer, and PDF nodes never receive the
        memory collaborators.
        """

        conversation = await self._conversations.get_or_create(
            conversation_id=conversation_id,
            owner_id=owner_id,
        )
        await self._conversations.set_title_from_first_query(conversation=conversation, query=query)
        research_id = uuid4()
        citations, sources = self._runtime_evidence_metadata(evidence)
        answer = self._format_runtime_draft(draft)
        await self._persist_session(
            research_id=research_id,
            conversation_id=conversation.id,
            owner_id=owner_id,
            query=query,
            answer=answer,
            citations=citations,
            sources=sources,
            runtime_metadata={
                "runtime": "research_runtime_v1",
                "report_title": draft.title,
                "generation_id": str(draft.generation_id) if draft.generation_id else None,
                "memory_used": memory_used,
            },
        )
        await self._extract_and_store_memory(
            owner_id=owner_id,
            session_id=conversation.id,
            research_id=research_id,
            query=query,
            answer=answer,
        )
        return ResearchOutcome(
            research_id=research_id,
            conversation_id=conversation.id,
            query=query,
            answer=answer,
            citations=citations,
            sources=sources,
            duration_ms=duration_ms,
        )

    # ==========================================================
    # Internal helpers
    # ==========================================================

    # -- Runtime Memory Injection Pipeline -----------------------

    async def _retrieve_memory_context(
        self,
        *,
        owner_id: UUID,
        session_id: UUID,
        query: str,
        transcript: str | None = None,
    ) -> FormattedMemoryContext:
        """
        Memory retrieval, ahead of knowledge retrieval (Request ->
        Memory Retrieval -> Knowledge Retrieval -> ... per the platform's
        runtime integration flow). Best-effort: a memory outage must
        never block a research request.
        """

        if self._memory is None:
            return FormattedMemoryContext(text=None, memory_ids=())

        try:
            context = await self._memory.get_context(
                owner_id=owner_id,
                session_id=session_id,
                semantic_query=query,
                top_k=5,
                transcript=transcript,
            )
        except Exception as exc:
            logger.warning(
                "memory.research.retrieval_failed",
                owner_id=str(owner_id),
                session_id=str(session_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return FormattedMemoryContext(text=None, memory_ids=())

        return format_memory_context_with_ids(context)

    async def _extract_and_store_memory(
        self,
        *,
        owner_id: UUID,
        session_id: UUID,
        research_id: UUID,
        query: str,
        answer: str,
    ) -> None:
        """
        Post-generation half of the Runtime Memory Injection Pipeline:
        the raw turn is always captured as SESSION memory (unconditional
        -- it's the conversational record, not an LLM judgment call);
        durable USER/RESEARCH facts are additionally proposed by
        `MemoryExtractionService` and stored when above the importance
        threshold. Best-effort throughout: never fails the request that
        already completed successfully.
        """

        if self._memory is None:
            return

        try:
            if settings.memory_session_raw_turn_storage_enabled:
                await self._memory.remember(
                    owner_id=owner_id,
                    type=MemoryType.SESSION,
                    content=f"Q: {query}\nA: {answer}",
                    session_id=session_id,
                    metadata={
                        "kind": "raw_turn",
                        "source_turn_id": str(research_id),
                        "research_id": str(research_id),
                    },
                )
            elif (
                settings.memory_session_state_storage_enabled
                and self._session_state_updater is not None
            ):
                await distill_and_upsert_session_state(
                    memory_service=self._memory,
                    session_state_updater=self._session_state_updater,
                    owner_id=owner_id,
                    session_id=session_id,
                    user_message=query,
                    assistant_message=answer,
                    turn_id=str(research_id),
                )
        except Exception as exc:
            logger.warning(
                "memory.research.session_remember_failed",
                owner_id=str(owner_id),
                session_id=str(session_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )

        if self._memory_extraction is None:
            return

        try:
            await MemoryExtractionOrchestrator(
                self._memory,
                self._memory_extraction,
                create_memory_availability_client(),
                get_memory_metrics(),
            ).process_turn(
                MemoryTurnEvent(
                    owner_id=owner_id,
                    session_id=session_id,
                    conversation_id=session_id,
                    research_id=research_id,
                    runtime="research",
                    user_message=query,
                    assistant_message=answer,
                    turn_id=f"research:{research_id}",
                )
            )
        except Exception as exc:
            logger.warning(
                "memory.research.extraction_orchestration_failed",
                research_id=str(research_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )

    # -- Retrieval / context / persistence -----------------------

    def _scoped_query(
        self,
        *,
        query: str,
        top_k: int,
        filters: dict[str, Any],
        owner_id: UUID,
    ) -> RetrievalQuery:
        """
        `owner_id` always comes from the authenticated caller, never from
        request-supplied filters -- mirrors
        `api/v1/retrieval.py::_scoped_owner_id`.
        """

        return RetrievalQuery(
            query=query,
            top_k=top_k,
            filters=filters,
            owner_id=str(owner_id),
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
    def _format_transcript(history: list[BaseMessage], query: str) -> str:
        """
        Folds prior turns of the conversation into a plain-text transcript
        prefix for `query` -- mirrors `chat.py::_format_transcript`
        (same scope limitation: no native multi-message array support in
        `BaseGenerationProvider.build_messages` yet, so history is folded
        into `user_prompt` as text). Without this, a follow-up like "so
        if I make a RAG application..." has no way to resolve what "so"
        refers to -- only the current turn's `query` reaches the prompt.
        """

        if not history:
            return query

        lines = [
            f"{'User' if isinstance(message, HumanMessage) else 'Assistant'}: {message.content}"
            for message in history
        ]

        lines.append(f"User: {query}")

        return "\n".join(lines)

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

    @staticmethod
    def _coerce_uuid(value: str) -> UUID:
        """`Citation`/`ResearchSource` require real `UUID` fields, but web
        evidence (`ResearchEvidenceReference.source_type == "web"`) carries a
        URL/synthetic string in `document_id`/`chunk_id` instead of a real
        document/chunk UUID. Deterministically derive a stable UUID from the
        string rather than raising -- the same URL/chunk id always maps to
        the same synthetic UUID, so repeated runs stay consistent, and this
        never collides with a real `uuid4()`-generated document/chunk id
        (UUID5 vs UUID4 namespaces don't overlap in practice)."""

        try:
            return UUID(value)
        except ValueError:
            return uuid5(NAMESPACE_URL, value)

    @staticmethod
    def _runtime_evidence_metadata(
        evidence: ResearchEvidenceBundle,
    ) -> tuple[list[Citation], list[ResearchSource]]:
        """Convert compact, already-owner-scoped evidence references to API metadata."""

        citations: list[Citation] = []
        sources: list[ResearchSource] = []
        seen_citations: set[str] = set()
        seen_sources: set[tuple[str, str]] = set()
        for item in evidence.evidence:
            document_id = ResearchService._coerce_uuid(item.document_id)
            chunk_id = ResearchService._coerce_uuid(item.chunk_id)
            source_key = (item.document_id, item.chunk_id)
            if source_key not in seen_sources:
                sources.append(
                    ResearchSource(
                        document_id=document_id,
                        filename=item.filename,
                        chunk_id=chunk_id,
                        score=item.score,
                    )
                )
                seen_sources.add(source_key)
            if item.citation_id and item.citation_id not in seen_citations:
                citations.append(
                    Citation(
                        citation_id=item.citation_id,
                        filename=item.filename,
                        document_id=document_id,
                        score=item.score,
                        chunk_ids=[chunk_id],
                    )
                )
                seen_citations.add(item.citation_id)
        return citations, sources

    @staticmethod
    def _format_runtime_draft(draft: ResearchDraft) -> str:
        sections = [
            ("Abstract", draft.abstract),
            ("Methodology", draft.methodology),
            *[(finding.heading, finding.content) for finding in draft.findings],
            ("Discussion", draft.discussion),
            ("Conclusion", draft.conclusion),
        ]
        if draft.limitations:
            sections.append(("Limitations", "\n".join(f"- {item}" for item in draft.limitations)))
        if draft.citation_ids:
            sections.append(("References", "\n".join(f"- [{item}]" for item in draft.citation_ids)))
        rendered_sections = [f"## {heading}\n{content}" for heading, content in sections]
        return "\n\n".join([f"# {draft.title}", *rendered_sections])

    async def _persist_session(
        self,
        *,
        research_id: UUID,
        conversation_id: UUID,
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
                conversation_id=conversation_id,
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
