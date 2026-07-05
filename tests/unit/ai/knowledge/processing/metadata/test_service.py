"""
Unit tests for MetadataEnrichmentService.

Regression coverage for a production bug: PDFMetadataProvider was being
run against every document format, including DOCX. It opens the temp
file with pypdf.PdfReader regardless of format, so a DOCX upload crashed
mid-processing with `PdfStreamError: Stream has ended unexpectedly`
after upload had already succeeded.

Covers:
- A provider is skipped for document formats it does not support
- A provider that supports every format runs regardless of format
- Only the providers whose supported_formats include the document's
  format are ever invoked
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.ai.knowledge.processing.enums import DocumentFormat, ParserType
from app.ai.knowledge.processing.metadata.base import BaseMetadataProvider
from app.ai.knowledge.processing.metadata.models import MetadataUpdate
from app.ai.knowledge.processing.metadata.providers.language import (
    LanguageMetadataProvider,
)
from app.ai.knowledge.processing.metadata.providers.pdf import (
    PDFMetadataProvider,
)
from app.ai.knowledge.processing.metadata.registry import MetadataRegistry
from app.ai.knowledge.processing.metadata.service import (
    MetadataEnrichmentService,
)
from app.ai.knowledge.processing.models import (
    DocumentMetadata,
    DocumentStatistics,
    ProcessedDocument,
)


class FakeMetadataProvider(BaseMetadataProvider):
    """Configurable fake that records whether it was invoked."""

    def __init__(self, name: str, formats: set[DocumentFormat]) -> None:
        self._name = name
        self._formats = formats
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def supported_formats(self) -> set[DocumentFormat]:
        return self._formats

    async def enrich(
        self,
        *,
        document: ProcessedDocument,
        file_path: Path,
    ) -> MetadataUpdate:
        self.call_count += 1
        return MetadataUpdate()


def _make_document(document_format: DocumentFormat) -> ProcessedDocument:
    return ProcessedDocument(
        document_id=uuid4(),
        filename="test-document",
        format=document_format,
        parser=ParserType.DOCLING,
        metadata=DocumentMetadata(),
        statistics=DocumentStatistics(),
        raw_text="some text",
        markdown="some text",
        blocks=[],
    )


# ---------------------------------------------------------------------------
# Format-scoped provider dispatch
# ---------------------------------------------------------------------------


class TestFormatScopedDispatch:
    async def test_provider_skipped_for_unsupported_format(self) -> None:
        pdf_only = FakeMetadataProvider("pdf-only", {DocumentFormat.PDF})
        service = MetadataEnrichmentService(
            registry=MetadataRegistry(providers=[pdf_only]),
        )

        await service.enrich(
            document=_make_document(DocumentFormat.DOCX),
            file_path=Path("irrelevant.docx"),
        )

        assert pdf_only.call_count == 0

    async def test_provider_runs_for_supported_format(self) -> None:
        pdf_only = FakeMetadataProvider("pdf-only", {DocumentFormat.PDF})
        service = MetadataEnrichmentService(
            registry=MetadataRegistry(providers=[pdf_only]),
        )

        await service.enrich(
            document=_make_document(DocumentFormat.PDF),
            file_path=Path("irrelevant.pdf"),
        )

        assert pdf_only.call_count == 1

    async def test_all_format_provider_runs_for_every_format(self) -> None:
        all_formats = FakeMetadataProvider("all-formats", set(DocumentFormat))
        service = MetadataEnrichmentService(
            registry=MetadataRegistry(providers=[all_formats]),
        )

        for document_format in DocumentFormat:
            await service.enrich(
                document=_make_document(document_format),
                file_path=Path("irrelevant"),
            )

        assert all_formats.call_count == len(DocumentFormat)

    async def test_mixed_providers_only_matching_ones_run(self) -> None:
        pdf_only = FakeMetadataProvider("pdf-only", {DocumentFormat.PDF})
        all_formats = FakeMetadataProvider("all-formats", set(DocumentFormat))
        service = MetadataEnrichmentService(
            registry=MetadataRegistry(providers=[pdf_only, all_formats]),
        )

        await service.enrich(
            document=_make_document(DocumentFormat.DOCX),
            file_path=Path("irrelevant.docx"),
        )

        assert pdf_only.call_count == 0
        assert all_formats.call_count == 1


# ---------------------------------------------------------------------------
# Real provider format declarations (locks in the actual regression)
# ---------------------------------------------------------------------------


class TestRealProviderFormats:
    def test_pdf_provider_only_supports_pdf(self) -> None:
        provider = PDFMetadataProvider()

        assert provider.supports(DocumentFormat.PDF) is True
        assert provider.supports(DocumentFormat.DOCX) is False
        assert provider.supports(DocumentFormat.MARKDOWN) is False
        assert provider.supports(DocumentFormat.TEXT) is False

    def test_language_provider_supports_every_format(self) -> None:
        provider = LanguageMetadataProvider()

        for document_format in DocumentFormat:
            assert provider.supports(document_format) is True

    async def test_pdf_provider_never_invoked_for_docx_document(self) -> None:
        """
        The exact regression: uploading a DOCX must never open it with
        pypdf.PdfReader.
        """
        service = MetadataEnrichmentService(
            registry=MetadataRegistry(
                providers=[
                    PDFMetadataProvider(),
                    LanguageMetadataProvider(),
                ],
            ),
        )

        # A path that does not exist and is not a valid PDF — if
        # PDFMetadataProvider were invoked, this would raise.
        result = await service.enrich(
            document=_make_document(DocumentFormat.DOCX),
            file_path=Path("/nonexistent/not-a-real-file.docx"),
        )

        assert result.format == DocumentFormat.DOCX
