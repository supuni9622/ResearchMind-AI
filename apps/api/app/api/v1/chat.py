from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime
from uuid import UUID

import structlog
from fastapi import (
    APIRouter,
    Depends,
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
from app.ai.runtime.events.enums import CoreEventType
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.streaming.service import StreamingService
from app.ai.runtime.generation.streaming.transports.sse import sse_stream_response
from app.ai.runtime.generation.streaming.transports.websocket import run_websocket_stream
from app.auth.dependencies import authenticate_token, get_current_user
from app.db.session import SessionFactory
from app.dependencies.generation import (
    get_artifact_policy_service_dependency,
    get_conversation_artifact_writer,
    get_conversation_service,
    get_streaming_service,
)
from app.exceptions.base import AppException
from app.models.user import User
from app.schemas.chat import ChatStreamRequest
from app.services.conversation import ConversationService

logger = structlog.get_logger()

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


def _format_transcript(
    history: list[BaseMessage],
    user_prompt: str,
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

    if not history:
        return user_prompt

    lines = [
        f"{'User' if isinstance(message, HumanMessage) else 'Assistant'}: {message.content}"
        for message in history
    ]

    lines.append(f"User: {user_prompt}")

    return "\n".join(lines)


async def _build_request(
    *,
    payload: ChatStreamRequest,
    conversation_service: ConversationService,
    conversation_id: UUID,
) -> GenerationRequest:

    history = await conversation_service.load_history(
        conversation_id=conversation_id,
    )

    return GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt=_format_transcript(history, payload.user_prompt),
        stream=True,
        conversation_id=conversation_id,
        routing_strategy=payload.routing_strategy,
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

        if event.type == CoreEventType.COMPLETE.value:
            assistant_content = "".join(content_parts)

            await conversation_service.append_turn(
                conversation_id=conversation_id,
                user_prompt=user_prompt,
                assistant_content=assistant_content,
                provider=provider.value if provider else None,
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


@router.post(
    "/stream",
    summary="Stream a chat completion over Server-Sent Events",
)
async def stream_chat(
    payload: ChatStreamRequest,
    current_user: User = Depends(get_current_user),
    streaming_service: StreamingService = Depends(get_streaming_service),
    conversation_service: ConversationService = Depends(get_conversation_service),
    conversation_artifact_writer: ConversationArtifactWriter = Depends(
        get_conversation_artifact_writer
    ),
    artifact_policy_service: ArtifactPolicyService = Depends(
        get_artifact_policy_service_dependency
    ),
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
        conversation_id=conversation.id,
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
        conversation_artifact_writer = get_conversation_artifact_writer()
        artifact_policy_service = get_artifact_policy_service_dependency()

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
            conversation_id=conversation.id,
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
                ),
            )
        finally:
            await websocket.close()
