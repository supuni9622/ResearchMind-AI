"""
Queue provider types.
"""

from __future__ import annotations

from enum import StrEnum


class QueueProvider(StrEnum):
    """
    Supported queue providers.
    """

    VALKEY = "valkey"
    SQS = "sqs"
