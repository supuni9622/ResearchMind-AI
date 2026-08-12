"""E10's promotion-review queue (EVALUATION_PLAN.md §3/§15's "both
directions" promotion loop).

Same `require_eval_dashboard_access` gate as every other route in
`eval_dashboard.py` -- this is a separate router file (not appended to
that one) purely to keep that file from growing further, not a
different access model.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.observability.providers.langsmith.trace_link import get_trace_url
from app.db.session import get_db
from app.dependencies.eval_dashboard import require_eval_dashboard_access
from app.dependencies.generation_usage import get_generation_usage_repository
from app.dependencies.promotion_review import get_promotion_review_repository
from app.exceptions.base import ValidationException
from app.models.enums import PromotionCandidateView, PromotionDirection, PromotionStatus
from app.models.user import User
from app.repositories.generation_usage import GenerationUsageRepository
from app.repositories.promotion_review import PromotionReviewRepository
from app.schemas.promotion_review import (
    ConfirmPromotionRequest,
    PromotionCandidateListResponse,
    PromotionCandidateResponse,
    PromotionReviewResponse,
    RejectPromotionRequest,
    TraceUrlResponse,
)

router = APIRouter(prefix="/eval-dashboard/promotion-review", tags=["Promotion Review"])


@router.get(
    "/candidates",
    response_model=PromotionCandidateListResponse,
    summary="Unreviewed promotion candidates (E10)",
)
async def list_candidates(
    direction: PromotionCandidateView = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(require_eval_dashboard_access),
    repository: PromotionReviewRepository = Depends(get_promotion_review_repository),
) -> PromotionCandidateListResponse:
    """
    `direction="failure"` merges thumbs-down feedback E11 classified
    `objective` with online-sampled `eval_scores` rows that failed a
    check. `direction="good"` is thumbs-up feedback -- promoting a
    confirmed good example directly into `rag_answer_gold`, not just
    harvesting failures, per E10's own "both directions" framing.
    `direction="preference"` is thumbs-down feedback E11 classified
    `preference` instead -- excluded from the `failure` view by design,
    surfaced separately so a reviewer can override the classifier's
    conservative default instead of it vanishing from the queue for
    good.
    """

    if direction is PromotionCandidateView.GOOD:
        candidates, total = await repository.list_good_candidates(limit=limit, offset=offset)
    elif direction is PromotionCandidateView.PREFERENCE:
        candidates, total = await repository.list_preference_candidates(limit=limit, offset=offset)
    else:
        candidates, total = await repository.list_failure_candidates(limit=limit, offset=offset)

    return PromotionCandidateListResponse(
        items=[
            PromotionCandidateResponse(
                source=candidate.source.value,
                owner_id=candidate.owner_id,
                generation_id=candidate.generation_id,
                reason=candidate.reason,
                created_at=candidate.created_at,
            )
            for candidate in candidates
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/trace-url",
    response_model=TraceUrlResponse,
    summary="LangSmith trace URL for one generation, if available",
)
async def trace_url(
    generation_id: UUID = Query(...),
    _current_user: User = Depends(require_eval_dashboard_access),
    generation_usage_repository: GenerationUsageRepository = Depends(
        get_generation_usage_repository
    ),
) -> TraceUrlResponse:
    """
    Fetched on demand per candidate the reviewer actually opens, not
    eagerly for every row in the list -- each lookup is a real LangSmith
    API call (`read_run` + `get_run_url`), and most listed candidates
    are never clicked into.
    """

    run_id = await generation_usage_repository.get_langsmith_run_id(generation_id)
    if run_id is None:
        return TraceUrlResponse(trace_url=None)
    return TraceUrlResponse(trace_url=get_trace_url(run_id))


@router.post(
    "/reject",
    response_model=PromotionReviewResponse,
    summary="Reject a candidate -- removes it from the queue, no promotion",
)
async def reject(
    payload: RejectPromotionRequest,
    current_user: User = Depends(require_eval_dashboard_access),
    session: AsyncSession = Depends(get_db),
    repository: PromotionReviewRepository = Depends(get_promotion_review_repository),
) -> PromotionReviewResponse:
    review = await repository.create(
        source=payload.source,
        direction=PromotionDirection.FAILURE.value,  # irrelevant for a reject, but non-null
        owner_id=payload.owner_id,
        generation_id=payload.generation_id,
        status=PromotionStatus.REJECTED.value,
        reviewed_by=current_user.id,
    )
    await session.commit()
    return PromotionReviewResponse.model_validate(review)


@router.post(
    "/confirm",
    response_model=PromotionReviewResponse,
    summary="Confirm a candidate -- writes a pending promotion, synced later by a script",
)
async def confirm(
    payload: ConfirmPromotionRequest,
    current_user: User = Depends(require_eval_dashboard_access),
    session: AsyncSession = Depends(get_db),
    repository: PromotionReviewRepository = Depends(get_promotion_review_repository),
) -> PromotionReviewResponse:
    """
    Does not touch `rag_answer_gold.json`/`production_failures.json`
    directly -- writes a `status="confirmed"` row that
    `sync_promoted_examples.py` picks up separately, so a promotion is
    always a git-reviewable diff, never a live API mutation of a
    version-controlled dataset file.
    """

    if payload.direction == "failure" and payload.failure_category is None:
        raise ValidationException(
            message="failure_category is required when direction is 'failure'."
        )
    if payload.direction == "good" and payload.failure_category is not None:
        raise ValidationException(
            message="failure_category must not be set when direction is 'good'."
        )

    review = await repository.create(
        source=payload.source,
        direction=payload.direction,
        owner_id=payload.owner_id,
        generation_id=payload.generation_id,
        status=PromotionStatus.CONFIRMED.value,
        reviewed_by=current_user.id,
        question=payload.question,
        reference_answer=payload.reference_answer,
        contexts=payload.contexts,
        reference_context_ids=payload.reference_context_ids,
        expected_citation_ids=payload.expected_citation_ids,
        query_type=payload.query_type,
        difficulty=payload.difficulty,
        workflow=payload.workflow,
        rubric=payload.rubric,
        failure_category=payload.failure_category,
    )
    await session.commit()
    return PromotionReviewResponse.model_validate(review)
