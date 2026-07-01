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
