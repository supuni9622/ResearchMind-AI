"""
Integration tests for how RetrievalError/VectorStoreError/StorageError
surface to the frontend.

All three exception hierarchies are plain `Exception` subclasses, not
`AppException`, so without a dedicated handler they'd fall through to
the generic 500 "An unexpected error occurred." -- correct in that the
app never crashes, but not a meaningful message for the frontend to
show or act on (e.g. distinguishing "your input was invalid" from
"try again in a moment").

Covers:
- RetrievalValidationError -> 400 with a specific error code
- RetrievalProviderNotFoundError -> 500 with a specific error code
  (internal misconfiguration, not user-fixable, but still distinct
  from the generic "INTERNAL_SERVER_ERROR")
- RetrievalExecutionError (a failed Qdrant call) -> 503, signaling a
  transient, retry-worthy failure rather than a hard error
- CollectionOperationError (the vector store's equivalent, raised by
  GET /documents/stats) -> 503
- StorageNotFoundError (a failed S3 `exists()` check during report
  download, e.g. GET /research/runs/{id}/report) -> 503
- The response body always matches ErrorResponse/ErrorDetail, which
  apps/web/src/lib/errors.ts::extractErrorMessage already knows how to
  read -- no frontend change needed, only a more specific `message`
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from app.ai.knowledge.retrieval.exceptions import (
    RetrievalExecutionError,
    RetrievalProviderNotFoundError,
    RetrievalValidationError,
)
from app.ai.knowledge.retrieval.models import RetrievalQuery
from app.ai.knowledge.vectorstores.exceptions import CollectionOperationError
from app.ai.knowledge.vectorstores.service import VectorStoreService
from app.auth.dependencies import get_current_user
from app.dependencies.research import get_research_report_download_service
from app.dependencies.retrieval import get_retrieval_service
from app.dependencies.vector_store import get_vectorstore_service
from app.infrastructure.storage.exceptions import StorageNotFoundError
from app.main import app
from app.models.user import User
from fastapi.testclient import TestClient


def _fake_user() -> User:
    owner_id = str(uuid.uuid4())
    return User(
        id=uuid.UUID(owner_id),
        auth_provider="test",
        provider_user_id=owner_id,
        email=f"{owner_id}@example.com",
    )


@pytest.fixture(autouse=True)
def _authenticated() -> Generator[None, None, None]:
    app.dependency_overrides[get_current_user] = _fake_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


class _RaisingRetrievalService:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def search(self, *, provider, query: RetrievalQuery):
        raise self._exc


@pytest.fixture
def _retrieval_error(request: pytest.FixtureRequest):
    exc = request.param
    service = _RaisingRetrievalService(exc)
    app.dependency_overrides[get_retrieval_service] = lambda: service
    yield exc
    app.dependency_overrides.pop(get_retrieval_service, None)


@pytest.mark.parametrize(
    ("_retrieval_error", "expected_status", "expected_code"),
    [
        (
            RetrievalValidationError("Query cannot be empty."),
            400,
            "RETRIEVAL_VALIDATION_ERROR",
        ),
        (
            RetrievalProviderNotFoundError("Provider 'qdrant' is not registered."),
            500,
            "RETRIEVAL_PROVIDER_NOT_FOUND",
        ),
        (
            RetrievalExecutionError("Dense retrieval failed."),
            503,
            "RETRIEVAL_UNAVAILABLE",
        ),
    ],
    indirect=["_retrieval_error"],
)
def test_retrieval_errors_return_meaningful_responses(
    client: TestClient,
    _retrieval_error: Exception,
    expected_status: int,
    expected_code: str,
) -> None:
    response = client.post(
        "/api/v1/retrieve",
        json={"query": "what is rag?"},
    )

    assert response.status_code == expected_status
    body = response.json()
    assert body["error"]["code"] == expected_code
    # A real, non-generic message -- not "An unexpected error occurred."
    assert body["error"]["message"]
    assert body["error"]["message"] != "An unexpected error occurred."


class _RaisingVectorStoreService:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def collection_exists(self, *, provider, collection_name: str) -> bool:
        return True

    async def count(
        self, *, provider, collection_name: str, owner_id: str, project_id: str | None = None
    ) -> int:
        raise self._exc


def test_vector_store_error_returns_meaningful_response(client: TestClient) -> None:
    service: VectorStoreService = _RaisingVectorStoreService(  # type: ignore[assignment]
        CollectionOperationError("Failed to count vectors in 'researchmind_knowledge'.")
    )
    app.dependency_overrides[get_vectorstore_service] = lambda: service

    try:
        response = client.get("/api/v1/documents/stats")
    finally:
        app.dependency_overrides.pop(get_vectorstore_service, None)

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "VECTOR_STORE_UNAVAILABLE"
    assert body["error"]["message"]
    assert body["error"]["message"] != "An unexpected error occurred."


def test_storage_error_returns_meaningful_response(client: TestClient) -> None:
    report_downloads = AsyncMock()
    report_downloads.get_download_url.side_effect = StorageNotFoundError(
        "Failed to check 'artifacts/research-runs/.../final-report.pdf'."
    )
    app.dependency_overrides[get_research_report_download_service] = lambda: report_downloads

    try:
        response = client.get(f"/api/v1/research/runs/{uuid.uuid4()}/report")
    finally:
        app.dependency_overrides.pop(get_research_report_download_service, None)

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "STORAGE_NOT_FOUND_CHECK_FAILED"
    assert body["error"]["message"]
    assert body["error"]["message"] != "An unexpected error occurred."
