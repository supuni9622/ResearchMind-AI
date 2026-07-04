"""
Background worker for asynchronous document processing.

The worker continuously consumes processing jobs from the configured
queue and delegates execution to the application service.

Responsibilities:

- Consume queued processing jobs
- Invoke QueuedDocumentProcessingService
- Acknowledge successful jobs
- Reject failed jobs

Business logic intentionally remains outside this worker.
"""

from __future__ import annotations

import asyncio
import time

import structlog
from app.core.settings import settings
from app.infrastructure.queue.interfaces import ProcessingQueue
from app.services.queued_document_processing_service import (
    QueuedDocumentProcessingService,
)

from apps.worker.metrics import WorkerMetrics

logger = structlog.get_logger()


class ProcessingWorker:
    """
    Background worker responsible for consuming processing jobs.
    """

    def __init__(
        self,
        *,
        queue: ProcessingQueue,
        queued_document_processing_service: QueuedDocumentProcessingService,
        poll_interval: float = 0.5,
    ) -> None:
        self._queue = queue
        self._queued_document_processing_service = queued_document_processing_service
        self._poll_interval = poll_interval
        self._running = True
        self._metrics = WorkerMetrics()

    async def run(self) -> None:
        """
        Continuously process queued jobs.
        """

        logger.info("processing_worker.started")

        while self._running:
            message = await self._queue.dequeue()

            if message is None:
                await asyncio.sleep(self._poll_interval)
                continue
            start = time.perf_counter()

            try:
                logger.info(
                    "processing_worker.job_received",
                    document_id=str(message.job.document_id),
                )

                await self._queued_document_processing_service.process(
                    message.job,
                )

                duration_ms = (time.perf_counter() - start) * 1000

                # metrics
                self._metrics.processed_jobs += 1
                self._metrics.successful_jobs += 1
                self._metrics.total_processing_time_ms += duration_ms

                # Logs metrics in every 2 attempts, we can increase this to a larger number in
                # production

                if self._metrics.processed_jobs % 2 == 0:
                    logger.info(
                        "processing_worker.metrics",
                        processed_jobs=self._metrics.processed_jobs,
                        successful_jobs=self._metrics.successful_jobs,
                        failed_jobs=self._metrics.failed_jobs,
                        retried_jobs=self._metrics.retried_jobs,
                        dead_letter_jobs=self._metrics.dead_letter_jobs,
                        average_processing_time_ms=(self._metrics.average_processing_time_ms),
                    )

                await self._queue.acknowledge(
                    message,
                )

                logger.info(
                    "processing_worker.job_completed",
                    document_id=str(message.job.document_id),
                )

            except Exception:
                self._metrics.failed_jobs += 1
                logger.exception(
                    "processing_worker.job_failed",
                    document_id=str(message.job.document_id),
                )

                job = message.job

                job.attempt += 1

                if job.attempt <= settings.queue_max_attempts:
                    logger.warning(
                        "processing_worker.retrying",
                        document_id=str(job.document_id),
                        attempt=job.attempt,
                    )

                    # metrics
                    self._metrics.retried_jobs += 1

                    await self._queue.retry(job)

                    await self._queue.acknowledge(message)

                else:
                    logger.error(
                        "processing_worker.max_attempts_exceeded",
                        document_id=str(job.document_id),
                        attempts=job.attempt,
                    )

                    # metrics
                    self._metrics.dead_letter_jobs += 1

                    await self._queue.reject(message)
        logger.info(
            "processing_worker.shutdown_complete",
        )

    def stop(self) -> None:
        """
        Request a graceful worker shutdown.

        The worker finishes the current job before exiting.
        """

        logger.info(
            "processing_worker.stopping_requested",
        )

        self._running = False
