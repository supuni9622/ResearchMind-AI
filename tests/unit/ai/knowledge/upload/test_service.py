"""
Unit tests for UploadService.

Covers:
- Invalid files: validation rejects before storage/hasher/DB are touched
- Large files: the size boundary is enforced before any I/O happens
- Storage failures: upload failures, DB-persist-after-upload failures, and
  cleanup-itself-fails are all handled without masking the original error
- Concurrency: multiple uploads running concurrently do not share state
  or interfere with one another
"""

from __future__ import annotations

import asyncio
import io
import uuid
from unittest.mock import AsyncMock

import pytest
from app.ai.knowledge.upload.constants import MAX_UPLOAD_SIZE_BYTES
from app.ai.knowledge.upload.duplicate.models import DuplicateCheckResult
from app.ai.knowledge.upload.exceptions import FileTooLargeError, UploadValidationError
from app.ai.knowledge.upload.service import UploadService
from app.exceptions.base import ConflictException
from app.infrastructure.hashing.exceptions import HashingError
from app.infrastructure.storage.exceptions import StorageUploadError
from app.models.document import Document
from app.models.enums import DocumentUploadStatus

_OWNER_ID = uuid.uuid4()


def _make_deps() -> dict[str, AsyncMock]:
    session = AsyncMock()
    storage = AsyncMock()
    hasher = AsyncMock()
    repository = AsyncMock()
    duplicate_detection_service = AsyncMock()
    processing_queue = AsyncMock()

    hasher.hash_file = AsyncMock(return_value="deadbeef")
    storage.upload = AsyncMock(return_value=None)
    storage.delete = AsyncMock(return_value=None)
    duplicate_detection_service.check = AsyncMock(
        return_value=DuplicateCheckResult(is_duplicate=False),
    )
    processing_queue.enqueue = AsyncMock(return_value=None)

    async def _create(document):
        return document

    repository.create = AsyncMock(side_effect=_create)

    return {
        "session": session,
        "storage": storage,
        "hasher": hasher,
        "repository": repository,
        "duplicate_detection_service": duplicate_detection_service,
        "processing_queue": processing_queue,
    }


def _make_service(deps: dict[str, AsyncMock]) -> UploadService:
    return UploadService(
        session=deps["session"],
        storage=deps["storage"],
        hasher=deps["hasher"],
        repository=deps["repository"],
        duplicate_detection_service=deps["duplicate_detection_service"],
        processing_queue=deps["processing_queue"],
    )


def _upload_kwargs(**overrides: object) -> dict:
    kwargs = {
        "owner_id": _OWNER_ID,
        "filename": "report.pdf",
        "content_type": "application/pdf",
        "size_bytes": 1024,
        "file": io.BytesIO(b"%PDF-1.4 fake pdf bytes"),
    }
    kwargs.update(overrides)
    return kwargs


# ---------------------------------------------------------------------------
# Invalid files
# ---------------------------------------------------------------------------


class TestInvalidFilesRejectedBeforeIO:
    async def test_unsupported_extension_raises_and_touches_nothing(self) -> None:
        deps = _make_deps()
        service = _make_service(deps)

        with pytest.raises(UploadValidationError):
            await service.upload(**_upload_kwargs(filename="malware.exe"))

        deps["hasher"].hash_file.assert_not_called()
        deps["storage"].upload.assert_not_called()
        deps["repository"].create.assert_not_called()
        deps["session"].commit.assert_not_called()

    async def test_empty_file_raises_and_touches_nothing(self) -> None:
        deps = _make_deps()
        service = _make_service(deps)

        with pytest.raises(UploadValidationError):
            await service.upload(**_upload_kwargs(size_bytes=0))

        deps["storage"].upload.assert_not_called()

    async def test_blank_filename_raises_and_touches_nothing(self) -> None:
        deps = _make_deps()
        service = _make_service(deps)

        with pytest.raises(UploadValidationError):
            await service.upload(**_upload_kwargs(filename="   "))

        deps["storage"].upload.assert_not_called()


# ---------------------------------------------------------------------------
# Large files
# ---------------------------------------------------------------------------


class TestLargeFiles:
    async def test_file_over_max_size_rejected_before_hashing(self) -> None:
        deps = _make_deps()
        service = _make_service(deps)

        with pytest.raises(FileTooLargeError):
            await service.upload(
                **_upload_kwargs(size_bytes=MAX_UPLOAD_SIZE_BYTES + 1),
            )

        deps["hasher"].hash_file.assert_not_called()
        deps["storage"].upload.assert_not_called()

    async def test_file_at_max_size_is_accepted(self) -> None:
        deps = _make_deps()
        service = _make_service(deps)

        document = await service.upload(
            **_upload_kwargs(size_bytes=MAX_UPLOAD_SIZE_BYTES),
        )

        assert document.size_bytes == MAX_UPLOAD_SIZE_BYTES
        deps["storage"].upload.assert_awaited_once()


# ---------------------------------------------------------------------------
# Storage failures
# ---------------------------------------------------------------------------


class TestStorageFailures:
    async def test_hashing_failure_never_touches_storage(self) -> None:
        deps = _make_deps()
        deps["hasher"].hash_file = AsyncMock(side_effect=HashingError("disk read error"))
        service = _make_service(deps)

        with pytest.raises(HashingError):
            await service.upload(**_upload_kwargs())

        deps["storage"].upload.assert_not_called()
        deps["session"].rollback.assert_awaited_once()

    async def test_storage_upload_failure_does_not_attempt_cleanup(self) -> None:
        """
        If storage.upload() itself raises, no object was ever created in
        storage, so cleanup must not fire a delete for a key that was
        never written.
        """
        deps = _make_deps()
        deps["storage"].upload = AsyncMock(side_effect=StorageUploadError("S3 unavailable"))
        service = _make_service(deps)

        with pytest.raises(StorageUploadError):
            await service.upload(**_upload_kwargs())

        deps["storage"].delete.assert_not_called()
        deps["repository"].create.assert_not_called()
        deps["session"].rollback.assert_awaited_once()

    async def test_db_persist_failure_after_successful_upload_cleans_up_storage(
        self,
    ) -> None:
        """
        If the object was uploaded to storage but the DB insert then fails,
        the orphaned storage object must be cleaned up.
        """
        deps = _make_deps()
        deps["repository"].create = AsyncMock(side_effect=RuntimeError("db unavailable"))
        service = _make_service(deps)

        with pytest.raises(RuntimeError, match="db unavailable"):
            await service.upload(**_upload_kwargs())

        deps["storage"].upload.assert_awaited_once()
        deps["storage"].delete.assert_awaited_once()
        deps["session"].rollback.assert_awaited_once()

    async def test_cleanup_failure_does_not_mask_original_error(self) -> None:
        """
        If the compensating storage.delete() itself fails, the original
        failure (not the cleanup failure) must still propagate.
        """
        deps = _make_deps()
        deps["repository"].create = AsyncMock(side_effect=RuntimeError("db unavailable"))
        deps["storage"].delete = AsyncMock(side_effect=StorageUploadError("delete also failed"))
        service = _make_service(deps)

        with pytest.raises(RuntimeError, match="db unavailable"):
            await service.upload(**_upload_kwargs())

        deps["storage"].delete.assert_awaited_once()

    async def test_commit_failure_triggers_cleanup(self) -> None:
        deps = _make_deps()
        deps["session"].commit = AsyncMock(side_effect=RuntimeError("commit failed"))
        service = _make_service(deps)

        with pytest.raises(RuntimeError, match="commit failed"):
            await service.upload(**_upload_kwargs())

        deps["storage"].delete.assert_awaited_once()
        deps["session"].rollback.assert_awaited_once()


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


class TestConcurrency:
    async def test_concurrent_uploads_generate_independent_storage_keys(self) -> None:
        deps = _make_deps()
        service = _make_service(deps)

        results = await asyncio.gather(
            *(
                service.upload(
                    **_upload_kwargs(
                        filename=f"file-{i}.pdf",
                        file=io.BytesIO(f"content-{i}".encode()),
                    )
                )
                for i in range(10)
            )
        )

        document_ids = {doc.id for doc in results}
        storage_keys = {doc.storage_key for doc in results}

        assert len(document_ids) == 10
        assert len(storage_keys) == 10
        assert deps["storage"].upload.await_count == 10
        assert deps["repository"].create.await_count == 10

    async def test_one_failure_among_concurrent_uploads_does_not_affect_others(
        self,
    ) -> None:
        """
        One request with an invalid file must fail on its own without
        corrupting or blocking the sibling requests running concurrently.
        """
        deps = _make_deps()
        service = _make_service(deps)

        async def _upload(*, valid: bool, index: int):
            return await service.upload(
                **_upload_kwargs(
                    filename=f"doc-{index}.pdf" if valid else f"bad-{index}.exe",
                    file=io.BytesIO(f"content-{index}".encode()),
                )
            )

        tasks = [_upload(valid=(i != 2), index=i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        failures = [r for r in results if isinstance(r, BaseException)]
        successes = [r for r in results if not isinstance(r, BaseException)]

        assert len(failures) == 1
        assert isinstance(failures[0], UploadValidationError)
        assert len(successes) == 4
        assert len({doc.id for doc in successes}) == 4


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


def _existing_document() -> Document:
    return Document(
        id=uuid.uuid4(),
        owner_id=_OWNER_ID,
        filename="original.pdf",
        storage_key="documents/owner/doc/original.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        checksum="deadbeef",
        upload_status=DocumentUploadStatus.COMPLETED,
    )


class TestDuplicateDetection:
    async def test_duplicate_raises_conflict_and_never_touches_storage_or_db(self) -> None:
        deps = _make_deps()
        existing = _existing_document()
        deps["duplicate_detection_service"].check = AsyncMock(
            return_value=DuplicateCheckResult(is_duplicate=True, document=existing),
        )
        service = _make_service(deps)

        with pytest.raises(ConflictException) as exc_info:
            await service.upload(**_upload_kwargs())

        assert exc_info.value.details == {
            "existing_document_id": str(existing.id),
            "filename": existing.filename,
        }
        deps["storage"].upload.assert_not_called()
        deps["repository"].create.assert_not_called()
        deps["session"].rollback.assert_not_called()
