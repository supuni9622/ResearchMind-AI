"""
Valkey-backed implementation of the processing queue.
"""

from __future__ import annotations

import structlog
from app.core.settings import settings
from app.infrastructure.queue.exceptions import (
    QueueConnectionError,
    QueueDequeueError,
    QueueEnqueueError,
)
from app.infrastructure.queue.interfaces import ProcessingQueue
from app.infrastructure.queue.models import (
    ProcessingJob,
    QueueMessage,
)
from redis.asyncio import Redis

logger = structlog.get_logger()


class ValkeyQueue(ProcessingQueue):
    """
    Processing queue backed by Valkey.

    This implementation uses a Redis List for the MVP.

    Future iterations may migrate to Redis Streams without affecting the
    application layer.
    """

    def __init__(
        self,
        client: Redis,
    ) -> None:
        self._client = client
        self._queue_name = settings.queue_name
        self._dead_letter_queue_name = f"{settings.queue_name}-dlq"

    async def enqueue(
        self,
        job: ProcessingJob,
    ) -> None:
        """
        Enqueue a processing job.
        """

        try:
            payload = job.model_dump_json()

            await self._client.lpush(  # type: ignore[misc]
                self._queue_name,
                payload,
            )

        except Exception as exc:
            raise QueueEnqueueError("Failed to enqueue processing job.") from exc

    async def dequeue(
        self,
    ) -> QueueMessage | None:
        """
        Retrieve the next available processing job.

        Returns None when the queue is empty.
        """

        try:
            result = await self._client.rpop(  # type: ignore[misc]
                self._queue_name,
            )

            if result is None:
                return None
            if isinstance(result, list):
                raise QueueDequeueError("Unexpected list returned from Valkey.")

            job = ProcessingJob.model_validate_json(
                result,
            )
            return QueueMessage(
                job=job,
            )

        except Exception as exc:
            raise QueueDequeueError("Failed to dequeue processing job.") from exc

    async def acknowledge(
        self,
        message: QueueMessage,
    ) -> None:
        """
        Acknowledge successful processing.

        Redis Lists remove the message when it is popped, so no explicit
        acknowledgement is required.
        """

        return

    async def reject(
        self,
        message: QueueMessage,
    ) -> None:
        """
        Move a failed message into the dead-letter queue.
        """

        payload = message.job.model_dump_json()
        logger.warning(
            "queue.dead_letter",
            document_id=str(message.job.document_id),
            attempt=message.job.attempt,
            queue=self._dead_letter_queue_name,
        )

        await self._client.lpush(  # type: ignore[misc]
            self._dead_letter_queue_name,
            payload,
        )

        await self.acknowledge(
            message,
        )

    async def ping(self) -> None:
        """
        Verify connectivity to Valkey.
        """

        try:
            await self._client.ping()  # type: ignore[misc]

        except Exception as exc:
            raise QueueConnectionError("Unable to connect to Valkey.") from exc

    async def retry(
        self,
        job: ProcessingJob,
    ) -> None:
        await self.enqueue(job)
