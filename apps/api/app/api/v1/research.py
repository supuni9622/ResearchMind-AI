from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.ai.research.service import ResearchService
from app.ai.runtime.generation.streaming.transports.sse import sse_stream_response
from app.auth.dependencies import get_current_user
from app.dependencies.research import (
    get_research_conversation_service,
    get_research_repository,
    get_research_service,
)
from app.exceptions.base import NotFoundException
from app.models.research import ResearchSession
from app.models.user import User
from app.repositories.research import ResearchRepository
from app.schemas.research import (
    ResearchCitationsRequest,
    ResearchCitationsResponse,
    ResearchConversationListResponse,
    ResearchConversationResponse,
    ResearchConversationSummary,
    ResearchRequest,
    ResearchResponse,
    ResearchSessionResponse,
    ResearchStreamRequest,
)
from app.services.research_conversation import ResearchConversationService

router = APIRouter(
    prefix="/research",
    tags=["Research"],
)


def _session_response(research_session: ResearchSession) -> ResearchSessionResponse:
    return ResearchSessionResponse(
        research_id=research_session.id,
        conversation_id=research_session.conversation_id,
        query=research_session.query,
        answer=research_session.answer,
        citations=research_session.citations,
        sources=research_session.sources,
        created_at=research_session.created_at,
    )


@router.post(
    "",
    response_model=ResearchResponse,
    summary="Ask a research question and receive a grounded, cited answer",
)
async def create_research(
    payload: ResearchRequest,
    current_user: User = Depends(get_current_user),
    research_service: ResearchService = Depends(get_research_service),
) -> ResearchResponse:
    outcome = await research_service.research(
        query=payload.query,
        top_k=payload.top_k,
        filters=payload.filters,
        owner_id=current_user.id,
        provider=payload.provider,
        routing_strategy=payload.routing_strategy,
        conversation_id=payload.conversation_id,
    )

    return ResearchResponse(
        research_id=outcome.research_id,
        conversation_id=outcome.conversation_id,
        query=outcome.query,
        answer=outcome.answer,
        citations=outcome.citations,
        sources=outcome.sources,
        duration_ms=outcome.duration_ms,
    )


@router.post(
    "/stream",
    summary="Stream a research answer over Server-Sent Events",
)
async def stream_research(
    payload: ResearchStreamRequest,
    current_user: User = Depends(get_current_user),
    research_service: ResearchService = Depends(get_research_service),
) -> StreamingResponse:
    events = research_service.stream_research(
        query=payload.query,
        top_k=payload.top_k,
        filters=payload.filters,
        owner_id=current_user.id,
        provider=payload.provider,
        routing_strategy=payload.routing_strategy,
        conversation_id=payload.conversation_id,
    )

    return sse_stream_response(events)


@router.get(
    "/conversations",
    response_model=ResearchConversationListResponse,
    summary="List this user's research conversations, most recently updated first",
)
async def list_research_conversations(
    current_user: User = Depends(get_current_user),
    repository: ResearchRepository = Depends(get_research_repository),
) -> ResearchConversationListResponse:
    conversations = await repository.list_conversations_for_owner(owner_id=current_user.id)

    return ResearchConversationListResponse(
        conversations=[
            ResearchConversationSummary(
                conversation_id=conversation.id,
                title=conversation.title,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
            )
            for conversation in conversations
        ],
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ResearchConversationResponse,
    summary="Replay every turn of a research conversation, oldest first",
)
async def get_research_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    repository: ResearchRepository = Depends(get_research_repository),
    conversation_service: ResearchConversationService = Depends(get_research_conversation_service),
) -> ResearchConversationResponse:
    conversation = await conversation_service.get_or_create(
        conversation_id=conversation_id,
        owner_id=current_user.id,
    )

    sessions = await repository.list_sessions_for_conversation(
        conversation_id=conversation.id,
        owner_id=current_user.id,
    )

    return ResearchConversationResponse(
        conversation_id=conversation.id,
        title=conversation.title,
        turns=[_session_response(session) for session in sessions],
    )


@router.post(
    "/citations",
    response_model=ResearchCitationsResponse,
    summary="Preview citations for a query without generating an answer",
)
async def research_citations(
    payload: ResearchCitationsRequest,
    current_user: User = Depends(get_current_user),
    research_service: ResearchService = Depends(get_research_service),
) -> ResearchCitationsResponse:
    citations = await research_service.citations_only(
        query=payload.query,
        top_k=payload.top_k,
        filters=payload.filters,
        owner_id=current_user.id,
    )

    return ResearchCitationsResponse(citations=citations)


@router.get(
    "/{research_id}",
    response_model=ResearchSessionResponse,
    summary="Replay a previous research session",
)
async def get_research(
    research_id: UUID,
    current_user: User = Depends(get_current_user),
    repository: ResearchRepository = Depends(get_research_repository),
) -> ResearchSessionResponse:
    research_session = await repository.get_by_id_for_owner(
        research_id=research_id,
        owner_id=current_user.id,
    )

    if research_session is None:
        raise NotFoundException(
            message=f"Research session '{research_id}' was not found.",
        )

    return _session_response(research_session)
