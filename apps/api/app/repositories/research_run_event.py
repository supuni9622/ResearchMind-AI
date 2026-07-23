"""Owner-scoped durable runtime-event journal."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research_run import ResearchRun
from app.models.research_run_event import ResearchRunEvent


class ResearchRunEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, *, run_id: UUID, event_type: str, metadata: dict) -> None:
        self._session.add(ResearchRunEvent(run_id=run_id, type=event_type, event_metadata=metadata))
        await self._session.flush()

    async def list_after_for_owner(
        self, *, run_id: UUID, owner_id: UUID, after: int, limit: int = 100
    ) -> list[ResearchRunEvent]:
        result = await self._session.execute(
            select(ResearchRunEvent)
            .join(ResearchRun, ResearchRun.id == ResearchRunEvent.run_id)
            .where(
                ResearchRunEvent.run_id == run_id,
                ResearchRun.owner_id == owner_id,
                ResearchRunEvent.id > after,
            )
            .order_by(ResearchRunEvent.id)
            .limit(limit)
        )
        return list(result.scalars())
