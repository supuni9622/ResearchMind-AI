from __future__ import annotations

import asyncio

import boto3
from app.infrastructure.queue.exceptions import (
    QueueAcknowledgeError,
    QueueDequeueError,
    QueueEnqueueError,
    QueueRejectError,
)
from app.infrastructure.queue.interfaces import ProcessingQueue
from app.infrastructure.queue.models import (
    ProcessingJob,
    QueueMessage,
)
from botocore.exceptions import BotoCoreError, ClientError


class SQSQueue(ProcessingQueue):
    """
    Amazon SQS implementation.

    Uses the official boto3 SDK executed inside asyncio.to_thread()
    so the public interface remains asynchronous while avoiding
    aioboto3 dependency issues.
    """

    def __init__(
        self,
        *,
        queue_url: str,
        region_name: str,
    ) -> None:
        self._queue_url = queue_url

        self._client = boto3.client(
            "sqs",
            region_name=region_name,
        )

    async def enqueue(
        self,
        job: ProcessingJob,
    ) -> None:
        """
        Send a processing job to SQS.
        """

        body = job.model_dump_json()

        try:
            await asyncio.to_thread(
                self._client.send_message,
                QueueUrl=self._queue_url,
                MessageBody=body,
            )
        except (ClientError, BotoCoreError) as exc:
            raise QueueEnqueueError("Failed to enqueue processing job.") from exc

    async def dequeue(
        self,
    ) -> QueueMessage | None:
        """
        Receive one processing job from SQS.

        The message is not removed until acknowledge() is called.
        """

        try:
            response = await asyncio.to_thread(
                self._client.receive_message,
                QueueUrl=self._queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,
                VisibilityTimeout=300,
            )
        except (ClientError, BotoCoreError) as exc:
            raise QueueDequeueError("Failed to dequeue processing job.") from exc

        messages = response.get("Messages", [])

        if not messages:
            return None

        message = messages[0]

        job = ProcessingJob.model_validate_json(
            message["Body"],
        )

        return QueueMessage(
            job=job,
            receipt_handle=message["ReceiptHandle"],
        )

    async def acknowledge(
        self,
        message: QueueMessage,
    ) -> None:
        """
        Delete a processed message from SQS.
        """

        try:
            await asyncio.to_thread(
                self._client.delete_message,
                QueueUrl=self._queue_url,
                ReceiptHandle=message.receipt_handle,
            )
        except (ClientError, BotoCoreError) as exc:
            raise QueueAcknowledgeError("Failed to acknowledge processing job.") from exc

    async def reject(
        self,
        message: QueueMessage,
    ) -> None:
        """
        Make the message immediately visible again.
        """

        try:
            await asyncio.to_thread(
                self._client.change_message_visibility,
                QueueUrl=self._queue_url,
                ReceiptHandle=message.receipt_handle,
                VisibilityTimeout=0,
            )

        except (ClientError, BotoCoreError) as exc:
            raise QueueRejectError("Failed to reject processing job.") from exc

    async def retry(
        self,
        job: ProcessingJob,
    ) -> None:
        await self.enqueue(job)
