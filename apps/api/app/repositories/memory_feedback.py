"""Persistence for explicit memory utility feedback."""

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FeedbackSurface, MemoryFeedbackSignal
from app.models.memory_feedback import MemoryFeedback


class MemoryFeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        *,
        owner_id: UUID,
        generation_id: UUID,
        surface: FeedbackSurface,
        signal: MemoryFeedbackSignal,
    ) -> MemoryFeedback:
        statement = (
            insert(MemoryFeedback)
            .values(
                owner_id=owner_id,
                generation_id=generation_id,
                surface=surface.value,
                signal=signal.value,
            )
            .on_conflict_do_update(
                constraint="uq_memory_feedback_owner_generation",
                set_={"surface": surface.value, "signal": signal.value},
            )
            .returning(MemoryFeedback)
        )
        result = await self._session.execute(
            statement, execution_options={"populate_existing": True}
        )
        return result.scalar_one()
