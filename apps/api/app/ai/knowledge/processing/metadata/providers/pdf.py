"""
PDF metadata provider.

Extracts document metadata from the original PDF using pypdf.

This provider reads embedded PDF metadata only.

It does not inspect document content or perform language detection.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

from app.ai.knowledge.processing.enums import DocumentFormat
from app.ai.knowledge.processing.metadata.base import BaseMetadataProvider
from app.ai.knowledge.processing.metadata.models import (
    MetadataUpdate,
    PDFMetadata,
)
from app.ai.knowledge.processing.models import ProcessedDocument


class PDFMetadataProvider(BaseMetadataProvider):
    """
    Extracts embedded PDF metadata.
    """

    @property
    def provider_name(self) -> str:
        return "PDF Metadata"

    @property
    def supported_formats(self) -> set[DocumentFormat]:
        return {DocumentFormat.PDF}

    async def enrich(
        self,
        *,
        document: ProcessedDocument,
        file_path: Path,
    ) -> MetadataUpdate:
        """
        Extract metadata embedded within a PDF document.
        """

        reader = PdfReader(file_path)

        metadata = reader.metadata

        if metadata is None:
            return MetadataUpdate()

        return MetadataUpdate(
            pdf=PDFMetadata(
                title=self._clean(metadata.title),
                author=self._clean(metadata.author),
                subject=self._clean(metadata.subject),
                creator=self._clean(metadata.creator),
                producer=self._clean(metadata.producer),
                keywords=self._parse_keywords(metadata.get("/Keywords")),
                creation_date=self._parse_pdf_datetime(metadata.get("/CreationDate")),
                modification_date=self._parse_pdf_datetime(metadata.get("/ModDate")),
            )
        )

    def _clean(
        self,
        value: str | None,
    ) -> str | None:
        """
        Normalize empty strings.
        """

        if value is None:
            return None

        value = value.strip()

        return value or None

    def _parse_keywords(
        self,
        value: str | None,
    ) -> list[str]:
        """
        Parse PDF keyword metadata.
        """

        if not value:
            return []

        return [keyword.strip() for keyword in value.split(",") if keyword.strip()]

    def _parse_pdf_datetime(
        self,
        value: str | None,
    ) -> datetime | None:
        """
        Parse a PDF date string.

        PDF dates typically follow:

            D:YYYYMMDDHHmmSS
        """

        if not value:
            return None

        value = value.removeprefix("D:")

        try:
            return datetime.strptime(
                value[:14],
                "%Y%m%d%H%M%S",
            )
        except ValueError:
            return None
