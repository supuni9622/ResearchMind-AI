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
from app.ai.memory.enums import MemoryType
from app.ai.memory.extraction.service import MemoryExtractionService
from app.ai.memory.services.formatting import format_memory_context, with_memory_context
from app.ai.memory.services.memory_service import MemoryService
from app.ai.research.models import ResearchOutcome, ResearchSource
from app.ai.runtime.events.enums import CoreEventType, EventCategory
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.events.research.models import ResearchEventType
from app.ai.runtime.generation.caching.enums import CacheRuntime
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import GenerationRequest, StreamEventType
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface
from app.ai.runtime.generation.routing.enums import RoutingStrategy
from app.ai.runtime.generation.streaming.service import StreamingService
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType
from app.models.research import ResearchSession
from app.repositories.research import ResearchRepository
from app.services.research_conversation import ResearchConversationService

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
        memory_service: MemoryService | None = None,
        memory_extraction_service: MemoryExtractionService | None = None,
    ) -> None:
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

        history = await self._conversations.load_history(
            conversation_id=conversation.id,
            owner_id=owner_id,
        )

        memory_context_text = await self._retrieve_memory_context(
            owner_id=owner_id,
            session_id=session_id,
            query=query,
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
                memory_context_text,
            ),
            user_prompt=self._format_transcript(history, query),
            owner_id=owner_id,
            session_id=research_id,
            routing_strategy=routing_strategy,
            cache_runtime=CacheRuntime.RESEARCH,
            runtime=RuntimeType.RESEARCH,
            artifact_runtime=ArtifactRuntime.RESEARCH,
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

        memory_context_text = await self._retrieve_memory_context(
            owner_id=owner_id,
            session_id=session_id,
            query=query,
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
                memory_context_text,
            ),
            user_prompt=self._format_transcript(history, query),
            stream=True,
            owner_id=owner_id,
            session_id=research_id,
            routing_strategy=routing_strategy,
            cache_runtime=CacheRuntime.RESEARCH,
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
    ) -> str | None:
        """
        Memory retrieval, ahead of knowledge retrieval (Request ->
        Memory Retrieval -> Knowledge Retrieval -> ... per the platform's
        runtime integration flow). Best-effort: a memory outage must
        never block a research request.
        """

        if self._memory is None:
            return None

        try:
            context = await self._memory.get_context(
                owner_id=owner_id,
                session_id=session_id,
                semantic_query=query,
                top_k=5,
            )
        except Exception as exc:
            logger.warning(
                "memory.research.retrieval_failed",
                owner_id=str(owner_id),
                session_id=str(session_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return None

        return format_memory_context(context)

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
            await self._memory.remember(
                owner_id=owner_id,
                type=MemoryType.SESSION,
                content=f"Q: {query}\nA: {answer}",
                session_id=session_id,
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

        extracted = await self._memory_extraction.extract(
            user_message=query,
            assistant_message=answer,
            owner_id=owner_id,
            conversation_id=session_id,
        )

        for item in extracted:
            metadata = (
                {"research_id": str(research_id)} if item.type == MemoryType.RESEARCH else None
            )

            try:
                await self._memory.remember(
                    owner_id=owner_id,
                    type=item.type,
                    content=item.content,
                    importance_score=item.importance,
                    metadata=metadata,
                )
            except Exception as exc:
                logger.warning(
                    "memory.research.extracted_remember_failed",
                    owner_id=str(owner_id),
                    memory_type=item.type.value,
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
