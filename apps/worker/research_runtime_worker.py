"""Dedicated worker for approved, durable Research Runtime executions."""

from __future__ import annotations

import asyncio
import time
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
        expire_stale_awaiting_approval: Callable[[], Awaitable[int]] | None = None,
        expire_interval_seconds: float = 3600.0,
    ) -> None:
        self._dispatches = dispatches
        self._execute_run = execute_run
        self._commit = commit
        self._rollback = rollback
        self._poll_interval_seconds = poll_interval_seconds
        self._lease_seconds = lease_seconds
        self._expire_stale_awaiting_approval = expire_stale_awaiting_approval
        self._expire_interval_seconds = expire_interval_seconds
        self._last_expire_sweep_at: float | None = None
        self._running = True

    async def run(self) -> None:
        logger.info("research_runtime_worker.started")
        while self._running:
            await self._maybe_expire_stale_awaiting_approval()
            claimed = await self.run_once()
            if not claimed:
                await asyncio.sleep(self._poll_interval_seconds)
        logger.info("research_runtime_worker.shutdown_complete")

    async def _maybe_expire_stale_awaiting_approval(self) -> None:
        """Piggyback the AWAITING_APPROVAL expiry sweep on this worker's poll
        loop rather than adding a second scheduled process for it. Runs at
        most once per `_expire_interval_seconds`, independent of the (much
        tighter) dispatch poll interval.

        Failures are isolated with a rollback, not left to propagate: this
        worker holds one session for its entire process lifetime (see
        `research_runtime_main.py`), so an unrolled-back error here would
        poison every dispatch claimed afterward, not just this sweep.
        """

        if self._expire_stale_awaiting_approval is None:
            return
        now = time.monotonic()
        if (
            self._last_expire_sweep_at is not None
            and now - self._last_expire_sweep_at < self._expire_interval_seconds
        ):
            return
        self._last_expire_sweep_at = now
        try:
            expired_count = await self._expire_stale_awaiting_approval()
            if expired_count:
                logger.info(
                    "research_runtime_worker.awaiting_approval_expired",
                    expired_count=expired_count,
                )
        except Exception:
            logger.exception("research_runtime_worker.expire_sweep_failed")
            await self._rollback()

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
