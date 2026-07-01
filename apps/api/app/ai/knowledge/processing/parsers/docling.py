"""
Docling document parser.

This parser converts supported documents into the canonical
ProcessedDocument representation using Docling.

The parser intentionally relies only on Docling's stable public APIs.

Semantic block extraction is intentionally deferred to the
Chunking Platform (Phase 2.3).
"""

from __future__ import annotations

from pathlib import Path

import structlog
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from app.ai.knowledge.processing.enums import (
    DocumentFormat,
    ParserType,
)
from app.ai.knowledge.processing.exceptions import DocumentParsingError
from app.ai.knowledge.processing.interfaces import ParseRequest
from app.ai.knowledge.processing.models import (
    DocumentMetadata,
    DocumentStatistics,
    ProcessedDocument,
)
from app.ai.knowledge.processing.parsers.base import BaseDocumentParser

logger = structlog.get_logger()


class DoclingParser(BaseDocumentParser):
    """
    Parser implementation backed by Docling.
    """

    def __init__(self) -> None:
        pipeline_options = PdfPipelineOptions(do_ocr=False)
        self._converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            }
        )

    @property
    def parser_name(self) -> str:
        return "Docling"

    @property
    def supported_formats(self) -> set[DocumentFormat]:
        return {
            DocumentFormat.PDF,
            DocumentFormat.DOCX,
            DocumentFormat.MARKDOWN,
            DocumentFormat.TEXT,
        }

    async def parse(
        self,
        request: ParseRequest,
    ) -> ProcessedDocument:
        """
        Parse a document into the canonical ResearchMind model.
        """

        log = logger.bind(
            document_id=str(request.document_id),
            document_format=request.document_format.value,
            file_path=str(request.file_path),
            parser=self.parser_name,
        )

        log.debug("parser.docling.parse.started")

        try:
            conversion_result = self._converter.convert(str(request.file_path))
        except Exception as exc:
            log.exception(
                "parser.docling.conversion_failed",
                exc_type=type(exc).__name__,
            )
            raise DocumentParsingError(
                f"Docling failed to convert '{request.file_path}': {exc}"
            ) from exc

        document = conversion_result.document

        try:
            markdown = document.export_to_markdown()
            raw_text = document.export_to_text()
        except Exception as exc:
            log.exception(
                "parser.docling.export_failed",
                exc_type=type(exc).__name__,
            )
            raise DocumentParsingError(
                f"Docling failed to export '{request.file_path}': {exc}"
            ) from exc

        metadata = self._build_metadata(source=request.file_path)
        statistics = self._build_statistics(raw_text=raw_text)

        log.info(
            "parser.docling.parse.completed",
            char_count=statistics.character_count,
            word_count=statistics.word_count,
            line_count=statistics.line_count,
        )

        return ProcessedDocument(
            format=request.document_format,
            parser=ParserType.DOCLING,
            metadata=metadata,
            statistics=statistics,
            raw_text=raw_text,
            markdown=markdown,
            blocks=[],
        )

    def _build_metadata(
        self,
        *,
        source: Path,
    ) -> DocumentMetadata:
        """
        Build the canonical metadata.

        Rich metadata extraction will be added in a future milestone.
        """

        return DocumentMetadata(
            title=source.stem,
            source=str(source),
        )

    def _build_statistics(
        self,
        *,
        raw_text: str,
    ) -> DocumentStatistics:
        """
        Compute document statistics.
        """

        return DocumentStatistics(
            character_count=len(raw_text),
            word_count=len(raw_text.split()),
            line_count=len(raw_text.splitlines()),
        )
