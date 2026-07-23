"""Entry point for the dedicated approved Research Runtime worker."""

from __future__ import annotations

import asyncio
import signal

import structlog
from app.bootstrap.worker import create_research_runtime_worker
from app.db.session import SessionFactory

logger = structlog.get_logger()


async def main() -> None:
    logger.info("research_runtime_worker.initializing")
    async with SessionFactory() as session:
        worker = create_research_runtime_worker(session=session)

        def shutdown(signum: int, frame: object | None) -> None:
            logger.info(
                "research_runtime_worker.signal_received",
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
        logger.info("research_runtime_worker.stopped")
