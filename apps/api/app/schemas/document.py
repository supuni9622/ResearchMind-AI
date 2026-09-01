# Upload/search models.
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentProcessingStatus, DocumentUploadStatus


class DocumentUploadResponse(BaseModel):
    """
    Response returned after a successful document upload.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    project_id: uuid.UUID | None = None

    filename: str

    content_type: str

    size_bytes: int

    upload_status: DocumentUploadStatus

    processing_status: DocumentProcessingStatus

    storage_key: str

    created_at: datetime


class DocumentResponse(BaseModel):
    """
    Generic document response.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    project_id: uuid.UUID | None = None

    filename: str

    content_type: str

    size_bytes: int

    upload_status: DocumentUploadStatus

    processing_status: DocumentProcessingStatus

    storage_key: str

    created_at: datetime

    processing_error: str | None = None


class DocumentListResponse(BaseModel):
    """Paginated page of a user's documents."""

    items: list[DocumentResponse]

    total: int

    limit: int

    offset: int


class DocumentKnowledgeStats(BaseModel):
    """Owner-scoped knowledge-base counts backed by the vector index."""

    indexed_chunk_count: int
    embedding_count: int
