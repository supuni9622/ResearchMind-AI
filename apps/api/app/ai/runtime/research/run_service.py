"""Application service for idempotent Research Runtime lifecycle creation."""

from __future__ import annotations

from uuid import UUID, uuid4

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.runtime.research.types import TERMINAL_RESEARCH_RUN_STATUSES, ResearchRunStatus
from app.models.research_run import ResearchRun
from app.repositories.research_run import ResearchRunRepository
from app.repositories.research_run_dispatch import ResearchRunDispatchRepository

logger = structlog.get_logger()


class ResearchRunService:
    """Owns lifecycle creation; graph nodes do not create run records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = ResearchRunRepository(session)
        self._dispatches = ResearchRunDispatchRepository(session)

    async def create_or_get(
        self,
        *,
        owner_id: UUID,
        request_fingerprint: str,
        idempotency_key: str | None = None,
        conversation_id: UUID | None = None,
        parent_research_id: UUID | None = None,
    ) -> ResearchRun:
        if idempotency_key is not None:
            existing = await self._repository.get_by_idempotency_key(
                owner_id=owner_id,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
                if existing.request_fingerprint != request_fingerprint:
                    raise ValueError(
                        "Idempotency key was reused with a different research request."
                    )
                return existing

        try:
            run = await self._repository.create(
                ResearchRun(
                    owner_id=owner_id,
                    conversation_id=conversation_id,
                    parent_research_id=parent_research_id,
                    graph_thread_id=str(uuid4()),
                    status=ResearchRunStatus.CREATED.value,
                    idempotency_key=idempotency_key,
                    request_fingerprint=request_fingerprint,
                )
            )
            logger.info(
                "research_runtime.run.created",
                research_run_id=str(run.id),
                owner_id=str(owner_id),
                graph_thread_id=run.graph_thread_id,
            )
            return run
        except IntegrityError:
            # Concurrent requests with the same key race between the lookup
            # above and the unique constraint. The constraint is canonical;
            # after rolling back, replay the run it selected.
            await self._session.rollback()
            if idempotency_key is None:
                raise
            existing = await self._repository.get_by_idempotency_key(
                owner_id=owner_id,
                idempotency_key=idempotency_key,
            )
            if existing is None:
                raise
            if existing.request_fingerprint != request_fingerprint:
                raise ValueError(
                    "Idempotency key was reused with a different research request."
                ) from None
            return existing

    async def get_for_owner(self, *, run_id: UUID, owner_id: UUID) -> ResearchRun | None:
        """Read a lifecycle record only through the owner-scoped repository."""

        return await self._repository.get_by_id_for_owner(run_id=run_id, owner_id=owner_id)

    async def request_cancellation(self, *, run_id: UUID, owner_id: UUID) -> ResearchRun | None:
        """Flag a non-terminal run for cancellation; the graph observes this cooperatively.

        There is no synchronous abort: the worker checks this flag only at
        bounded points (before a new wave, before a new synthesis attempt),
        so cancellation takes effect on the next such checkpoint, not
        immediately.
        """

        run = await self._repository.get_by_id_for_owner(run_id=run_id, owner_id=owner_id)
        if run is None:
            return None
        if run.status in TERMINAL_RESEARCH_RUN_STATUSES or run.cancellation_requested:
            return run
        run.cancellation_requested = True
        await self._session.commit()
        logger.info(
            "research_runtime.run.cancellation_requested",
            research_run_id=str(run.id),
            owner_id=str(owner_id),
        )
        return run

    async def is_cancellation_requested(self, *, run_id: UUID) -> bool:
        return await self._repository.is_cancellation_requested(run_id=run_id)

    async def record_report_decision(
        self,
        *,
        run_id: UUID,
        owner_id: UUID,
        approved: bool,
        reason: str | None = None,
    ) -> ResearchRun | None:
        """Record the report-approval decision and re-queue the run's dispatch
        in one transaction -- both must land together, or neither does,
        otherwise a committed decision with no dispatch would strand the run
        in `awaiting_approval` forever."""

        run = await self._repository.get_by_id_for_owner(run_id=run_id, owner_id=owner_id)
        if run is None:
            return None
        if run.status != ResearchRunStatus.AWAITING_APPROVAL.value:
            raise ValueError(f"Research run '{run.id}' is not awaiting a report decision.")
        run.budget_usage = {
            **(run.budget_usage or {}),
            "report_decision": {
                "decision": "approved" if approved else "rejected",
                "reason": reason,
            },
        }
        await self._dispatches.reopen(run_id=run.id)
        await self._session.commit()
        logger.info(
            "research_runtime.run.report_decision_recorded",
            research_run_id=str(run.id),
            owner_id=str(owner_id),
            approved=approved,
        )
        return run
