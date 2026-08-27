"""Poll loop wrapping `OnlineScoringJob` (E5, EVALUATION_PLAN.md §14)."""

from __future__ import annotations

import asyncio

import structlog
from app.ai.runtime.generation.online_scoring.job import OnlineScoringJob

logger = structlog.get_logger()


class EvalScoringWorker:
    """
    Unlike `ResearchRuntimeWorker`'s outbox-claim loop, this job has no
    per-row lease to claim -- `run_once()` processes a whole batch per
    tick via `GenerationUsageRepository.list_unscored_since()`'s
    anti-join. The loop is therefore a plain fixed-interval poll: sleep
    `poll_interval_seconds` after every tick regardless of whether that
    tick found candidates, rather than draining the queue as fast as
    possible -- this job scores already-completed requests informationally,
    nothing is waiting on low latency the way request-serving workers are.
    """

    def __init__(
        self,
        *,
        job: OnlineScoringJob,
        poll_interval_seconds: float = 30.0,
    ) -> None:
        self._job = job
        self._poll_interval_seconds = poll_interval_seconds
        self._running = True

    async def run(self) -> None:
        logger.info("eval_scoring_worker.started")
        while self._running:
            await self.run_once()
            await asyncio.sleep(self._poll_interval_seconds)
        logger.info("eval_scoring_worker.shutdown_complete")

    async def run_once(self) -> int:
        try:
            processed = await self._job.run_once()
            if processed:
                logger.info("eval_scoring_worker.tick_completed", processed=processed)
            return processed
        except Exception:
            logger.exception("eval_scoring_worker.tick_failed")
            return 0

    def stop(self) -> None:
        logger.info("eval_scoring_worker.stopping_requested")
        self._running = False
