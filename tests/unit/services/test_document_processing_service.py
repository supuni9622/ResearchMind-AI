"""
Unit tests for DocumentProcessingService.

Covers:
- Happy path: PROCESSING then COMPLETED are both persisted (flushed AND
  committed) via the session
- Storage/processing failures: FAILED status and the error message are
  persisted, and the original exception still propagates so callers
  (e.g. the upload endpoint) can catch it without the request crashing
- A failure to persist the FAILED status itself is caught, logged, and
  does not replace or hide the original processing error
- Concurrency: multiple documents processed concurrently each reach the
  correct terminal status independently
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock

import pytest
from app.ai.knowledge.processing.enums import DocumentFormat
from app.ai.knowledge.processing.interfaces import ParseRequest
from app.ai.knowledge.processing.models import ProcessingResult
from app.infrastructure.storage.exceptions import StorageDownloadError
from app.models.document import Document
from app.models.enums import DocumentProcessingStatus, DocumentUploadStatus
from app.services.document_processing_service import DocumentProcessingService


def _make_document() -> Document:
    return Document(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        filename="report.pdf",
        storage_key=f"documents/{uuid.uuid4()}/original.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        checksum="deadbeef",
        upload_status=DocumentUploadStatus.COMPLETED,
        processing_status=DocumentProcessingStatus.PENDING,
    )


def _make_request(document: Document) -> ParseRequest:
    return ParseRequest(
        document_id=document.id,
        storage_key=document.storage_key,
        filename=document.filename,
        content_type=document.content_type,
        document_format=DocumentFormat.PDF,
    )


def _make_service(
    *,
    processing_service: AsyncMock,
    repository: AsyncMock | None = None,
    session: AsyncMock | None = None,
) -> tuple[DocumentProcessingService, AsyncMock, AsyncMock]:
    if repository is None:
        repository = AsyncMock()
        repository.update = AsyncMock(side_effect=lambda document: document)

    session = session or AsyncMock()

    service = DocumentProcessingService(
        processing_service=processing_service,
        document_repository=repository,
        session=session,
    )
    return service, repository, session


# ---------------------------------------------------------------------------
# Happy path: status transitions are actually committed
# ---------------------------------------------------------------------------


class TestHappyPath:
    async def test_status_transitions_to_processing_then_completed(self) -> None:
        document = _make_document()
        expected_result = ProcessingResult(status="completed", document=None)

        processing_service = AsyncMock()
        processing_service.process = AsyncMock(return_value=expected_result)

        service, repository, session = _make_service(processing_service=processing_service)

        result = await service.process(document, _make_request(document))

        assert result is expected_result
        assert document.processing_status == DocumentProcessingStatus.COMPLETED
        assert document.processing_error is None
        assert document.processed_at is not None

        # Both the PROCESSING and COMPLETED transitions must be committed,
        # not just flushed, or the status is lost when the request-scoped
        # session closes.
        assert session.commit.await_count == 2
        assert repository.update.await_count == 2

    async def test_completed_document_clears_previous_error(self) -> None:
        document = _make_document()
        document.processing_error = "previous failure"

        processing_service = AsyncMock()
        processing_service.process = AsyncMock(
            return_value=ProcessingResult(status="completed", document=None)
        )

        service, _, _ = _make_service(processing_service=processing_service)
        await service.process(document, _make_request(document))

        assert document.processing_error is None


# ---------------------------------------------------------------------------
# Storage / processing failures
# ---------------------------------------------------------------------------


class TestFailureHandling:
    async def test_storage_failure_marks_document_failed_and_persists_error(
        self,
    ) -> None:
        document = _make_document()

        processing_service = AsyncMock()
        processing_service.process = AsyncMock(
            side_effect=StorageDownloadError("object not found in S3")
        )

        service, repository, session = _make_service(processing_service=processing_service)

        with pytest.raises(StorageDownloadError):
            await service.process(document, _make_request(document))

        assert document.processing_status == DocumentProcessingStatus.FAILED
        assert document.processing_error == "object not found in S3"

        # PROCESSING commit + FAILED commit.
        assert session.commit.await_count == 2
        assert repository.update.await_count == 2

    async def test_long_error_message_is_truncated(self) -> None:
        document = _make_document()

        processing_service = AsyncMock()
        processing_service.process = AsyncMock(side_effect=RuntimeError("x" * 5000))

        service, _, _ = _make_service(processing_service=processing_service)

        with pytest.raises(RuntimeError):
            await service.process(document, _make_request(document))

        assert document.processing_error is not None
        assert len(document.processing_error) <= 2000

    async def test_failure_to_persist_failed_status_does_not_hide_original_error(
        self,
    ) -> None:
        """
        If the DB write for the FAILED status itself fails (e.g. the DB is
        down), the *original* processing error must still be the one that
        propagates — not a generic DB error that obscures what really
        happened.
        """
        document = _make_document()

        processing_service = AsyncMock()
        processing_service.process = AsyncMock(
            side_effect=StorageDownloadError("object not found in S3")
        )

        repository = AsyncMock()
        call_count = 0

        async def _flaky_update(doc: Document) -> Document:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("database connection lost")
            return doc

        repository.update = AsyncMock(side_effect=_flaky_update)

        service, _, session = _make_service(
            processing_service=processing_service,
            repository=repository,
        )

        with pytest.raises(StorageDownloadError, match="object not found in S3"):
            await service.process(document, _make_request(document))

        session.rollback.assert_awaited_once()

    async def test_exception_still_propagates_so_upload_request_survives(self) -> None:
        """
        Mirrors production usage: the API route catches processing
        exceptions so a processing failure never fails the upload
        response. This test only asserts the exception propagates out of
        the service — the "upload still succeeds" contract is enforced by
        the caller, exercised here as a smoke check on the pattern.
        """
        document = _make_document()

        processing_service = AsyncMock()
        processing_service.process = AsyncMock(side_effect=RuntimeError("boom"))

        service, _, _ = _make_service(processing_service=processing_service)

        try:
            await service.process(document, _make_request(document))
            raised = False
        except RuntimeError:
            raised = True

        assert raised is True


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


class TestConcurrency:
    async def test_concurrent_processing_of_different_documents_is_independent(
        self,
    ) -> None:
        documents = [_make_document() for _ in range(8)]

        processing_service = AsyncMock()
        processing_service.process = AsyncMock(
            return_value=ProcessingResult(status="completed", document=None)
        )

        service, _, _ = _make_service(processing_service=processing_service)

        await asyncio.gather(*(service.process(doc, _make_request(doc)) for doc in documents))

        assert all(doc.processing_status == DocumentProcessingStatus.COMPLETED for doc in documents)
        assert len({doc.id for doc in documents}) == 8

    async def test_concurrent_processing_mixed_success_and_failure_isolated(
        self,
    ) -> None:
        documents = [_make_document() for _ in range(6)]

        async def _process(*, owner_id: str, request: ParseRequest) -> ProcessingResult:
            # Fail every other document deterministically by document_id parity.
            if int(str(request.document_id).replace("-", ""), 16) % 2 == 0:
                raise StorageDownloadError("simulated outage")
            return ProcessingResult(status="completed", document=None)

        processing_service = AsyncMock()
        processing_service.process = AsyncMock(side_effect=_process)

        service, _, _ = _make_service(processing_service=processing_service)

        results = await asyncio.gather(
            *(service.process(doc, _make_request(doc)) for doc in documents),
            return_exceptions=True,
        )

        for document, result in zip(documents, results, strict=True):
            if isinstance(result, Exception):
                assert document.processing_status == DocumentProcessingStatus.FAILED
            else:
                assert document.processing_status == DocumentProcessingStatus.COMPLETED
