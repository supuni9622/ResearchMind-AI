from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.ai.research.service import ResearchService
from app.ai.runtime.generation.streaming.transports.sse import sse_stream_response
from app.auth.dependencies import get_current_user
from app.dependencies.research import get_research_repository, get_research_service
from app.exceptions.base import NotFoundException
from app.models.user import User
from app.repositories.research import ResearchRepository
from app.schemas.research import (
    ResearchCitationsRequest,
    ResearchCitationsResponse,
    ResearchRequest,
    ResearchResponse,
    ResearchSessionResponse,
    ResearchStreamRequest,
)

router = APIRouter(
    prefix="/research",
    tags=["Research"],
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
    )

    return ResearchResponse(
        research_id=outcome.research_id,
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
    )

    return sse_stream_response(events)


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

    return ResearchSessionResponse(
        research_id=research_session.id,
        query=research_session.query,
        answer=research_session.answer,
        citations=research_session.citations,
        sources=research_session.sources,
        created_at=research_session.created_at,
    )
