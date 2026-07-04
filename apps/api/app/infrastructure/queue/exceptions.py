"""
Exceptions for the queue infrastructure.

Queue provider implementations should raise these exceptions rather than
provider-specific exceptions, allowing the application layer to remain
independent of the underlying queue technology.
"""

from __future__ import annotations


class QueueError(Exception):
    """
    Base exception for queue operations.
    """


class QueueConnectionError(QueueError):
    """
    Raised when a queue provider cannot be reached.
    """


class QueueEnqueueError(QueueError):
    """
    Raised when a job cannot be enqueued.
    """


class QueueDequeueError(QueueError):
    """
    Raised when a job cannot be dequeued.
    """


class QueueAcknowledgeError(QueueError):
    """
    Raised when a processed message cannot be acknowledged.
    """


class QueueRejectError(QueueError):
    """
    Raised when a message cannot be rejected or requeued.
    """
