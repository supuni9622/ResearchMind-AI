"""Entry point for the dedicated approved Research Runtime worker.

Runs `settings.research_runtime_worker_concurrency` claim lanes concurrently
in this one process, each owning its own `AsyncSession` (sessions aren't
safe to share across concurrent asyncio tasks). The Postgres outbox
(`SELECT ... FOR UPDATE SKIP LOCKED`, see `ResearchRunDispatchRepository.
claim_next`) already makes concurrent claims safe across lanes, so this
is the cheapest way to raise this worker's throughput; running more copies
of this same process/container is equally safe and composes with it (see
REMAINING_WORK.md D2).
"""

from __future__ import annotations

import asyncio
import signal
from contextlib import AsyncExitStack

import structlog
from app.bootstrap.worker import create_research_runtime_worker
from app.core.settings import settings
from app.db.session import SessionFactory

logger = structlog.get_logger()


async def main() -> None:
    concurrency = max(1, settings.research_runtime_worker_concurrency)
    logger.info("research_runtime_worker.initializing", concurrency=concurrency)

    async with AsyncExitStack() as stack:
        workers = []
        for _lane_id in range(concurrency):
            session = await stack.enter_async_context(SessionFactory())
            workers.append(create_research_runtime_worker(session=session))

        def shutdown(signum: int, frame: object | None) -> None:
            logger.info(
                "research_runtime_worker.signal_received",
                signal=signal.Signals(signum).name,
            )
            for worker in workers:
                worker.stop()

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        await asyncio.gather(*(worker.run() for worker in workers))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("research_runtime_worker.stopped")
