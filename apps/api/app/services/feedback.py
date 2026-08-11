"""Transaction boundary for submitting generation feedback."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.observability.providers.langsmith.user_feedback import sync_user_feedback
from app.models.enums import EvalScoreSource, FeedbackRating, FeedbackSurface
from app.models.feedback import Feedback
from app.repositories.eval_score import EvalScoreRepository
from app.repositories.feedback import FeedbackRepository
from app.repositories.generation_usage import GenerationUsageRepository

USER_RATING_METRIC = "user_rating"
"""
`eval_scores.metric_name` for a mirrored feedback row (E6,
EVALUATION_PLAN.md §16 phase 7) -- deliberately distinct from any Ragas
metric name so a segment-analysis query (E9) can filter human signal
from automated signal by name alone, without also filtering on `source`.
"""


class FeedbackService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: FeedbackRepository,
        generation_usage_repository: GenerationUsageRepository,
        eval_score_repository: EvalScoreRepository,
    ) -> None:
        self._session = session
        self._repository = repository
        self._generation_usage_repository = generation_usage_repository
        self._eval_score_repository = eval_score_repository

    async def submit(
        self,
        *,
        owner_id: UUID,
        generation_id: UUID,
        surface: FeedbackSurface,
        rating: FeedbackRating,
        comment: str | None,
    ) -> Feedback:
        feedback = await self._repository.upsert(
            owner_id=owner_id,
            generation_id=generation_id,
            surface=surface,
            rating=rating,
            comment=comment,
        )
        #
        # Mirrored into eval_scores in the same transaction as the
        # feedback write, per EVALUATION_PLAN.md §6's "one place to
        # query, not three" -- a single `eval_scores` query by
        # `generation_id` now returns both the user's rating and every
        # automated score for that generation (E5), without a join
        # against `feedback`.
        #
        is_up = rating == FeedbackRating.UP
        await self._eval_score_repository.upsert(
            owner_id=owner_id,
            generation_id=generation_id,
            metric_name=USER_RATING_METRIC,
            score=1.0 if is_up else 0.0,
            passed=is_up,
            reason=comment or f"user rated {rating.value}",
            source=EvalScoreSource.HUMAN_FEEDBACK.value,
        )
        await self._session.commit()

        run_id = await self._generation_usage_repository.get_langsmith_run_id(generation_id)
        if run_id is not None:
            sync_user_feedback(
                run_id=run_id,
                feedback_id=feedback.id,
                rating=rating,
                comment=comment,
            )

        return feedback
