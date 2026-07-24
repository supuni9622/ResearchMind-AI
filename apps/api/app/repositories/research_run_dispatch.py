"""Transactional outbox persistence for Research Runtime workers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.runtime.research.types import ResearchRunDispatchStatus
from app.models.research_run_dispatch import ResearchRunDispatch


class ResearchRunDispatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, run_id: UUID) -> ResearchRunDispatch:
        dispatch = ResearchRunDispatch(
            run_id=run_id,
            status=ResearchRunDispatchStatus.PENDING.value,
        )
        self._session.add(dispatch)
        await self._session.flush()
        return dispatch

    async def count_active(self) -> int:
        """PENDING + RUNNING dispatch rows -- work not yet completed by any
        worker lane. Used as a global load-shedding signal ahead of proposal
        approval (see `ResearchQueueSaturatedError`); intentionally counts
        RUNNING too, since a lease that hasn't expired yet is still real
        in-flight demand, not free capacity."""

        result = await self._session.execute(
            select(func.count())
            .select_from(ResearchRunDispatch)
            .where(
                ResearchRunDispatch.status.in_(
                    (
                        ResearchRunDispatchStatus.PENDING.value,
                        ResearchRunDispatchStatus.RUNNING.value,
                    )
                )
            )
        )
        return result.scalar_one()

    async def claim_next(self, *, lease_seconds: int) -> ResearchRunDispatch | None:
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(ResearchRunDispatch)
            .where(
                or_(
                    ResearchRunDispatch.status == ResearchRunDispatchStatus.PENDING.value,
                    (ResearchRunDispatch.status == ResearchRunDispatchStatus.RUNNING.value)
                    & (ResearchRunDispatch.lease_expires_at < now),
                )
            )
            .order_by(ResearchRunDispatch.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        dispatch = result.scalar_one_or_none()
        if dispatch is None:
            return None
        dispatch.status = ResearchRunDispatchStatus.RUNNING.value
        dispatch.attempt_count += 1
        dispatch.lease_expires_at = now + timedelta(seconds=lease_seconds)
        await self._session.flush()
        return dispatch

    async def complete(self, *, run_id: UUID) -> None:
        dispatch = await self._session.get(ResearchRunDispatch, run_id, with_for_update=True)
        if dispatch is None:
            raise RuntimeError(f"Research runtime dispatch for run '{run_id}' was not found.")
        dispatch.status = ResearchRunDispatchStatus.COMPLETED.value
        dispatch.completed_at = datetime.now(UTC)
        dispatch.lease_expires_at = None
        await self._session.flush()

    async def reopen(self, *, run_id: UUID) -> None:
        """Re-queue an existing (`run_id` is the dispatch's own primary key,
        one row per run) dispatch so the worker picks the run back up --
        e.g. after a report-approval decision is recorded for a run paused
        at the graph's `interrupt()`. `create()` cannot be reused for this:
        it would violate the 1:1 run<->dispatch invariant."""

        dispatch = await self._session.get(ResearchRunDispatch, run_id, with_for_update=True)
        if dispatch is None:
            raise RuntimeError(f"Research runtime dispatch for run '{run_id}' was not found.")
        dispatch.status = ResearchRunDispatchStatus.PENDING.value
        dispatch.lease_expires_at = None
        dispatch.completed_at = None
        await self._session.flush()
