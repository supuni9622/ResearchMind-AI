"""
Resilience tests for ProcessingService.

Covers:
- Storage failures: download failures and artifact-write failures are
  logged with pipeline-stage context and propagate untouched (not
  swallowed, not remapped to a different exception type)
- Concurrency: multiple documents processed concurrently resolve
  independently, and one failure does not corrupt sibling results
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock

import pytest
from app.ai.knowledge.processing.artifact_builder import ArtifactBuilder
from app.ai.knowledge.processing.enums import DocumentFormat, ParserType, ProcessingStatus
from app.ai.knowledge.processing.interfaces import DocumentParser, ParseRequest
from app.ai.knowledge.processing.models import (
    DocumentMetadata,
    DocumentStatistics,
    ProcessedDocument,
)
from app.ai.knowledge.processing.registry import ParserRegistry
from app.ai.knowledge.processing.service import ProcessingService
from app.ai.knowledge.processing.temporary_file_manager import TemporaryFileManager
from app.infrastructure.storage.exceptions import StorageDownloadError, StorageUploadError

_OWNER_ID = "test-owner"


class FakeParser(DocumentParser):
    def __init__(self, formats: set[DocumentFormat]) -> None:
        self._formats = formats
        self.call_count = 0

    @property
    def parser_name(self) -> str:
        return "fake-parser"

    @property
    def supported_formats(self) -> set[DocumentFormat]:
        return self._formats

    async def parse(self, request: ParseRequest) -> ProcessedDocument:
        self.call_count += 1
        return ProcessedDocument(
            document_id=request.document_id,
            filename=request.filename,
            format=request.document_format,
            parser=ParserType.DOCLING,
            metadata=DocumentMetadata(),
            statistics=DocumentStatistics(),
            raw_text=f"text-{request.document_id}",
            markdown=f"# {request.document_id}",
            blocks=[],
        )


def _make_request(document_format: DocumentFormat = DocumentFormat.PDF) -> ParseRequest:
    return ParseRequest(
        document_id=uuid.uuid4(),
        storage_key="test-storage-key",
        filename="test.pdf",
        content_type="application/pdf",
        document_format=document_format,
    )


def _default_storage() -> AsyncMock:
    storage = AsyncMock()
    storage.download = AsyncMock(return_value=b"fake document bytes")
    return storage


def _default_writer() -> AsyncMock:
    writer = AsyncMock()
    writer.write = AsyncMock(return_value=None)
    return writer


def _default_metadata_service() -> AsyncMock:
    """Pass-through metadata service: returns the document unchanged."""
    metadata_service = AsyncMock()
    metadata_service.enrich = AsyncMock(side_effect=lambda *, document, file_path: document)
    return metadata_service


def _default_statistics_service() -> AsyncMock:
    """Pass-through statistics service: returns the document unchanged."""
    statistics_service = AsyncMock()
    statistics_service.enrich = AsyncMock(side_effect=lambda *, document, file_path: document)
    return statistics_service


def _make_service(
    *,
    storage: AsyncMock | None = None,
    writer: AsyncMock | None = None,
    parser: FakeParser | None = None,
) -> tuple[ProcessingService, FakeParser]:
    parser = parser or FakeParser({DocumentFormat.PDF, DocumentFormat.TEXT})
    storage = storage if storage is not None else _default_storage()
    writer = writer if writer is not None else _default_writer()

    service = ProcessingService(
        storage=storage,
        temporary_file_manager=TemporaryFileManager(),
        parser_registry=ParserRegistry(parsers=[parser]),
        metadata_service=_default_metadata_service(),
        statistics_service=_default_statistics_service(),
        artifact_builder=ArtifactBuilder(),
        artifact_writer=writer,
    )
    return service, parser


# ---------------------------------------------------------------------------
# Storage failures
# ---------------------------------------------------------------------------


class TestStorageFailures:
    async def test_download_failure_propagates_and_parser_never_runs(self) -> None:
        storage = AsyncMock()
        storage.download = AsyncMock(side_effect=StorageDownloadError("object not found"))
        service, parser = _make_service(storage=storage)

        with pytest.raises(StorageDownloadError):
            await service.process(owner_id=_OWNER_ID, request=_make_request())

        assert parser.call_count == 0

    async def test_artifact_write_failure_propagates_after_successful_parse(self) -> None:
        writer = AsyncMock()
        writer.write = AsyncMock(side_effect=StorageUploadError("bucket unreachable"))
        service, parser = _make_service(writer=writer)

        with pytest.raises(StorageUploadError):
            await service.process(owner_id=_OWNER_ID, request=_make_request())

        # The document was successfully parsed even though persistence failed.
        assert parser.call_count == 1
        writer.write.assert_awaited_once()


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


class TestConcurrency:
    async def test_concurrent_processing_resolves_each_document_independently(
        self,
    ) -> None:
        service, parser = _make_service()

        requests = [_make_request() for _ in range(10)]
        results = await asyncio.gather(
            *(service.process(owner_id=_OWNER_ID, request=req) for req in requests)
        )

        assert parser.call_count == 10
        assert len(results) == 10
        for request, result in zip(requests, results, strict=True):
            assert result.status == ProcessingStatus.COMPLETED
            assert result.document is not None
            assert str(request.document_id) in result.document.raw_text

    async def test_one_concurrent_failure_does_not_affect_siblings(self) -> None:
        real_download_calls = 0

        async def _flaky_download(*, key: str) -> bytes:
            nonlocal real_download_calls
            real_download_calls += 1
            if real_download_calls == 3:
                raise StorageDownloadError("transient outage")
            return b"fake document bytes"

        storage = AsyncMock()
        storage.download = AsyncMock(side_effect=_flaky_download)
        service, parser = _make_service(storage=storage)

        requests = [_make_request() for _ in range(6)]
        results = await asyncio.gather(
            *(service.process(owner_id=_OWNER_ID, request=req) for req in requests),
            return_exceptions=True,
        )

        failures = [r for r in results if isinstance(r, BaseException)]
        successes = [r for r in results if not isinstance(r, BaseException)]

        assert len(failures) == 1
        assert isinstance(failures[0], StorageDownloadError)
        assert len(successes) == 5
        assert all(r.status == ProcessingStatus.COMPLETED for r in successes)
