"""Dedicated memory lifecycle worker entry point.

Run one replica per environment with:
`python -m apps.worker.memory_lifecycle_main`. A Valkey lock also prevents
overlap during deploys or accidental duplicate scheduling.
"""

from __future__ import annotations

import asyncio
import signal

import structlog
from app.ai.memory.create import create_memory_vector_index, get_memory_metrics
from app.ai.memory.lifecycle.service import MemoryLifecycleService
from app.ai.observability.prometheus.create import start_worker_metrics_server
from app.core.settings import settings
from app.db.session import SessionFactory
from app.repositories.memory import MemoryRepository
from redis.asyncio import Redis

from apps.worker.memory_lifecycle_worker import MemoryLifecycleWorker

logger = structlog.get_logger()


async def main() -> None:
    start_worker_metrics_server(settings.memory_lifecycle_worker_metrics_port)
    redis = Redis.from_url(settings.valkey_url, decode_responses=True)
    async with SessionFactory() as session:
        worker = MemoryLifecycleWorker(
            service=MemoryLifecycleService(
                MemoryRepository(session),
                create_memory_vector_index(),
                metrics=get_memory_metrics(),
            ),
            redis=redis,
            settings=settings,
            metrics=get_memory_metrics(),
        )

        def shutdown(signum: int, frame: object | None) -> None:
            logger.info("memory_lifecycle_worker.signal_received", signal=signum)
            worker.stop()

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)
        try:
            if settings.memory_lifecycle_enabled:
                await worker.run()
            else:
                logger.info("memory_lifecycle_worker.disabled")
        finally:
            await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
