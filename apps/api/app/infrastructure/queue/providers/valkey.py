"""
Valkey-backed implementation of the processing queue.
"""

from __future__ import annotations

from app.infrastructure.queue.exceptions import (
    QueueConnectionError,
    QueueDequeueError,
    QueueEnqueueError,
    QueueRejectError,
)
from app.infrastructure.queue.interfaces import ProcessingQueue
from app.infrastructure.queue.models import (
    ProcessingJob,
    QueueMessage,
)
from redis.asyncio import Redis


class ValkeyQueue(ProcessingQueue):
    """
    Processing queue backed by Valkey.

    This implementation uses a Redis List for the MVP.

    Future iterations may migrate to Redis Streams without affecting the
    application layer.
    """

    DEFAULT_QUEUE_NAME = "document-processing"

    def __init__(
        self,
        client: Redis,
        queue_name: str = DEFAULT_QUEUE_NAME,
    ) -> None:
        self._client = client
        self._queue_name = queue_name

    async def enqueue(
        self,
        job: ProcessingJob,
    ) -> None:
        """
        Enqueue a processing job.
        """

        try:
            payload = job.model_dump_json()

            await self._client.lpush(
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
            result = await self._client.rpop(
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
        Requeue a failed processing job.
        """

        try:
            await self.enqueue(
                message.job,
            )
        except Exception as exc:
            raise QueueRejectError("Failed to requeue processing job.") from exc

    async def ping(self) -> None:
        """
        Verify connectivity to Valkey.
        """

        try:
            await self._client.ping()

        except Exception as exc:
            raise QueueConnectionError("Unable to connect to Valkey.") from exc

    async def retry(
        self,
        job: ProcessingJob,
    ) -> None:
        await self.enqueue(job)
