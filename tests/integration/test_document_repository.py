import uuid

import pytest
from app.models.document import Document
from app.models.enums import DocumentUploadStatus
from app.models.project import Project
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


def _make_document(
    *,
    owner_id: uuid.UUID,
    checksum: str,
    filename: str = "a.pdf",
    project_id: uuid.UUID | None = None,
) -> Document:
    return Document(
        owner_id=owner_id,
        project_id=project_id,
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


@pytest.mark.asyncio
async def test_list_by_owner_page_omitted_project_id_returns_personal_only(
    db_session,
) -> None:
    """The omit=personal-only contract: no `project_id` arg means only
    documents with `project_id IS NULL`, not "every project" -- mirrors
    ConversationRepository.list_conversations_page's identical contract."""

    owner_id = await _make_owner(db_session)
    project = Project(owner_id=owner_id, name="X")
    db_session.add(project)
    await db_session.flush()
    repository = DocumentRepository(db_session)

    personal = await repository.create(_make_document(owner_id=owner_id, checksum="personal-doc"))
    await repository.create(
        _make_document(owner_id=owner_id, checksum="project-doc", project_id=project.id)
    )

    documents, total = await repository.list_by_owner_page(owner_id, limit=10, offset=0)

    assert total == 1
    assert [d.id for d in documents] == [personal.id]


@pytest.mark.asyncio
async def test_list_by_owner_page_scopes_to_the_given_project(db_session) -> None:
    owner_id = await _make_owner(db_session)
    project_x = Project(owner_id=owner_id, name="X")
    project_y = Project(owner_id=owner_id, name="Y")
    db_session.add_all([project_x, project_y])
    await db_session.flush()
    repository = DocumentRepository(db_session)

    doc_x = await repository.create(
        _make_document(owner_id=owner_id, checksum="doc-x", project_id=project_x.id)
    )
    await repository.create(
        _make_document(owner_id=owner_id, checksum="doc-y", project_id=project_y.id)
    )
    await repository.create(_make_document(owner_id=owner_id, checksum="doc-personal"))

    documents, total = await repository.list_by_owner_page(
        owner_id, limit=10, offset=0, project_id=project_x.id
    )

    assert total == 1
    assert [d.id for d in documents] == [doc_x.id]


@pytest.mark.asyncio
async def test_get_by_ids_for_owner_returns_only_matching_documents(db_session) -> None:
    """ "@document" mentioning: silently drops ids belonging to another
    owner or that don't exist -- the caller (ResearchService) is what
    turns "fewer than requested" into a not-found error."""

    owner_id = await _make_owner(db_session)
    other_owner_id = await _make_owner(db_session)
    repository = DocumentRepository(db_session)

    mine = await repository.create(_make_document(owner_id=owner_id, checksum="mine"))
    theirs = await repository.create(_make_document(owner_id=other_owner_id, checksum="theirs"))

    result = await repository.get_by_ids_for_owner(
        [mine.id, theirs.id, uuid.uuid4()], owner_id=owner_id
    )

    assert [d.id for d in result] == [mine.id]


@pytest.mark.asyncio
async def test_get_by_ids_for_owner_with_no_ids_returns_empty(db_session) -> None:
    owner_id = await _make_owner(db_session)
    repository = DocumentRepository(db_session)

    result = await repository.get_by_ids_for_owner([], owner_id=owner_id)

    assert result == []


@pytest.mark.asyncio
async def test_delete_removes_the_document(db_session) -> None:
    owner_id = await _make_owner(db_session)
    repository = DocumentRepository(db_session)

    document = await repository.create(_make_document(owner_id=owner_id, checksum="to-delete"))

    await repository.delete(document)
    await db_session.flush()

    result = await repository.get_by_id(document.id)
    assert result is None
