"""
PDF statistics provider.

Extracts statistics that are specific to PDF documents.

Current responsibilities:

- Page count

Future structural statistics (headings, paragraphs, tables, figures,
etc.) are intentionally handled by the Docling statistics provider.
"""

from __future__ import annotations

from pathlib import Path

from app.ai.knowledge.processing.models import ProcessedDocument
from app.ai.knowledge.processing.statistics.base import (
    BaseStatisticsProvider,
)
from app.ai.knowledge.processing.statistics.models import (
    StatisticsUpdate,
)
from pypdf import PdfReader


class PDFStatisticsProvider(BaseStatisticsProvider):
    """
    Statistics provider for PDF documents.
    """

    @property
    def provider_name(self) -> str:
        return "PDF Statistics"

    async def enrich(
        self,
        *,
        document: ProcessedDocument,
        file_path: Path,
    ) -> StatisticsUpdate:
        """
        Extract PDF-specific statistics.

        Currently this provider extracts only the page count.
        """

        if document.format.value != "pdf":
            return StatisticsUpdate()

        reader = PdfReader(str(file_path))

        return StatisticsUpdate(
            page_count=len(reader.pages),
        )
