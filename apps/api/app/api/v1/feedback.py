"""Owner-scoped generation feedback endpoint (EVALUATION_PLAN.md §16 phase 3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.dependencies.feedback import get_feedback_service, get_memory_feedback_service
from app.models.user import User
from app.schemas.feedback import (
    FeedbackCreateRequest,
    FeedbackResponse,
    MemoryFeedbackCreateRequest,
    MemoryFeedbackResponse,
)
from app.services.feedback import FeedbackService
from app.services.memory_feedback import MemoryFeedbackService

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit thumbs up/down feedback on a generation",
)
async def submit_feedback(
    payload: FeedbackCreateRequest,
    current_user: User = Depends(get_current_user),
    feedback_service: FeedbackService = Depends(get_feedback_service),
) -> FeedbackResponse:
    """
    Record the authenticated user's rating for a single generation.

    Scoped to `current_user.id` — a user can only rate their own
    generations, never another user's. Resubmitting for the same
    `generation_id` updates the existing rating/comment rather than
    creating a second record (see `Feedback`'s unique constraint).
    """

    feedback = await feedback_service.submit(
        owner_id=current_user.id,
        generation_id=payload.generation_id,
        surface=payload.surface,
        rating=payload.rating,
        comment=payload.comment,
    )

    return FeedbackResponse.model_validate(feedback)


@router.post(
    "/memory",
    response_model=MemoryFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report whether injected memory helped or was wrong",
)
async def submit_memory_feedback(
    payload: MemoryFeedbackCreateRequest,
    current_user: User = Depends(get_current_user),
    feedback_service: MemoryFeedbackService = Depends(get_memory_feedback_service),
) -> MemoryFeedbackResponse:
    feedback = await feedback_service.submit(
        owner_id=current_user.id,
        generation_id=payload.generation_id,
        surface=payload.surface,
        signal=payload.signal,
    )
    return MemoryFeedbackResponse.model_validate(feedback)
