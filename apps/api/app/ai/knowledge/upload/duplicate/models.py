"""
Models for duplicate document detection.

These models define the request and response objects exchanged
between the upload workflow and the duplicate detection service.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.models.document import Document


class DuplicateCheckRequest(BaseModel):
    """
    Request to perform duplicate detection.
    """

    owner_id: UUID

    sha256: str


class DuplicateCheckResult(BaseModel):
    """
    Result of duplicate detection.
    """

    is_duplicate: bool

    document: Document | None = None

    model_config = {
        "arbitrary_types_allowed": True,
    }
