"""
Unit tests for ProcessingService.

Covers:
- Happy path: correct parser resolved, parse() called, returns COMPLETED result
- Parser errors propagate out of process()
- ParserNotFoundError from registry propagates unchanged
- Document returned in result matches what the parser produced
- Service delegates to the registry rather than importing parsers directly
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.ai.knowledge.processing.artifact_builder import ArtifactBuilder
from app.ai.knowledge.processing.enums import DocumentFormat, ParserType, ProcessingStatus
from app.ai.knowledge.processing.exceptions import ParserNotFoundError
from app.ai.knowledge.processing.interfaces import DocumentParser, ParseRequest
from app.ai.knowledge.processing.models import (
    DocumentMetadata,
    DocumentStatistics,
    ParagraphBlock,
    ProcessedDocument,
    ProcessingResult,
)
from app.ai.knowledge.processing.registry import ParserRegistry
from app.ai.knowledge.processing.service import ProcessingService
from app.ai.knowledge.processing.temporary_file_manager import (
    TemporaryFileManager,
)

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

_OWNER_ID = "test-owner"


def _make_request(
    document_format: DocumentFormat = DocumentFormat.PDF,
) -> ParseRequest:
    return ParseRequest(
        document_id=uuid.uuid4(),
        storage_key="test-storage-key",
        filename="test.pdf",
        content_type="application/pdf",
        document_format=document_format,
    )


def _make_storage() -> AsyncMock:
    """Build a fake storage that returns dummy document bytes."""
    storage = AsyncMock()
    storage.download = AsyncMock(return_value=b"fake document bytes")
    return storage


def _make_metadata_service() -> AsyncMock:
    """Build a pass-through metadata service: returns the document unchanged."""
    metadata_service = AsyncMock()
    metadata_service.enrich = AsyncMock(side_effect=lambda *, document, file_path: document)
    return metadata_service


def _make_statistics_service() -> AsyncMock:
    """Build a pass-through statistics service: returns the document unchanged."""
    statistics_service = AsyncMock()
    statistics_service.enrich = AsyncMock(side_effect=lambda *, document, file_path: document)
    return statistics_service


def _make_chunking_service() -> AsyncMock:
    """Build a fake chunking service: returns a single dummy chunk."""
    chunking_service = AsyncMock()
    chunking_service.chunk = AsyncMock(return_value=[MagicMock()])
    return chunking_service


def _make_chunk_artifact_builder() -> MagicMock:
    """Build a fake chunk artifact builder: returns an opaque artifact."""
    builder = MagicMock()
    builder.build = MagicMock(return_value=MagicMock())
    return builder


def _make_chunk_artifact_writer() -> AsyncMock:
    """Build a no-op chunk artifact writer."""
    writer = AsyncMock()
    writer.write = AsyncMock(return_value=None)
    return writer


def _make_embedding_service() -> AsyncMock:
    """Build a fake embedding service: returns a single dummy embedding."""
    embedding_service = AsyncMock()
    embedding_service.embed = AsyncMock(return_value=[MagicMock()])
    return embedding_service


def _make_embedding_artifact_builder() -> MagicMock:
    """Build a fake embedding artifact builder: returns an opaque artifact."""
    builder = MagicMock()
    builder.build = MagicMock(return_value=MagicMock())
    return builder


def _make_embedding_artifact_writer() -> AsyncMock:
    """Build a no-op embedding artifact writer."""
    writer = AsyncMock()
    writer.write = AsyncMock(return_value=None)
    return writer


def _make_document(blocks: list | None = None) -> ProcessedDocument:
    return ProcessedDocument(
        document_id=uuid.uuid4(),
        filename="test.pdf",
        format=DocumentFormat.PDF,
        parser=ParserType.DOCLING,
        metadata=DocumentMetadata(),
        statistics=DocumentStatistics(),
        raw_text="sample text",
        markdown="# Sample",
        blocks=blocks or [],
    )


def _make_service(parser: DocumentParser, *extra_parsers: DocumentParser) -> ProcessingService:
    """Build a ProcessingService with a no-op artifact writer."""
    registry = ParserRegistry(parsers=[parser, *extra_parsers])
    writer = AsyncMock()
    writer.write = AsyncMock(return_value=None)
    return ProcessingService(
        storage=_make_storage(),
        temporary_file_manager=TemporaryFileManager(),
        parser_registry=registry,
        metadata_service=_make_metadata_service(),
        statistics_service=_make_statistics_service(),
        artifact_builder=ArtifactBuilder(),
        artifact_writer=writer,
        chunking_service=_make_chunking_service(),
        chunk_artifact_builder=_make_chunk_artifact_builder(),
        chunk_artifact_writer=_make_chunk_artifact_writer(),
        embedding_service=_make_embedding_service(),
        embedding_artifact_builder=_make_embedding_artifact_builder(),
        embedding_artifact_writer=_make_embedding_artifact_writer(),
    )


class FakeParser(DocumentParser):
    """Configurable fake that either returns a document or raises."""

    def __init__(
        self,
        formats: set[DocumentFormat],
        *,
        result: ProcessedDocument | None = None,
        raises: Exception | None = None,
    ) -> None:
        self._formats = formats
        self._result = result
        self._raises = raises
        self.call_count = 0
        self.last_request: ParseRequest | None = None

    @property
    def parser_name(self) -> str:
        return "fake-parser"

    @property
    def supported_formats(self) -> set[DocumentFormat]:
        return self._formats

    async def parse(self, request: ParseRequest) -> ProcessedDocument:
        self.call_count += 1
        self.last_request = request
        if self._raises is not None:
            raise self._raises
        if self._result is None:  # pragma: no cover
            raise RuntimeError("FakeParser: no result configured")
        return self._result


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestProcessingServiceHappyPath:
    @pytest.fixture()
    def document(self) -> ProcessedDocument:
        return _make_document(blocks=[ParagraphBlock(id="p1", text="Hello")])

    @pytest.fixture()
    def parser(self, document: ProcessedDocument) -> FakeParser:
        return FakeParser({DocumentFormat.PDF}, result=document)

    @pytest.fixture()
    def service(self, parser: FakeParser) -> ProcessingService:
        return _make_service(parser)

    async def test_returns_completed_status(
        self,
        service: ProcessingService,
        document: ProcessedDocument,
    ) -> None:
        request = _make_request(DocumentFormat.PDF)
        result = await service.process(owner_id=_OWNER_ID, request=request)
        assert result.status == ProcessingStatus.COMPLETED

    async def test_result_document_matches_parser_output(
        self,
        service: ProcessingService,
        document: ProcessedDocument,
        parser: FakeParser,
    ) -> None:
        request = _make_request(DocumentFormat.PDF)
        result = await service.process(owner_id=_OWNER_ID, request=request)
        expected = document.model_copy(
            update={"document_id": request.document_id, "filename": request.filename}
        )
        assert result.document == expected

    async def test_parser_called_exactly_once(
        self,
        service: ProcessingService,
        parser: FakeParser,
    ) -> None:
        await service.process(owner_id=_OWNER_ID, request=_make_request(DocumentFormat.PDF))
        assert parser.call_count == 1

    async def test_parser_receives_original_request(
        self,
        service: ProcessingService,
        parser: FakeParser,
    ) -> None:
        request = _make_request(DocumentFormat.PDF)
        await service.process(owner_id=_OWNER_ID, request=request)

        assert parser.last_request is not None
        assert parser.last_request.document_id == request.document_id
        assert parser.last_request.storage_key == request.storage_key
        assert parser.last_request.filename == request.filename
        assert parser.last_request.file_path is not None

    async def test_result_error_is_none(
        self,
        service: ProcessingService,
    ) -> None:
        result = await service.process(
            owner_id=_OWNER_ID, request=_make_request(DocumentFormat.PDF)
        )
        assert result.error is None

    async def test_result_is_processing_result_instance(
        self,
        service: ProcessingService,
    ) -> None:
        result = await service.process(
            owner_id=_OWNER_ID, request=_make_request(DocumentFormat.PDF)
        )
        assert isinstance(result, ProcessingResult)


# ---------------------------------------------------------------------------
# Parser error propagation
# ---------------------------------------------------------------------------


class TestParserErrorPropagation:
    async def test_exception_from_parser_propagates(self) -> None:
        error = RuntimeError("parser blew up")
        parser = FakeParser({DocumentFormat.PDF}, raises=error)
        service = _make_service(parser)

        with pytest.raises(RuntimeError, match="parser blew up"):
            await service.process(owner_id=_OWNER_ID, request=_make_request(DocumentFormat.PDF))

    async def test_value_error_propagates(self) -> None:
        parser = FakeParser({DocumentFormat.DOCX}, raises=ValueError("bad file"))
        service = _make_service(parser)

        with pytest.raises(ValueError, match="bad file"):
            await service.process(owner_id=_OWNER_ID, request=_make_request(DocumentFormat.DOCX))


# ---------------------------------------------------------------------------
# Registry errors surface from service
# ---------------------------------------------------------------------------


class TestRegistryErrors:
    async def test_parser_not_found_propagates(self) -> None:
        writer = AsyncMock()
        writer.write = AsyncMock(return_value=None)
        service = ProcessingService(
            storage=_make_storage(),
            temporary_file_manager=TemporaryFileManager(),
            parser_registry=ParserRegistry(),
            metadata_service=_make_metadata_service(),
            statistics_service=_make_statistics_service(),
            artifact_builder=ArtifactBuilder(),
            artifact_writer=writer,
            chunking_service=_make_chunking_service(),
            chunk_artifact_builder=_make_chunk_artifact_builder(),
            chunk_artifact_writer=_make_chunk_artifact_writer(),
            embedding_service=_make_embedding_service(),
            embedding_artifact_builder=_make_embedding_artifact_builder(),
            embedding_artifact_writer=_make_embedding_artifact_writer(),
        )

        with pytest.raises(ParserNotFoundError):
            await service.process(owner_id=_OWNER_ID, request=_make_request(DocumentFormat.PDF))

    async def test_wrong_format_raises_parser_not_found(self) -> None:
        parser = FakeParser({DocumentFormat.PDF}, result=_make_document())
        service = _make_service(parser)

        with pytest.raises(ParserNotFoundError):
            await service.process(owner_id=_OWNER_ID, request=_make_request(DocumentFormat.DOCX))


# ---------------------------------------------------------------------------
# Format routing: correct parser selected per format
# ---------------------------------------------------------------------------


class TestFormatRouting:
    async def test_pdf_request_routes_to_pdf_parser(self) -> None:
        pdf_doc = _make_document()
        txt_doc = ProcessedDocument(
            document_id=uuid.uuid4(),
            filename="test.txt",
            format=DocumentFormat.TEXT,
            parser=ParserType.DOCLING,
            metadata=DocumentMetadata(),
            statistics=DocumentStatistics(),
            raw_text="text",
            markdown="text",
            blocks=[],
        )
        pdf_parser = FakeParser({DocumentFormat.PDF}, result=pdf_doc)
        txt_parser = FakeParser({DocumentFormat.TEXT}, result=txt_doc)
        service = _make_service(pdf_parser, txt_parser)

        request = _make_request(DocumentFormat.PDF)
        result = await service.process(owner_id=_OWNER_ID, request=request)
        expected = pdf_doc.model_copy(
            update={"document_id": request.document_id, "filename": request.filename}
        )
        assert result.document == expected
        assert pdf_parser.call_count == 1
        assert txt_parser.call_count == 0

    async def test_text_request_routes_to_text_parser(self) -> None:
        txt_doc = ProcessedDocument(
            document_id=uuid.uuid4(),
            filename="test.txt",
            format=DocumentFormat.TEXT,
            parser=ParserType.DOCLING,
            metadata=DocumentMetadata(),
            statistics=DocumentStatistics(),
            raw_text="text",
            markdown="text",
            blocks=[],
        )
        pdf_parser = FakeParser({DocumentFormat.PDF}, result=_make_document())
        txt_parser = FakeParser({DocumentFormat.TEXT}, result=txt_doc)
        service = _make_service(pdf_parser, txt_parser)

        request = _make_request(DocumentFormat.TEXT)
        result = await service.process(owner_id=_OWNER_ID, request=request)
        expected = txt_doc.model_copy(
            update={"document_id": request.document_id, "filename": request.filename}
        )
        assert result.document == expected
        assert txt_parser.call_count == 1
        assert pdf_parser.call_count == 0

    async def test_sequential_requests_each_resolve_correctly(self) -> None:
        pdf_doc = _make_document()
        txt_doc = ProcessedDocument(
            document_id=uuid.uuid4(),
            filename="test.txt",
            format=DocumentFormat.TEXT,
            parser=ParserType.DOCLING,
            metadata=DocumentMetadata(),
            statistics=DocumentStatistics(),
            raw_text="",
            markdown="",
            blocks=[],
        )
        pdf_parser = FakeParser({DocumentFormat.PDF}, result=pdf_doc)
        txt_parser = FakeParser({DocumentFormat.TEXT}, result=txt_doc)
        service = _make_service(pdf_parser, txt_parser)

        pdf_request = _make_request(DocumentFormat.PDF)
        txt_request = _make_request(DocumentFormat.TEXT)
        r1 = await service.process(owner_id=_OWNER_ID, request=pdf_request)
        r2 = await service.process(owner_id=_OWNER_ID, request=txt_request)

        expected_pdf = pdf_doc.model_copy(
            update={"document_id": pdf_request.document_id, "filename": pdf_request.filename}
        )
        expected_txt = txt_doc.model_copy(
            update={"document_id": txt_request.document_id, "filename": txt_request.filename}
        )
        assert r1.document == expected_pdf
        assert r2.document == expected_txt
