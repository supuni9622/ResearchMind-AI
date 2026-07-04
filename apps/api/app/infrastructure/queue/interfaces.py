"""
Queue infrastructure interfaces.

Application services depend only on these abstractions rather than
concrete queue implementations.

Concrete providers (Valkey, Amazon SQS, etc.) implement this contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.infrastructure.queue.models import (
    ProcessingJob,
    QueueMessage,
)


class ProcessingQueue(ABC):
    """
    Abstract processing queue.

    Responsible for enqueueing and consuming document processing jobs.
    """

    @abstractmethod
    async def enqueue(
        self,
        job: ProcessingJob,
    ) -> None:
        """
        Enqueue a processing job.
        """

    @abstractmethod
    async def dequeue(
        self,
    ) -> QueueMessage | None:
        """
        Retrieve the next available processing job.

        Returns None when no jobs are available.
        """

    @abstractmethod
    async def acknowledge(
        self,
        message: QueueMessage,
    ) -> None:
        """
        Acknowledge successful processing of a message.
        """

    @abstractmethod
    async def reject(
        self,
        message: QueueMessage,
    ) -> None:
        """
        Reject processing of a message.

        Queue implementations may immediately requeue the message,
        delay it for retry, or move it to a dead-letter queue,
        depending on their capabilities.
        """
