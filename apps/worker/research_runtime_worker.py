"""Dedicated worker for approved, durable Research Runtime executions."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from uuid import UUID

import structlog
from app.repositories.research_run_dispatch import ResearchRunDispatchRepository

logger = structlog.get_logger()


class ResearchRuntimeWorker:
    """Claims transactional-outbox records; it never shares the document worker."""

    def __init__(
        self,
        *,
        dispatches: ResearchRunDispatchRepository,
        execute_run: Callable[[UUID], Awaitable[object]],
        commit: Callable[[], Awaitable[None]],
        rollback: Callable[[], Awaitable[None]],
        poll_interval_seconds: float = 1.0,
        lease_seconds: int = 900,
    ) -> None:
        self._dispatches = dispatches
        self._execute_run = execute_run
        self._commit = commit
        self._rollback = rollback
        self._poll_interval_seconds = poll_interval_seconds
        self._lease_seconds = lease_seconds
        self._running = True

    async def run(self) -> None:
        logger.info("research_runtime_worker.started")
        while self._running:
            claimed = await self.run_once()
            if not claimed:
                await asyncio.sleep(self._poll_interval_seconds)
        logger.info("research_runtime_worker.shutdown_complete")

    async def run_once(self) -> bool:
        dispatch = await self._dispatches.claim_next(lease_seconds=self._lease_seconds)
        if dispatch is None:
            return False
        await self._commit()

        try:
            logger.info(
                "research_runtime_worker.run_claimed",
                research_run_id=str(dispatch.run_id),
                attempt=dispatch.attempt_count,
            )
            await self._execute_run(dispatch.run_id)
        except Exception:
            # The execution service persists a failed lifecycle outcome. Marking
            # this outbox record complete avoids rerunning a terminal failure;
            # recovery/resume is an explicit future user action.
            logger.exception(
                "research_runtime_worker.run_failed",
                research_run_id=str(dispatch.run_id),
            )
            # This worker holds one session for its entire process lifetime
            # (see `research_runtime_main.py`), so a failure that aborts the
            # session's transaction -- e.g. an error raised before the
            # execution service's first commit -- would otherwise poison
            # every dispatch claimed afterward, not just this one.
            await self._rollback()
        finally:
            await self._dispatches.complete(run_id=dispatch.run_id)
            await self._commit()
        return True

    def stop(self) -> None:
        logger.info("research_runtime_worker.stopping_requested")
        self._running = False
