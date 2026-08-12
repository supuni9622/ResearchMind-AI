from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    status,
)
from fastapi.responses import StreamingResponse
from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import ValidationError

from app.ai.artifacts.conversation.builders import ConversationTurnArtifactBuilder
from app.ai.artifacts.conversation.models import ConversationIdentity
from app.ai.artifacts.conversation.writers import ConversationArtifactWriter
from app.ai.artifacts.enums import ArtifactCategory, ArtifactRuntime
from app.ai.artifacts.policies.service import ArtifactPolicyService
from app.ai.knowledge.context.models import PromptContext
from app.ai.memory.create import (
    build_memory_extraction_service,
    build_memory_service,
    build_session_state_updater_service,
    create_memory_availability_client,
    get_memory_metrics,
)
from app.ai.memory.enums import MemoryType
from app.ai.memory.extraction.orchestrator import MemoryExtractionOrchestrator
from app.ai.memory.extraction.service import MemoryExtractionService
from app.ai.memory.policy.models import MemoryTurnEvent
from app.ai.memory.services.formatting import format_memory_context, with_memory_context
from app.ai.memory.services.memory_service import MemoryService
from app.ai.memory.session.state_updater import (
    SessionStateUpdaterService,
    distill_and_upsert_session_state,
)
from app.ai.runtime.chat.paper_query import (
    PaperQueryExtractionService,
    create_paper_query_extraction_service,
)
from app.ai.runtime.chat.paper_search import run_chat_paper_search
from app.ai.runtime.chat.web_search import run_chat_web_search
from app.ai.runtime.events.enums import CoreEventType
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.generation.caching.enums import CachePolicy, CacheRuntime
from app.ai.runtime.generation.config_fingerprint import config_fingerprint_kwargs
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import GenerationRequest, StreamEventType
from app.ai.runtime.generation.service import GenerationService
from app.ai.runtime.generation.streaming.service import StreamingService
from app.ai.runtime.generation.streaming.transports.sse import sse_stream_response
from app.ai.runtime.generation.streaming.transports.websocket import run_websocket_stream
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType
from app.ai.runtime.research.web_search.create import create_web_search_necessity_service
from app.ai.runtime.research.web_search.necessity import WebSearchNecessityService
from app.ai.tools.paper_search.create import create_paper_search_service
from app.ai.tools.paper_search.service import PaperSearchService
from app.ai.tools.web_search.create import create_web_search_service
from app.ai.tools.web_search.service import WebSearchService
from app.auth.dependencies import authenticate_token, get_current_user
from app.core.settings import settings
from app.db.session import SessionFactory
from app.dependencies.generation import (
    get_artifact_policy_service_dependency,
    get_conversation_artifact_writer,
    get_conversation_service,
    get_generation_service,
    get_streaming_service,
)
from app.dependencies.memory import (
    get_memory_extraction_service,
    get_memory_service,
    get_session_state_updater_service,
)
from app.dependencies.rate_limiting import enforce_rate_limit, get_rate_limiter
from app.dependencies.research import (
    get_paper_query_extraction_service,
    get_paper_search_service,
    get_web_search_necessity_service,
    get_web_search_service,
)
from app.exceptions.base import AppException, RateLimitExceededException
from app.infrastructure.rate_limiting import ValkeyRateLimiter
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.schemas.chat import (
    ChatConversationListResponse,
    ChatConversationResponse,
    ChatConversationSummary,
    ChatMessageResponse,
    ChatStreamRequest,
)
from app.services.conversation import ConversationService, PromptHistory

logger = structlog.get_logger()

_COMPLETION_EVENT_TYPES = {
    CoreEventType.COMPLETE.value,
    StreamEventType.COMPLETED.value,
}

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


async def _check_chat_rate_limit(*, rate_limiter: ValkeyRateLimiter, owner_id: UUID) -> None:
    """Raise if `owner_id` has exceeded the per-window chat-turn cap.

    Called before any conversation/generation work starts on both
    `/chat/stream` and `/chat/ws`, so a limited request never reaches the
    provider (no cost incurred) and never opens a stream that would then
    have to be aborted mid-flight.
    """

    await enforce_rate_limit(
        rate_limiter,
        scope="chat",
        owner_id=owner_id,
        limit=settings.chat_rate_limit_requests,
        window_seconds=settings.chat_rate_limit_window_seconds,
    )


def _message_response(message: Message) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        role=message.role.value,
        content=message.content,
        provider=message.provider,
        model=message.model,
        created_at=message.created_at,
    )


def _format_transcript(
    history: list[BaseMessage],
    user_prompt: str,
    compacted_summary: str | None = None,
) -> str:
    """
    Folds prior turns into a plain-text transcript prefix for
    `user_prompt`.

    `BaseGenerationProvider.build_messages` only builds a single
    system+user message pair today (no multi-message array), so there is
    no native way to pass a langchain message history straight to a
    provider yet -- this is a deliberate scope limitation, not a silent
    workaround. Multi-turn history is folded into `user_prompt` as text
    until providers support a message array.
    """

    if not history and not compacted_summary:
        return user_prompt

    lines: list[str] = []
    if compacted_summary:
        lines.extend(
            [
                "Earlier conversation summary "
                "(preserve these facts unless the user corrects them):",
                compacted_summary,
            ]
        )
    lines.extend(
        [
            f"{'User' if isinstance(message, HumanMessage) else 'Assistant'}: {message.content}"
            for message in history
        ]
    )

    lines.append(f"User: {user_prompt}")

    return "\n".join(lines)


_PAPER_SEARCH_CONTEXT_MESSAGE_LIMIT = 6


def _format_recent_context(
    history: list[BaseMessage],
    compacted_summary: str | None = None,
) -> str | None:
    """Short recent-turns text for collaborators that only need enough
    context to resolve a follow-up's anaphora (e.g. "this field", "those
    papers") -- distinct from `_format_transcript`, which folds the *full*
    prompt history plus the current turn into the generation prompt itself.
    `None` when there's nothing to add, so callers can treat it as "no
    context available" rather than an empty string."""

    if not history and not compacted_summary:
        return None

    lines: list[str] = []
    if compacted_summary:
        lines.append(f"Earlier conversation summary: {compacted_summary}")
    lines.extend(
        f"{'User' if isinstance(message, HumanMessage) else 'Assistant'}: {message.content}"
        for message in history[-_PAPER_SEARCH_CONTEXT_MESSAGE_LIMIT:]
    )
    return "\n".join(lines) if lines else None


async def _retrieve_memory_context(
    *,
    memory_service: MemoryService | None,
    owner_id: UUID,
    conversation_id: UUID,
    query: str,
    transcript: str | None = None,
) -> str | None:
    """
    Memory retrieval, ahead of generation (Runtime Memory Injection
    Pipeline -- mirrors `ResearchService._retrieve_memory_context`).
    `conversation_id` doubles as the session id: unlike research's
    freshly-minted-per-call id, a conversation already persists across
    turns via `ConversationService.get_or_create()`, so it's the
    natural session boundary for chat. Best-effort: a memory outage
    must never block a chat turn.
    """

    if memory_service is None:
        return None

    try:
        context = await memory_service.get_context(
            owner_id=owner_id,
            session_id=conversation_id,
            semantic_query=query,
            top_k=5,
            transcript=transcript,
        )
    except Exception as exc:
        logger.warning(
            "memory.chat.retrieval_failed",
            conversation_id=str(conversation_id),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return None

    return format_memory_context(context)


async def _extract_and_store_memory(
    *,
    memory_service: MemoryService | None,
    memory_extraction_service: MemoryExtractionService | None,
    session_state_updater: SessionStateUpdaterService | None,
    owner_id: UUID,
    conversation_id: UUID,
    user_prompt: str,
    assistant_content: str,
    user_message_id: UUID | None = None,
    assistant_message_id: UUID | None = None,
) -> None:
    """
    Post-generation half of the Runtime Memory Injection Pipeline
    (mirrors `ResearchService._extract_and_store_memory`): the raw turn
    is always captured as SESSION memory; durable USER/RESEARCH facts
    are additionally proposed by `MemoryExtractionService` and stored
    when above the importance threshold. Best-effort throughout.
    """

    if memory_service is None:
        return

    try:
        turn_id = str(assistant_message_id) if assistant_message_id else f"chat:{conversation_id}"
        if settings.memory_session_raw_turn_storage_enabled:
            await memory_service.remember(
                owner_id=owner_id,
                type=MemoryType.SESSION,
                content=f"Q: {user_prompt}\nA: {assistant_content}",
                session_id=conversation_id,
                metadata={
                    "kind": "raw_turn",
                    "source_turn_id": turn_id,
                    **({"source_user_message_id": str(user_message_id)} if user_message_id else {}),
                    **(
                        {"source_assistant_message_id": str(assistant_message_id)}
                        if assistant_message_id
                        else {}
                    ),
                },
            )
        elif settings.memory_session_state_storage_enabled and session_state_updater is not None:
            await distill_and_upsert_session_state(
                memory_service=memory_service,
                session_state_updater=session_state_updater,
                owner_id=owner_id,
                session_id=conversation_id,
                user_message=user_prompt,
                assistant_message=assistant_content,
                turn_id=turn_id,
            )
    except Exception as exc:
        logger.warning(
            "memory.chat.session_remember_failed",
            conversation_id=str(conversation_id),
            error_type=type(exc).__name__,
            error=str(exc),
        )

    if memory_extraction_service is None:
        return

    try:
        await MemoryExtractionOrchestrator(
            memory_service,
            memory_extraction_service,
            create_memory_availability_client(),
            get_memory_metrics(),
        ).process_turn(
            MemoryTurnEvent(
                owner_id=owner_id,
                session_id=conversation_id,
                conversation_id=conversation_id,
                runtime="chat",
                user_message=user_prompt,
                assistant_message=assistant_content,
                turn_id=turn_id,
            )
        )
    except Exception as exc:
        logger.warning(
            "memory.chat.extraction_orchestration_failed",
            conversation_id=str(conversation_id),
            error_type=type(exc).__name__,
            error=str(exc),
        )


def _with_web_search_context(
    prompt_context: PromptContext,
    web_context_text: str | None,
) -> PromptContext:
    """Appends (not prepends, unlike `with_memory_context`) web-search
    findings after whatever's already in `context` -- background/memory
    first, freshest evidence closest to the question."""

    if not web_context_text:
        return prompt_context

    return prompt_context.model_copy(
        update={
            "context": f"{prompt_context.context}\n\n{web_context_text}".strip(),
        },
    )


def _with_paper_search_context(
    prompt_context: PromptContext,
    paper_context_text: str | None,
) -> PromptContext:
    """Appends after web-search context (if any) -- memory, then web,
    then papers, freshest/most-specific evidence closest to the question."""

    if not paper_context_text:
        return prompt_context

    return prompt_context.model_copy(
        update={
            "context": f"{prompt_context.context}\n\n{paper_context_text}".strip(),
        },
    )


async def _build_request(
    *,
    payload: ChatStreamRequest,
    conversation: Conversation,
    owner_id: UUID,
    memory_service: MemoryService | None,
    prompt_history: PromptHistory,
    web_context_text: str | None = None,
    paper_context_text: str | None = None,
    web_invoked: bool = False,
    paper_invoked: bool = False,
) -> GenerationRequest:
    history = prompt_history.messages
    transcript = _format_transcript(
        history,
        payload.user_prompt,
        prompt_history.summary,
    )

    memory_context_text = await _retrieve_memory_context(
        memory_service=memory_service,
        owner_id=owner_id,
        conversation_id=conversation.id,
        query=payload.user_prompt,
        transcript=transcript,
    )

    prompt_context = with_memory_context(
        PromptContext(context="", chunks=[]),
        memory_context_text,
    )
    prompt_context = _with_web_search_context(prompt_context, web_context_text)
    prompt_context = _with_paper_search_context(prompt_context, paper_context_text)

    # E23 (EVALUATION_PLAN.md §10): recorded only when the toggle was on
    # for this turn -- "invoked" is only a meaningful question once the
    # tool was eligible. `OnlineScoringJob` reads these back off the
    # persisted `GenerationArtifact.request.metadata` and emits
    # `eval_scores` rows for them (same "free, 100%-sampled deterministic
    # signal" path `citation_validity` already uses), which
    # `_sync_to_langsmith` mirrors to LangSmith automatically -- no new
    # wiring needed in either place.
    tool_invocation_metadata: dict[str, Any] = {}
    if payload.web_search_enabled:
        tool_invocation_metadata["web_search_invoked"] = web_invoked
        if web_invoked:
            tool_invocation_metadata["web_search_success"] = web_context_text is not None
    if payload.paper_search_enabled:
        tool_invocation_metadata["paper_search_invoked"] = paper_invoked
        if paper_invoked:
            tool_invocation_metadata["paper_search_success"] = paper_context_text is not None

    return GenerationRequest(
        prompt_context=prompt_context,
        user_prompt=transcript,
        stream=True,
        owner_id=owner_id,
        conversation_id=conversation.id,
        # Mirrors ResearchService: populates StreamEvent.session_id on every
        # emitted event so a client that started a new conversation (no
        # `payload.conversation_id`) can learn the server-assigned id from
        # the stream itself, the same way `use-research.ts` learns
        # `research_id` from the first event.
        session_id=conversation.id,
        routing_strategy=payload.routing_strategy,
        cache_runtime=CacheRuntime.CHAT,
        runtime=RuntimeType.CHAT,
        artifact_runtime=ArtifactRuntime.CHAT,
        metadata=tool_invocation_metadata,
        **config_fingerprint_kwargs(surface="chat", prompt_version="chat-v1"),
    )


async def _prepare_chat_generation(
    *,
    payload: ChatStreamRequest,
    conversation_service: ConversationService,
    conversation: Conversation,
    owner_id: UUID,
    memory_service: MemoryService | None,
    web_search: WebSearchService | None,
    web_search_necessity: WebSearchNecessityService | None,
    paper_search: PaperSearchService | None,
    paper_query_extraction: PaperQueryExtractionService | None,
) -> tuple[list[StreamEvent], GenerationRequest]:
    """Runs the toggle-gated web search and paper search steps (if any)
    before building the `GenerationRequest`, so evidence -- when found --
    is already part of the prompt context the very first token is
    generated against. Returns each step's own status events (empty when
    the toggle is off, unconfigured, or nothing was found) to be yielded
    ahead of the real generation stream.

    History is loaded once, here, up front -- both so `run_chat_paper_search`
    can resolve a follow-up's anaphora ("this field", "those papers")
    against recent turns (2026-07-26 fix: it previously only ever saw the
    single latest message), and so `_build_request` doesn't redundantly
    reload/re-compact the same history a second time."""

    await conversation_service.compact_history_if_needed(
        conversation=conversation,
        recent_message_limit=settings.chat_prompt_recent_message_limit,
        summary_max_characters=settings.chat_prompt_summary_max_characters,
    )
    prompt_history = await conversation_service.load_prompt_history(
        conversation=conversation,
        recent_message_limit=settings.chat_prompt_recent_message_limit,
    )
    recent_context = _format_recent_context(prompt_history.messages, prompt_history.summary)

    web_outcome = await run_chat_web_search(
        enabled=payload.web_search_enabled,
        user_prompt=payload.user_prompt,
        owner_id=owner_id,
        conversation_id=conversation.id,
        session_id=conversation.id,
        web_search=web_search,
        web_search_necessity=web_search_necessity,
    )
    paper_outcome = await run_chat_paper_search(
        enabled=payload.paper_search_enabled,
        user_prompt=payload.user_prompt,
        owner_id=owner_id,
        session_id=conversation.id,
        paper_search=paper_search,
        query_extraction=paper_query_extraction,
        conversation_context=recent_context,
    )
    request = await _build_request(
        payload=payload,
        conversation=conversation,
        owner_id=owner_id,
        memory_service=memory_service,
        prompt_history=prompt_history,
        web_context_text=web_outcome.context_text,
        paper_context_text=paper_outcome.context_text,
        web_invoked=web_outcome.invoked,
        paper_invoked=paper_outcome.invoked,
    )
    return [*web_outcome.events, *paper_outcome.events], request


async def _persist_conversation_identity(
    *,
    conversation_artifact_writer: ConversationArtifactWriter,
    conversation_id: UUID,
    owner_id: UUID,
    title: str | None,
    created_at: datetime,
) -> None:
    """
    Best-effort (Artifact Platform PRD §24): writes `conversation.json`.
    `ConversationArtifactWriter.write_identity()` itself no-ops once the
    key already exists, so this is safe to call on every request rather
    than only on first creation.
    """

    try:
        await conversation_artifact_writer.write_identity(
            ConversationIdentity(
                conversation_id=conversation_id,
                owner_id=owner_id,
                title=title,
                created_at=created_at,
            ),
        )
    except Exception as exc:
        logger.warning(
            "artifacts.conversation.identity_failed",
            conversation_id=str(conversation_id),
            reason="artifact_persistence_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )


async def _generate_and_store_title(
    *,
    generation_service: GenerationService,
    conversation_service: ConversationService,
    conversation_id: UUID,
    owner_id: UUID,
) -> None:
    """Best-effort, Groq-only one-time title generation from the first question."""

    token = await conversation_service.claim_title_generation(
        conversation_id=conversation_id,
    )
    if token is None:
        return

    try:
        first_question = await conversation_service.get_first_user_prompt(
            conversation_id=conversation_id,
        )
        if not first_question:
            await conversation_service.release_title_generation(
                conversation_id=conversation_id,
                token=token,
            )
            return

        result = await generation_service.generate(
            provider=GenerationProvider.GROQ,
            request=GenerationRequest(
                prompt_context=PromptContext(context="", chunks=[]),
                system_prompt=(
                    "Write a concise title of at most eight words for the user's "
                    "question below. Use only the question's explicit subject; do "
                    "not infer a different subject or expand acronyms. Return only "
                    "the title, with no quotation marks or ending punctuation."
                ),
                user_prompt=f"First user question: {first_question}",
                owner_id=owner_id,
                conversation_id=conversation_id,
                max_tokens=24,
                temperature=0,
                cache_policy=CachePolicy.NEVER,
                metadata={"usage_category": "conversation_title"},
                artifact_runtime=ArtifactRuntime.CHAT,
            ),
        )
        title = " ".join(result.content.strip().strip('"').split())[:255]
        if title:
            await conversation_service.complete_title_generation(
                conversation_id=conversation_id,
                token=token,
                title=title,
            )
        else:
            await conversation_service.release_title_generation(
                conversation_id=conversation_id,
                token=token,
            )
    except Exception as exc:
        await conversation_service.release_title_generation(
            conversation_id=conversation_id,
            token=token,
        )
        logger.warning(
            "chat.title_generation_failed",
            conversation_id=str(conversation_id),
            error_type=type(exc).__name__,
            error=str(exc),
        )


async def _chain_events(
    prefix: list[StreamEvent],
    events: AsyncGenerator[StreamEvent, None],
) -> AsyncGenerator[StreamEvent, None]:
    """Yields the web-search step's own status events (if any) before the
    real generation stream -- these carry no TOKEN content, so
    `_persist_on_complete` (wrapped around this generator's output) passes
    them through untouched, same as it already does for START/etc."""

    for event in prefix:
        yield event

    async for event in events:
        yield event


async def _persist_on_complete(
    *,
    events: AsyncGenerator[StreamEvent, None],
    conversation_service: ConversationService,
    conversation_id: UUID,
    owner_id: UUID,
    user_prompt: str,
    provider: GenerationProvider | None,
    conversation_artifact_writer: ConversationArtifactWriter | None,
    artifact_policy_service: ArtifactPolicyService | None,
    generation_service: GenerationService | None = None,
    memory_service: MemoryService | None = None,
    memory_extraction_service: MemoryExtractionService | None = None,
    session_state_updater: SessionStateUpdaterService | None = None,
) -> AsyncGenerator[StreamEvent, None]:
    """
    Forwards every event untouched, accumulating TOKEN content along the
    way, and persists the completed turn once the stream reaches
    COMPLETE. Persistence lives here at the route/consumer level rather
    than inside StreamingService, keeping the Generation Streaming
    Platform itself conversation-agnostic (per ADR-028's actual scope --
    Conversation Runtime is listed there as future work). The Artifact
    Platform's immutable turn snapshot is written the same way,
    best-effort, right after the Postgres-backed turn is committed.
    """

    content_parts: list[str] = []

    async for event in events:
        if event.type == CoreEventType.TOKEN.value and event.content:
            content_parts.append(event.content)

        yield event

        if event.type in _COMPLETION_EVENT_TYPES:
            assistant_content = "".join(content_parts)

            persisted_turn = await conversation_service.append_turn(
                conversation_id=conversation_id,
                user_prompt=user_prompt,
                assistant_content=assistant_content,
                provider=provider.value if provider else None,
            )

            await _extract_and_store_memory(
                memory_service=memory_service,
                memory_extraction_service=memory_extraction_service,
                session_state_updater=session_state_updater,
                owner_id=owner_id,
                conversation_id=conversation_id,
                user_prompt=user_prompt,
                assistant_content=assistant_content,
                user_message_id=(
                    persisted_turn.user_message_id if persisted_turn is not None else None
                ),
                assistant_message_id=(
                    persisted_turn.assistant_message_id if persisted_turn is not None else None
                ),
            )

            if generation_service is not None:
                await _generate_and_store_title(
                    generation_service=generation_service,
                    conversation_service=conversation_service,
                    conversation_id=conversation_id,
                    owner_id=owner_id,
                )

            if conversation_artifact_writer is None:
                continue

            artifact_runtime = ArtifactRuntime.CHAT

            if artifact_policy_service is not None and not (
                artifact_policy_service.should_persist(
                    artifact_runtime,
                    ArtifactCategory.CONVERSATION,
                )
            ):
                continue

            try:
                turn = ConversationTurnArtifactBuilder().build(
                    conversation_id=conversation_id,
                    owner_id=owner_id,
                    user_prompt=user_prompt,
                    assistant_content=assistant_content,
                    provider=provider.value if provider else None,
                )

                await conversation_artifact_writer.write_turn(turn)
            except Exception as exc:
                logger.warning(
                    "artifacts.conversation.turn_failed",
                    conversation_id=str(conversation_id),
                    reason="artifact_persistence_failed",
                    error_type=type(exc).__name__,
                    error=str(exc),
                )


@router.get(
    "/conversations",
    response_model=ChatConversationListResponse,
    summary="List this user's chat conversations, most recently updated first",
)
async def list_chat_conversations(
    cursor: UUID | None = None,
    limit: int = Query(
        default=settings.chat_history_page_size, ge=1, le=settings.chat_history_page_max_size
    ),
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ChatConversationListResponse:
    page = await conversation_service.list_page_for_owner(
        owner_id=current_user.id,
        before_conversation_id=cursor,
        limit=limit,
    )
    return ChatConversationListResponse(
        conversations=[
            ChatConversationSummary(
                conversation_id=conversation.id,
                title=conversation.title,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
            )
            for conversation in page.conversations
        ],
        next_cursor=page.next_cursor,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ChatConversationResponse,
    summary="Replay every message in a chat conversation, oldest first",
)
async def get_chat_conversation(
    conversation_id: UUID,
    cursor: UUID | None = None,
    limit: int = Query(
        default=settings.chat_history_page_size, ge=1, le=settings.chat_history_page_max_size
    ),
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ChatConversationResponse:
    conversation = await conversation_service.get_or_create(
        conversation_id=conversation_id,
        owner_id=current_user.id,
    )
    page = await conversation_service.list_messages_page(
        conversation_id=conversation.id,
        before_message_id=cursor,
        limit=limit,
    )
    return ChatConversationResponse(
        conversation_id=conversation.id,
        title=conversation.title,
        messages=[_message_response(message) for message in page.messages],
        next_cursor=page.next_cursor,
    )


@router.post(
    "/stream",
    summary="Stream a chat completion over Server-Sent Events",
)
async def stream_chat(
    payload: ChatStreamRequest,
    current_user: User = Depends(get_current_user),
    streaming_service: StreamingService = Depends(get_streaming_service),
    generation_service: GenerationService = Depends(get_generation_service),
    conversation_service: ConversationService = Depends(get_conversation_service),
    conversation_artifact_writer: ConversationArtifactWriter = Depends(
        get_conversation_artifact_writer
    ),
    artifact_policy_service: ArtifactPolicyService = Depends(
        get_artifact_policy_service_dependency
    ),
    memory_service: MemoryService = Depends(get_memory_service),
    memory_extraction_service: MemoryExtractionService = Depends(get_memory_extraction_service),
    session_state_updater: SessionStateUpdaterService = Depends(get_session_state_updater_service),
    rate_limiter: ValkeyRateLimiter = Depends(get_rate_limiter),
    web_search: WebSearchService = Depends(get_web_search_service),
    web_search_necessity: WebSearchNecessityService = Depends(get_web_search_necessity_service),
    paper_search: PaperSearchService = Depends(get_paper_search_service),
    paper_query_extraction: PaperQueryExtractionService = Depends(
        get_paper_query_extraction_service
    ),
) -> StreamingResponse:
    """
    A `POST` consumed via `fetch` + `ReadableStream` on the frontend, not
    a bare `EventSource` -- the browser `EventSource` API can't attach a
    custom `Authorization` header, and this platform's auth is Bearer
    `id_token`. See ADR-028's "Production Considerations".
    """

    await _check_chat_rate_limit(rate_limiter=rate_limiter, owner_id=current_user.id)

    conversation = await conversation_service.get_or_create(
        conversation_id=payload.conversation_id,
        owner_id=current_user.id,
    )

    await _persist_conversation_identity(
        conversation_artifact_writer=conversation_artifact_writer,
        conversation_id=conversation.id,
        owner_id=conversation.owner_id,
        title=conversation.title,
        created_at=conversation.created_at,
    )

    tool_events, request = await _prepare_chat_generation(
        payload=payload,
        conversation_service=conversation_service,
        conversation=conversation,
        owner_id=current_user.id,
        memory_service=memory_service,
        web_search=web_search,
        web_search_necessity=web_search_necessity,
        paper_search=paper_search,
        paper_query_extraction=paper_query_extraction,
    )

    events = _chain_events(
        tool_events,
        streaming_service.stream_generate(
            request=request,
            provider=payload.provider,
        ),
    )

    return sse_stream_response(
        _persist_on_complete(
            events=events,
            conversation_service=conversation_service,
            conversation_id=conversation.id,
            owner_id=current_user.id,
            user_prompt=payload.user_prompt,
            provider=payload.provider,
            conversation_artifact_writer=conversation_artifact_writer,
            artifact_policy_service=artifact_policy_service,
            generation_service=generation_service,
            memory_service=memory_service,
            memory_extraction_service=memory_extraction_service,
            session_state_updater=session_state_updater,
        )
    )


@router.websocket("/ws")
async def stream_chat_ws(
    websocket: WebSocket,
    token: str,
) -> None:
    """
    Bidirectional alternative to `/chat/stream` (ADR-028 "WebSocket
    (Optional)"). A browser's WebSocket handshake can't set a custom
    `Authorization` header either, so auth here comes from a `?token=`
    query parameter, verified through the same `authenticate_token` flow
    `get_current_user` uses for HTTP requests.

    Protocol: connect, then send one JSON text frame matching
    `ChatStreamRequest`; the server streams `StreamEvent` JSON frames back
    until COMPLETE/ERROR, then closes.
    """

    await websocket.accept()

    async with SessionFactory() as session:
        try:
            current_user = await authenticate_token(token, session)
        except AppException as exc:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=exc.message,
            )
            return

        try:
            await _check_chat_rate_limit(rate_limiter=get_rate_limiter(), owner_id=current_user.id)
        except RateLimitExceededException as exc:
            await websocket.close(
                code=status.WS_1013_TRY_AGAIN_LATER,
                reason=exc.message,
            )
            return

        raw_payload = await websocket.receive_text()

        try:
            payload = ChatStreamRequest.model_validate_json(raw_payload)
        except ValidationError as exc:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=str(exc),
            )
            return

        conversation_service = ConversationService(session)
        streaming_service = get_streaming_service()
        generation_service = get_generation_service()
        conversation_artifact_writer = get_conversation_artifact_writer()
        artifact_policy_service = get_artifact_policy_service_dependency()
        # `build_memory_service`/`build_memory_extraction_service`, not the
        # `Depends`-based `get_memory_service`/`get_memory_extraction_service`
        # -- this route manages its own `session` outside FastAPI's
        # dependency graph (mirrors `ConversationService(session)` above).
        memory_service = build_memory_service(session)
        memory_extraction_service = build_memory_extraction_service()
        session_state_updater = build_session_state_updater_service()
        # Same stateless-composition-function pattern as `get_streaming_service()`
        # above -- called directly, not through FastAPI `Depends`, since this
        # route manages its own object graph outside the dependency graph.
        web_search = create_web_search_service()
        web_search_necessity = create_web_search_necessity_service()
        paper_search = create_paper_search_service()
        paper_query_extraction = create_paper_query_extraction_service()

        conversation = await conversation_service.get_or_create(
            conversation_id=payload.conversation_id,
            owner_id=current_user.id,
        )

        await _persist_conversation_identity(
            conversation_artifact_writer=conversation_artifact_writer,
            conversation_id=conversation.id,
            owner_id=conversation.owner_id,
            title=conversation.title,
            created_at=conversation.created_at,
        )

        tool_events, request = await _prepare_chat_generation(
            payload=payload,
            conversation_service=conversation_service,
            conversation=conversation,
            owner_id=current_user.id,
            memory_service=memory_service,
            web_search=web_search,
            web_search_necessity=web_search_necessity,
            paper_search=paper_search,
            paper_query_extraction=paper_query_extraction,
        )

        events = _chain_events(
            tool_events,
            streaming_service.stream_generate(
                request=request,
                provider=payload.provider,
            ),
        )

        try:
            await run_websocket_stream(
                websocket,
                _persist_on_complete(
                    events=events,
                    conversation_service=conversation_service,
                    conversation_id=conversation.id,
                    owner_id=current_user.id,
                    user_prompt=payload.user_prompt,
                    provider=payload.provider,
                    conversation_artifact_writer=conversation_artifact_writer,
                    artifact_policy_service=artifact_policy_service,
                    generation_service=generation_service,
                    memory_service=memory_service,
                    memory_extraction_service=memory_extraction_service,
                    session_state_updater=session_state_updater,
                ),
            )
        finally:
            await websocket.close()
