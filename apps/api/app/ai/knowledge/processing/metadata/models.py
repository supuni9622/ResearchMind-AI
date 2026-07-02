"""
Metadata models for the document processing platform.

These models are used by metadata providers to enrich the canonical
ProcessedDocument.

Each provider returns a MetadataUpdate describing the metadata it was
able to extract.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PDFMetadata(BaseModel):
    """
    Metadata extracted from a PDF document.
    """

    title: str | None = None

    author: str | None = None

    subject: str | None = None

    keywords: list[str] = Field(default_factory=list)

    creator: str | None = None

    producer: str | None = None

    creation_date: datetime | None = None

    modification_date: datetime | None = None


class LanguageMetadata(BaseModel):
    """
    Language detected from the document.
    """

    language: str | None = None

    confidence: float | None = None


class MetadataUpdate(BaseModel):
    """
    Metadata extracted by one or more metadata providers.

    Providers populate only the fields they are responsible for.
    The MetadataEnrichmentService merges multiple updates into the
    canonical DocumentMetadata.
    """

    pdf: PDFMetadata | None = None

    language: LanguageMetadata | None = None

    additional_metadata: dict[str, object] = Field(default_factory=dict)
