"""
Entry point for the online evaluation scoring worker (E5,
EVALUATION_PLAN.md §14).

Run locally:

    python -m apps.worker.eval_scoring_main
"""

from __future__ import annotations

import asyncio
import signal

import structlog
from app.bootstrap.worker import create_eval_scoring_worker
from app.db.session import SessionFactory

logger = structlog.get_logger()


async def main() -> None:
    logger.info("eval_scoring_worker.initializing")

    async with SessionFactory() as session:
        worker = create_eval_scoring_worker(session=session)

        def shutdown(signum: int, frame: object | None) -> None:
            logger.info(
                "eval_scoring_worker.signal_received",
                signal=signal.Signals(signum).name,
            )
            worker.stop()

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        await worker.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("eval_scoring_worker.stopped")
