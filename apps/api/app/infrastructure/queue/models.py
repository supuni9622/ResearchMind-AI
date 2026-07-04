"""
Models for the queue infrastructure.

These models define the canonical job payload exchanged between
application services and queue providers.

Queue implementations (Valkey, Amazon SQS, etc.) serialize and
deserialize these models, allowing the application layer to remain
independent of the underlying messaging technology.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProcessingJob(BaseModel):
    """
    Represents a document processing job.

    This is the canonical payload placed onto the processing queue.
    """

    document_id: UUID

    owner_id: UUID

    storage_key: str

    attempt: int = 1

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )


class QueueMessage(BaseModel):
    """
    Represents a queued message.

    Queue providers may attach provider-specific metadata
    (message IDs, receipt handles, delivery tokens, etc.)
    while exposing a common interface to the application.
    """

    job: ProcessingJob

    message_id: str | None = None

    receipt_handle: str | None = None
