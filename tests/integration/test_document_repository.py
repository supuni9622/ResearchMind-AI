import uuid

import pytest
from app.models.document import Document
from app.models.enums import DocumentUploadStatus
from app.models.user import User
from app.repositories.document import DocumentRepository


async def _make_owner(session) -> uuid.UUID:
    user = User(
        auth_provider="cognito",
        provider_user_id=str(uuid.uuid4()),
        email=f"{uuid.uuid4()}@example.com",
    )
    session.add(user)
    await session.flush()
    return user.id


def _make_document(*, owner_id: uuid.UUID, checksum: str, filename: str = "a.pdf") -> Document:
    return Document(
        owner_id=owner_id,
        filename=filename,
        storage_key=f"documents/{owner_id}/{uuid.uuid4()}/original.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        checksum=checksum,
        upload_status=DocumentUploadStatus.COMPLETED,
    )


@pytest.mark.asyncio
async def test_find_by_owner_and_hash_returns_none_when_no_match(db_session) -> None:
    owner_id = await _make_owner(db_session)
    repository = DocumentRepository(db_session)

    result = await repository.find_by_owner_and_hash(
        owner_id=owner_id,
        sha256="deadbeef",
    )

    assert result is None


@pytest.mark.asyncio
async def test_find_by_owner_and_hash_returns_matching_document(db_session) -> None:
    owner_id = await _make_owner(db_session)
    repository = DocumentRepository(db_session)

    document = await repository.create(
        _make_document(owner_id=owner_id, checksum="deadbeef"),
    )

    result = await repository.find_by_owner_and_hash(
        owner_id=owner_id,
        sha256="deadbeef",
    )

    assert result is not None
    assert result.id == document.id


@pytest.mark.asyncio
async def test_find_by_owner_and_hash_does_not_raise_when_multiple_rows_match(
    db_session,
) -> None:
    """
    Regression test: (owner_id, checksum) has no DB-level uniqueness
    constraint, so historical/duplicate rows can exist. The lookup
    must resolve to one document instead of raising
    sqlalchemy.exc.MultipleResultsFound.
    """

    owner_id = await _make_owner(db_session)
    repository = DocumentRepository(db_session)

    older = await repository.create(
        _make_document(owner_id=owner_id, checksum="deadbeef", filename="older.pdf"),
    )
    newer = await repository.create(
        _make_document(owner_id=owner_id, checksum="deadbeef", filename="newer.pdf"),
    )

    result = await repository.find_by_owner_and_hash(
        owner_id=owner_id,
        sha256="deadbeef",
    )

    assert result is not None
    assert result.id in {older.id, newer.id}


@pytest.mark.asyncio
async def test_find_by_owner_and_hash_is_scoped_per_owner(db_session) -> None:
    owner_a = await _make_owner(db_session)
    owner_b = await _make_owner(db_session)
    repository = DocumentRepository(db_session)

    await repository.create(
        _make_document(owner_id=owner_a, checksum="deadbeef"),
    )

    result = await repository.find_by_owner_and_hash(
        owner_id=owner_b,
        sha256="deadbeef",
    )

    assert result is None
