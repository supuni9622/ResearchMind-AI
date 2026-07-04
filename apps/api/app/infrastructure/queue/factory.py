"""
Factory for creating the configured processing queue.
"""

from __future__ import annotations

from app.core.settings import Settings
from app.infrastructure.queue.enums import QueueProvider
from app.infrastructure.queue.interfaces import ProcessingQueue
from app.infrastructure.queue.providers.sqs import SQSQueue
from app.infrastructure.queue.providers.valkey import ValkeyQueue
from redis.asyncio import Redis


def create_processing_queue(
    settings: Settings,
) -> ProcessingQueue:
    """
    Create the configured processing queue.
    """

    match settings.queue_provider:
        case QueueProvider.VALKEY:
            redis = Redis.from_url(
                settings.valkey_url,
                decode_responses=True,
            )

            return ValkeyQueue(
                client=redis,
            )

        case QueueProvider.SQS:
            return SQSQueue(
                queue_url=settings.sqs_queue_url,
                region_name=settings.aws_region,
            )

        case _:
            raise ValueError(f"Unsupported queue provider: {settings.queue_provider}")
