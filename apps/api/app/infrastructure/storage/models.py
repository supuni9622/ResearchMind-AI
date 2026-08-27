from pydantic import BaseModel


class StorageObject(BaseModel):
    """Represents an object stored in S3."""

    bucket: str

    key: str

    content_type: str | None = None

    size: int | None = None

    etag: str | None = None
