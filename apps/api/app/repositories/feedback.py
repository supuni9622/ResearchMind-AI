"""Persistence queries for owner-scoped generation feedback."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FeedbackRating, FeedbackSurface
from app.models.feedback import Feedback


class FeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        *,
        owner_id: UUID,
        generation_id: UUID,
        surface: FeedbackSurface,
        rating: FeedbackRating,
        comment: str | None,
    ) -> Feedback:
        """
        Insert new feedback, or update the existing record for this
        (owner, generation) pair if the user already rated this
        generation once -- resubmitting changes a vote rather than
        accumulating a history nothing downstream needs yet.
        """

        statement = (
            insert(Feedback)
            .values(
                owner_id=owner_id,
                generation_id=generation_id,
                surface=surface.value,
                rating=rating.value,
                comment=comment,
            )
            .on_conflict_do_update(
                constraint="uq_feedback_owner_generation",
                set_={
                    "surface": surface.value,
                    "rating": rating.value,
                    "comment": comment,
                },
            )
            .returning(Feedback)
        )

        # `populate_existing=True` is required here, not optional: without
        # it, SQLAlchemy's ORM-enabled RETURNING leaves an already
        # identity-mapped object (e.g. a second upsert for the same
        # owner/generation within one session) with its *stale* attribute
        # values instead of the row `ON CONFLICT DO UPDATE` just wrote --
        # confirmed against a real Postgres row in
        # tests/integration/test_feedback_repository.py, which failed
        # without this before this fix.
        result = await self._session.execute(
            statement,
            execution_options={"populate_existing": True},
        )
        return result.scalar_one()

    async def get_for_generation(
        self,
        *,
        owner_id: UUID,
        generation_id: UUID,
    ) -> Feedback | None:
        statement = select(Feedback).where(
            Feedback.owner_id == owner_id,
            Feedback.generation_id == generation_id,
        )
        return (await self._session.execute(statement)).scalar_one_or_none()
