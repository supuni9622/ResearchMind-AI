from enum import StrEnum


class DocumentStatus(StrEnum):
    """Lifecycle status of an uploaded document."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"
