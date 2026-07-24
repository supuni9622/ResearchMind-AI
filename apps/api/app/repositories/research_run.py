"""Persistence operations for the Research Runtime lifecycle record."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.runtime.research.types import ResearchRunStatus
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

    async def list_for_conversation(
        self, *, conversation_id: UUID, owner_id: UUID
    ) -> list[ResearchRun]:
        """Every Deep Research run in a conversation thread, oldest first --
        mirrors `ResearchRepository.list_sessions_for_conversation`'s shape,
        so a conversation replay can interleave both turn types. Scoped to
        `owner_id` so a caller can never enumerate another user's runs even
        if they guess a `conversation_id`."""

        result = await self._session.execute(
            select(ResearchRun)
            .where(
                ResearchRun.conversation_id == conversation_id,
                ResearchRun.owner_id == owner_id,
            )
            .order_by(ResearchRun.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_stale_awaiting_approval(self, *, older_than: datetime) -> list[ResearchRun]:
        """System-wide (not owner-scoped): the expiry sweep runs as an
        operator/ops job, not on behalf of a single request's owner.

        Covers both human-checkpoint pauses -- report approval and (as of
        the plan-approval checkpoint) plan approval -- since either can
        strand a run indefinitely if the user never returns to it."""

        result = await self._session.execute(
            select(ResearchRun).where(
                ResearchRun.status.in_(
                    (
                        ResearchRunStatus.AWAITING_APPROVAL.value,
                        ResearchRunStatus.AWAITING_PLAN_APPROVAL.value,
                    )
                ),
                ResearchRun.updated_at < older_than,
            )
        )
        return list(result.scalars().all())

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
