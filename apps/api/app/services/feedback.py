"""Transaction boundary for submitting generation feedback."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FeedbackRating, FeedbackSurface
from app.models.feedback import Feedback
from app.repositories.feedback import FeedbackRepository


class FeedbackService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: FeedbackRepository,
    ) -> None:
        self._session = session
        self._repository = repository

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
        return feedback
