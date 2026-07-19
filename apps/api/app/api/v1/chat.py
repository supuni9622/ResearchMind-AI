from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime
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
    create_memory_availability_client,
    get_memory_metrics,
)
from app.ai.memory.enums import MemoryType
from app.ai.memory.extraction.orchestrator import MemoryExtractionOrchestrator
from app.ai.memory.extraction.service import MemoryExtractionService
from app.ai.memory.policy.models import MemoryTurnEvent
from app.ai.memory.services.formatting import format_memory_context, with_memory_context
from app.ai.memory.services.memory_service import MemoryService
from app.ai.memory.session.state import state_from_user_turn
from app.ai.runtime.events.enums import CoreEventType
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.generation.caching.enums import CachePolicy, CacheRuntime
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import GenerationRequest, StreamEventType
from app.ai.runtime.generation.service import GenerationService
from app.ai.runtime.generation.streaming.service import StreamingService
from app.ai.runtime.generation.streaming.transports.sse import sse_stream_response
from app.ai.runtime.generation.streaming.transports.websocket import run_websocket_stream
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType
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
from app.dependencies.memory import get_memory_extraction_service, get_memory_service
from app.exceptions.base import AppException
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.schemas.chat import (
    ChatConversationListResponse,
    ChatConversationResponse,
    ChatConversationSummary,
    ChatMessageResponse,
    ChatStreamRequest,
)
from app.services.conversation import ConversationService

logger = structlog.get_logger()

_COMPLETION_EVENT_TYPES = {
    CoreEventType.COMPLETE.value,
    StreamEventType.COMPLETED.value,
}

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
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
        elif settings.memory_session_state_storage_enabled:
            state = state_from_user_turn(
                user_message=user_prompt,
                source_turn_id=turn_id,
                source_user_message_id=user_message_id,
                source_assistant_message_id=assistant_message_id,
            )
            if state is not None:
                await memory_service.remember(
                    owner_id=owner_id,
                    type=MemoryType.SESSION,
                    content=state.content,
                    session_id=conversation_id,
                    metadata=state.metadata(),
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


async def _build_request(
    *,
    payload: ChatStreamRequest,
    conversation_service: ConversationService,
    conversation: Conversation,
    owner_id: UUID,
    memory_service: MemoryService | None,
) -> GenerationRequest:
    await conversation_service.compact_history_if_needed(
        conversation=conversation,
        recent_message_limit=settings.chat_prompt_recent_message_limit,
        summary_max_characters=settings.chat_prompt_summary_max_characters,
    )
    prompt_history = await conversation_service.load_prompt_history(
        conversation=conversation,
        recent_message_limit=settings.chat_prompt_recent_message_limit,
    )
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

    return GenerationRequest(
        prompt_context=with_memory_context(
            PromptContext(context="", chunks=[]),
            memory_context_text,
        ),
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
    )


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
) -> StreamingResponse:
    """
    A `POST` consumed via `fetch` + `ReadableStream` on the frontend, not
    a bare `EventSource` -- the browser `EventSource` API can't attach a
    custom `Authorization` header, and this platform's auth is Bearer
    `id_token`. See ADR-028's "Production Considerations".
    """

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

    request = await _build_request(
        payload=payload,
        conversation_service=conversation_service,
        conversation=conversation,
        owner_id=current_user.id,
        memory_service=memory_service,
    )

    events = streaming_service.stream_generate(
        request=request,
        provider=payload.provider,
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

        request = await _build_request(
            payload=payload,
            conversation_service=conversation_service,
            conversation=conversation,
            owner_id=current_user.id,
            memory_service=memory_service,
        )

        events = streaming_service.stream_generate(
            request=request,
            provider=payload.provider,
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
                ),
            )
        finally:
            await websocket.close()
