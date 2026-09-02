"""
Integration tests for DELETE /api/v1/documents/{document_id}.

Covers:
- Requires authentication (401 without a bearer token)
- Deletes an owned document's Qdrant vectors, S3 artifacts, and Postgres
  row, in that order, and returns 204
- 404s for an unknown document id or one owned by another user, without
  touching Qdrant/S3/Postgres
- A Qdrant or S3 failure leaves the Postgres row untouched (repository
  delete never reached) rather than silently losing external state

DocumentRepository/VectorStoreService/DocumentStorage/the session are all
faked at the route boundary (like `_FakeResearchService` in
test_research_api.py) rather than run against a live Qdrant/S3/Postgres.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.api.v1.documents import delete_document
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.dependencies import get_document_repository, get_vectorstore_service
from app.dependencies.upload import get_document_storage
from app.main import app
from app.models.user import User
from fastapi.testclient import TestClient

_OWNER_ID = uuid.uuid4()


def _fake_user() -> User:
    return User(
        id=_OWNER_ID,
        auth_provider="test",
        provider_user_id=str(_OWNER_ID),
        email="owner@example.com",
    )


def _fake_document(*, owner_id: uuid.UUID = _OWNER_ID) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), owner_id=owner_id)


def _install_fakes(
    *,
    document: SimpleNamespace | None,
    collection_exists: bool = True,
    delete_document_side_effect: Exception | None = None,
    list_keys_side_effect: Exception | None = None,
) -> dict[str, AsyncMock]:
    repository = AsyncMock()
    repository.get_by_id = AsyncMock(return_value=document)
    repository.delete = AsyncMock()

    vectorstore_service = AsyncMock()
    vectorstore_service.collection_exists = AsyncMock(return_value=collection_exists)
    vectorstore_service.delete_document = AsyncMock(side_effect=delete_document_side_effect)

    storage = AsyncMock()
    storage.list_keys = AsyncMock(
        side_effect=list_keys_side_effect,
        return_value=["documents/owner/doc/original.pdf", "documents/owner/doc/parsed.md"],
    )
    storage.delete = AsyncMock()

    session = AsyncMock()

    app.dependency_overrides[get_document_repository] = lambda: repository
    app.dependency_overrides[get_vectorstore_service] = lambda: vectorstore_service
    app.dependency_overrides[get_document_storage] = lambda: storage
    app.dependency_overrides[get_db] = lambda: session

    return {
        "repository": repository,
        "vectorstore_service": vectorstore_service,
        "storage": storage,
        "session": session,
    }


def _teardown_fakes() -> None:
    del app.dependency_overrides[get_document_repository]
    del app.dependency_overrides[get_vectorstore_service]
    del app.dependency_overrides[get_document_storage]
    del app.dependency_overrides[get_db]


def test_delete_document_requires_authentication(client: TestClient) -> None:
    response = client.delete(f"/api/v1/documents/{uuid.uuid4()}")

    assert response.status_code == 401


def test_delete_document_removes_vectors_files_and_row(client: TestClient) -> None:
    document = _fake_document()
    fakes = _install_fakes(document=document)
    app.dependency_overrides[get_current_user] = _fake_user

    try:
        response = client.delete(f"/api/v1/documents/{document.id}")
    finally:
        del app.dependency_overrides[get_current_user]
        _teardown_fakes()

    assert response.status_code == 204
    fakes["vectorstore_service"].delete_document.assert_awaited_once()
    assert fakes["storage"].delete.await_count == 2
    fakes["repository"].delete.assert_awaited_once_with(document)
    fakes["session"].commit.assert_awaited_once()


def test_delete_document_returns_404_for_an_unknown_document(client: TestClient) -> None:
    fakes = _install_fakes(document=None)
    app.dependency_overrides[get_current_user] = _fake_user

    try:
        response = client.delete(f"/api/v1/documents/{uuid.uuid4()}")
    finally:
        del app.dependency_overrides[get_current_user]
        _teardown_fakes()

    assert response.status_code == 404
    fakes["vectorstore_service"].delete_document.assert_not_awaited()
    fakes["repository"].delete.assert_not_awaited()


def test_delete_document_returns_404_for_another_owners_document(client: TestClient) -> None:
    document = _fake_document(owner_id=uuid.uuid4())
    fakes = _install_fakes(document=document)
    app.dependency_overrides[get_current_user] = _fake_user

    try:
        response = client.delete(f"/api/v1/documents/{document.id}")
    finally:
        del app.dependency_overrides[get_current_user]
        _teardown_fakes()

    assert response.status_code == 404
    fakes["repository"].delete.assert_not_awaited()


def test_delete_document_skips_qdrant_when_the_collection_does_not_exist(
    client: TestClient,
) -> None:
    document = _fake_document()
    fakes = _install_fakes(document=document, collection_exists=False)
    app.dependency_overrides[get_current_user] = _fake_user

    try:
        response = client.delete(f"/api/v1/documents/{document.id}")
    finally:
        del app.dependency_overrides[get_current_user]
        _teardown_fakes()

    assert response.status_code == 204
    fakes["vectorstore_service"].delete_document.assert_not_awaited()
    fakes["repository"].delete.assert_awaited_once()


async def test_delete_document_leaves_the_row_untouched_when_qdrant_fails() -> None:
    """Calls the route function directly rather than through `TestClient`
    -- `TestClient`'s default `raise_server_exceptions=True` re-raises
    past the app's own registered exception handler, which would make
    this indistinguishable from a test bug. Matches this codebase's
    existing convention of asserting failure-path behavior with
    `pytest.raises` at the function/service layer, not through HTTP."""

    document = _fake_document()
    fakes = _install_fakes(
        document=document,
        delete_document_side_effect=RuntimeError("qdrant is down"),
    )

    with pytest.raises(RuntimeError, match="qdrant is down"):
        await delete_document(
            document_id=document.id,
            current_user=_fake_user(),
            repository=fakes["repository"],
            vectorstore_service=fakes["vectorstore_service"],
            storage=fakes["storage"],
            session=fakes["session"],
        )

    fakes["repository"].delete.assert_not_awaited()
    fakes["session"].commit.assert_not_awaited()


async def test_delete_document_leaves_the_row_untouched_when_storage_fails() -> None:
    document = _fake_document()
    fakes = _install_fakes(
        document=document,
        list_keys_side_effect=RuntimeError("s3 is down"),
    )

    with pytest.raises(RuntimeError, match="s3 is down"):
        await delete_document(
            document_id=document.id,
            current_user=_fake_user(),
            repository=fakes["repository"],
            vectorstore_service=fakes["vectorstore_service"],
            storage=fakes["storage"],
            session=fakes["session"],
        )

    fakes["repository"].delete.assert_not_awaited()
    fakes["session"].commit.assert_not_awaited()
