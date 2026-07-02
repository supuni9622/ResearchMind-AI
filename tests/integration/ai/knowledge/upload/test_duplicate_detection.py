"""
Integration tests for duplicate detection during upload.

Exercises the real UploadService, DuplicateDetectionService,
DocumentRepository, and SHA256Hasher against the Postgres test
database. Only the S3 boundary is faked, so we can assert on
whether an upload actually reached "storage".

Covers the duplicate-check test plan:
1. New PDF: new DB row, new S3 object.
2. Same PDF again: no new DB row, no new S3 object, upload is
   rejected with a 409 Conflict identifying the existing document.
3. Renamed file with identical bytes: still detected as a
   duplicate because SHA-256 is content-based, not name-based.
4. Different owners uploading the same bytes: duplicate detection
   is scoped per owner, so both get their own document.
"""

from __future__ import annotations

import io
import uuid
from typing import BinaryIO

import pytest
from app.ai.knowledge.upload.duplicate.service import DuplicateDetectionService
from app.ai.knowledge.upload.service import UploadService
from app.exceptions.base import ConflictException
from app.infrastructure.hashing.sha256 import SHA256Hasher
from app.infrastructure.storage.interfaces import DocumentStorage
from app.models.user import User
from app.repositories.document import DocumentRepository


class InMemoryDocumentStorage(DocumentStorage):
    """Fake DocumentStorage that keeps objects in memory."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.upload_calls: list[str] = []
        self.delete_calls: list[str] = []

    async def upload(self, *, key: str, file: BinaryIO, content_type: str) -> None:
        self.upload_calls.append(key)
        self.objects[key] = file.read()

    async def download(self, *, key: str) -> bytes:
        return self.objects[key]

    async def delete(self, *, key: str) -> None:
        self.delete_calls.append(key)
        self.objects.pop(key, None)

    async def exists(self, *, key: str) -> bool:
        return key in self.objects

    async def generate_presigned_url(self, *, key: str, expires_in: int = 3600) -> str:
        return f"https://fake-storage.test/{key}"


async def _make_owner(session) -> uuid.UUID:
    user = User(
        auth_provider="cognito",
        provider_user_id=str(uuid.uuid4()),
        email=f"{uuid.uuid4()}@example.com",
    )
    session.add(user)
    await session.flush()
    return user.id


def _make_upload_service(session, storage: InMemoryDocumentStorage) -> UploadService:
    repository = DocumentRepository(session)
    return UploadService(
        session=session,
        storage=storage,
        hasher=SHA256Hasher(),
        duplicate_detection_service=DuplicateDetectionService(repository),
        repository=repository,
    )


def _pdf_bytes(content: bytes) -> io.BytesIO:
    return io.BytesIO(b"%PDF-1.4 " + content)


@pytest.mark.asyncio
async def test_new_pdf_creates_document_and_uploads_to_storage(db_session) -> None:
    owner_id = await _make_owner(db_session)
    storage = InMemoryDocumentStorage()
    service = _make_upload_service(db_session, storage)
    repository = DocumentRepository(db_session)

    file_bytes = _pdf_bytes(b"unique content for test 1")
    document = await service.upload(
        owner_id=owner_id,
        filename="A.pdf",
        content_type="application/pdf",
        size_bytes=len(file_bytes.getvalue()),
        file=file_bytes,
    )

    assert document.id is not None
    assert storage.upload_calls == [document.storage_key]
    assert document.storage_key == f"documents/{owner_id}/{document.id}/original.pdf"

    owned_documents = await repository.list_by_owner(owner_id)
    assert len(owned_documents) == 1
    assert owned_documents[0].id == document.id


@pytest.mark.asyncio
async def test_same_pdf_uploaded_twice_is_rejected_as_duplicate(db_session) -> None:
    owner_id = await _make_owner(db_session)
    storage = InMemoryDocumentStorage()
    service = _make_upload_service(db_session, storage)
    repository = DocumentRepository(db_session)

    content = b"unique content for test 2"

    first = await service.upload(
        owner_id=owner_id,
        filename="A.pdf",
        content_type="application/pdf",
        size_bytes=len(content) + 9,
        file=_pdf_bytes(content),
    )

    with pytest.raises(ConflictException) as exc_info:
        await service.upload(
            owner_id=owner_id,
            filename="A.pdf",
            content_type="application/pdf",
            size_bytes=len(content) + 9,
            file=_pdf_bytes(content),
        )

    assert exc_info.value.details == {
        "existing_document_id": str(first.id),
        "filename": first.filename,
    }
    assert storage.upload_calls == [first.storage_key]

    owned_documents = await repository.list_by_owner(owner_id)
    assert len(owned_documents) == 1


@pytest.mark.asyncio
async def test_renamed_file_with_same_bytes_is_still_a_duplicate(db_session) -> None:
    owner_id = await _make_owner(db_session)
    storage = InMemoryDocumentStorage()
    service = _make_upload_service(db_session, storage)
    repository = DocumentRepository(db_session)

    content = b"unique content for test 3"

    original = await service.upload(
        owner_id=owner_id,
        filename="A.pdf",
        content_type="application/pdf",
        size_bytes=len(content) + 9,
        file=_pdf_bytes(content),
    )

    with pytest.raises(ConflictException) as exc_info:
        await service.upload(
            owner_id=owner_id,
            filename="My Notes.pdf",
            content_type="application/pdf",
            size_bytes=len(content) + 9,
            file=_pdf_bytes(content),
        )

    # The rejection references the pre-existing document, not the
    # incoming (renamed) upload.
    details = exc_info.value.details
    assert details is not None
    assert details["existing_document_id"] == str(original.id)
    assert details["filename"] == "A.pdf"
    assert storage.upload_calls == [original.storage_key]

    owned_documents = await repository.list_by_owner(owner_id)
    assert len(owned_documents) == 1


@pytest.mark.asyncio
async def test_same_bytes_across_different_owners_creates_two_documents(db_session) -> None:
    owner_a = await _make_owner(db_session)
    owner_b = await _make_owner(db_session)
    storage = InMemoryDocumentStorage()
    service = _make_upload_service(db_session, storage)
    repository = DocumentRepository(db_session)

    content = b"unique content for test 4"

    document_a = await service.upload(
        owner_id=owner_a,
        filename="A.pdf",
        content_type="application/pdf",
        size_bytes=len(content) + 9,
        file=_pdf_bytes(content),
    )

    document_b = await service.upload(
        owner_id=owner_b,
        filename="A.pdf",
        content_type="application/pdf",
        size_bytes=len(content) + 9,
        file=_pdf_bytes(content),
    )

    assert document_a.id != document_b.id
    assert storage.upload_calls == [document_a.storage_key, document_b.storage_key]

    assert len(await repository.list_by_owner(owner_a)) == 1
    assert len(await repository.list_by_owner(owner_b)) == 1
