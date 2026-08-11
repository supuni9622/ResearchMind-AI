"""Transaction boundary for submitting generation feedback."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.observability.providers.langsmith.user_feedback import sync_user_feedback
from app.models.enums import FeedbackRating, FeedbackSurface
from app.models.feedback import Feedback
from app.repositories.feedback import FeedbackRepository
from app.repositories.generation_usage import GenerationUsageRepository


class FeedbackService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: FeedbackRepository,
        generation_usage_repository: GenerationUsageRepository,
    ) -> None:
        self._session = session
        self._repository = repository
        self._generation_usage_repository = generation_usage_repository

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
