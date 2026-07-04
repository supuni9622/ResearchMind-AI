"""
Entry point for the document processing worker.

This process continuously consumes document processing jobs from the
configured queue.

Run locally:

    python -m app.worker.main
"""

from __future__ import annotations

import asyncio
import signal

import structlog
from app.bootstrap.worker import create_processing_worker
from app.db.session import SessionFactory

logger = structlog.get_logger()


async def main() -> None:
    """
    Start the processing worker.
    """

    logger.info("processing_worker.initializing")

    async with SessionFactory() as session:
        worker = create_processing_worker(
            session=session,
        )

        def shutdown(
            signum: int,
            frame: object | None,
        ) -> None:
            logger.info(
                "processing_worker.signal_received",
                signal=signal.Signals(signum).name,
            )

            worker.stop()

        signal.signal(
            signal.SIGINT,
            shutdown,
        )

        signal.signal(
            signal.SIGTERM,
            shutdown,
        )

        logger.info(
            "processing_worker.running",
        )

        await worker.run()

        logger.info(
            "processing_worker.shutdown_complete",
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info(
            "processing_worker.stopped",
        )
