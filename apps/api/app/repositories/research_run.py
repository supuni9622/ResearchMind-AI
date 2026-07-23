"""Persistence operations for the Research Runtime lifecycle record."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research_run import ResearchRun


class ResearchRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: ResearchRun) -> ResearchRun:
        self._session.add(run)
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def get_by_id_for_owner(self, *, run_id: UUID, owner_id: UUID) -> ResearchRun | None:
        result = await self._session.execute(
            select(ResearchRun).where(ResearchRun.id == run_id, ResearchRun.owner_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(
        self, *, owner_id: UUID, idempotency_key: str
    ) -> ResearchRun | None:
        result = await self._session.execute(
            select(ResearchRun).where(
                ResearchRun.owner_id == owner_id,
                ResearchRun.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def is_cancellation_requested(self, *, run_id: UUID) -> bool:
        """Read the flag as a fresh column value, not a possibly-stale ORM attribute.

        The worker's session may hold a long-lived identity-mapped `ResearchRun`
        instance across an entire graph execution; a different session (the
        cancel API request) sets this flag independently. Selecting the column
        directly (rather than the mapped entity) always reflects the latest
        committed value.
        """

        result = await self._session.execute(
            select(ResearchRun.cancellation_requested).where(ResearchRun.id == run_id)
        )
        return bool(result.scalar_one_or_none())
