from enum import StrEnum


class DocumentUploadStatus(StrEnum):
    """Lifecycle status of an uploaded document."""

    PENDING = "pending"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentProcessingStatus(StrEnum):
    """
    AI document processing lifecycle.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(StrEnum):
    """
    Who authored a chat Message.
    """

    USER = "user"
    ASSISTANT = "assistant"


class FeedbackRating(StrEnum):
    """
    Thumbs up/down on a single generation (EVALUATION_PLAN.md §16 phase 3).
    """

    UP = "up"
    DOWN = "down"


class FeedbackSurface(StrEnum):
    """
    Which product surface a piece of feedback was left on -- matches the
    `workflow` field in EVALUATION_PLAN.md §3's golden-dataset schema, so
    feedback and golden-set examples can eventually be sliced the same way.
    """

    CHAT = "chat"
    LINEAR_RESEARCH = "linear_research"
    DEEP_RESEARCH = "deep_research"
