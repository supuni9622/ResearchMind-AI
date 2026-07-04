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

import structlog
from app.infrastructure.queue.interfaces import ProcessingQueue
from app.services.queued_document_processing_service import (
    QueuedDocumentProcessingService,
)

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
        poll_interval: float = 1.0,
    ) -> None:
        self._queue = queue
        self._queued_document_processing_service = queued_document_processing_service
        self._poll_interval = poll_interval

    async def run(self) -> None:
        """
        Continuously process queued jobs.
        """

        logger.info("processing_worker.started")

        while True:
            message = await self._queue.dequeue()

            if message is None:
                await asyncio.sleep(self._poll_interval)
                continue

            try:
                logger.info(
                    "processing_worker.job_received",
                    document_id=str(message.job.document_id),
                )

                await self._queued_document_processing_service.process(
                    message.job,
                )

                await self._queue.acknowledge(
                    message,
                )

                logger.info(
                    "processing_worker.job_completed",
                    document_id=str(message.job.document_id),
                )

            except Exception:
                logger.exception(
                    "processing_worker.job_failed",
                    document_id=str(message.job.document_id),
                )

                await self._queue.reject(
                    message,
                )
