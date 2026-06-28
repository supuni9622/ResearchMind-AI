from enum import StrEnum


class UploadStatus(StrEnum):
    """Represents the current state of a document upload."""

    PENDING = "pending"
    VALIDATED = "validated"
    STORED = "stored"
    FAILED = "failed"


class UploadSource(StrEnum):
    """Indicates where the upload originated."""

    API = "api"
    WEB = "web"
    CLI = "cli"
    SYSTEM = "system"
