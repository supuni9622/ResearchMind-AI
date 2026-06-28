# Domain models - Business representation used by the AI pipeline.
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.ai.knowledge.upload.enums import UploadSource, UploadStatus


class UploadDocument(BaseModel):
    """
    Domain model representing a document uploaded into the
    Knowledge Platform.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)

    filename: str

    content_type: str

    size_bytes: int

    storage_key: str

    checksum: str | None = None

    uploaded_by: UUID

    source: UploadSource = UploadSource.API

    status: UploadStatus = UploadStatus.PENDING

    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# Why these fields?
# Field	Purpose
# id	Internal upload identifier
# filename	Original filename
# content_type	MIME type
# size_bytes	File size
# storage_key - s3 key
# checksum	Added after storage
# uploaded_by	User who uploaded
# source	API / Web / CLI
# status	Upload lifecycle
# uploaded_at	Upload timestamp
