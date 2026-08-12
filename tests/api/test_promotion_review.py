"""
Integration tests for auth/access-control on E10's promotion-review
routes (EVALUATION_PLAN.md §3/§15).

Same `require_eval_dashboard_access` gate as `tests/api/test_eval_dashboard.py`
-- covers 401/403/200 for each route, plus the one piece of real
business logic that lives in the route itself: `confirm` requires
`failure_category` for `direction="failure"` and forbids it for
`direction="good"`.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.auth.dependencies import get_current_user
from app.core.settings import settings
from app.db.session import get_db
from app.dependencies.generation_usage import get_generation_usage_repository
from app.dependencies.promotion_review import get_promotion_review_repository
from app.main import app
from app.models.enums import PromotionCandidateSource
from app.models.user import User
from app.repositories.promotion_review import PromotionCandidate
from fastapi.testclient import TestClient

_ADMIN_EMAIL = "admin@example.com"
_OWNER_ID = uuid.uuid4()
_GENERATION_ID = uuid.uuid4()


class _FakePromotionReviewRepository:
    async def list_good_candidates(self, *, limit, offset):  # noqa: ANN001
        return [
            PromotionCandidate(
                source=PromotionCandidateSource.HUMAN_FEEDBACK,
                owner_id=_OWNER_ID,
                generation_id=_GENERATION_ID,
                reason="thumbs up",
                created_at=datetime.now(UTC),
            )
        ], 1

    async def list_failure_candidates(self, *, limit, offset):  # noqa: ANN001
        return [], 0

    async def list_preference_candidates(self, *, limit, offset):  # noqa: ANN001
        return [
            PromotionCandidate(
                source=PromotionCandidateSource.HUMAN_FEEDBACK,
                owner_id=_OWNER_ID,
                generation_id=_GENERATION_ID,
                reason="not sufficient (classifier: preference)",
                created_at=datetime.now(UTC),
            )
        ], 1

    async def create(self, **kwargs):  # noqa: ANN001, ANN003
        class _Review:
            id = uuid.uuid4()
            source = kwargs["source"]
            direction = kwargs["direction"]
            owner_id = kwargs["owner_id"]
            generation_id = kwargs["generation_id"]
            status = kwargs["status"]
            reviewed_by = kwargs["reviewed_by"]
            reviewed_at = datetime.now(UTC)
            synced = False

        return _Review()


class _FakeGenerationUsageRepository:
    async def get_langsmith_run_id(self, generation_id):  # noqa: ANN001
        return None


def _fake_user(*, email: str) -> User:
    return User(
        id=uuid.uuid4(),
        auth_provider="test",
        provider_user_id=email,
        email=email,
    )


def _authenticate_as(email: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: _fake_user(email=email)


@pytest.fixture
def fake_repositories() -> Iterator[None]:
    app.dependency_overrides[get_promotion_review_repository] = lambda: (
        _FakePromotionReviewRepository()
    )
    app.dependency_overrides[get_generation_usage_repository] = lambda: (
        _FakeGenerationUsageRepository()
    )
    fake_session = MagicMock()
    fake_session.commit = AsyncMock()
    app.dependency_overrides[get_db] = lambda: fake_session

    original_admin_emails = settings.eval_dashboard_admin_emails
    settings.eval_dashboard_admin_emails = _ADMIN_EMAIL

    yield

    settings.eval_dashboard_admin_emails = original_admin_emails
    app.dependency_overrides.pop(get_promotion_review_repository, None)
    app.dependency_overrides.pop(get_generation_usage_repository, None)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


def test_candidates_route_rejects_a_non_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as("not-an-admin@example.com")

    response = client.get(
        "/api/v1/eval-dashboard/promotion-review/candidates", params={"direction": "good"}
    )

    assert response.status_code == 403


def test_candidates_route_allows_an_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.get(
        "/api/v1/eval-dashboard/promotion-review/candidates", params={"direction": "good"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["reason"] == "thumbs up"


def test_candidates_route_allows_preference_direction(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.get(
        "/api/v1/eval-dashboard/promotion-review/candidates", params={"direction": "preference"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert "classifier: preference" in body["items"][0]["reason"]


def test_candidates_route_rejects_an_invalid_direction(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.get(
        "/api/v1/eval-dashboard/promotion-review/candidates", params={"direction": "bogus"}
    )

    assert response.status_code == 422


def test_trace_url_route_requires_authentication(
    client: TestClient, fake_repositories: None
) -> None:
    response = client.get(
        "/api/v1/eval-dashboard/promotion-review/trace-url",
        params={"generation_id": str(_GENERATION_ID)},
    )

    assert response.status_code == 401


def test_trace_url_route_returns_none_when_no_run_id(
    client: TestClient, fake_repositories: None
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.get(
        "/api/v1/eval-dashboard/promotion-review/trace-url",
        params={"generation_id": str(_GENERATION_ID)},
    )

    assert response.status_code == 200
    assert response.json() == {"trace_url": None}


def test_reject_route_rejects_a_non_allowlisted_user(
    client: TestClient, fake_repositories: None
) -> None:
    _authenticate_as("not-an-admin@example.com")

    response = client.post(
        "/api/v1/eval-dashboard/promotion-review/reject",
        json={
            "source": "human_feedback",
            "owner_id": str(_OWNER_ID),
            "generation_id": str(_GENERATION_ID),
        },
    )

    assert response.status_code == 403


def test_reject_route_allows_an_allowlisted_user(
    client: TestClient, fake_repositories: None
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.post(
        "/api/v1/eval-dashboard/promotion-review/reject",
        json={
            "source": "human_feedback",
            "owner_id": str(_OWNER_ID),
            "generation_id": str(_GENERATION_ID),
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def _confirm_payload(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "source": "human_feedback",
        "direction": "good",
        "owner_id": str(_OWNER_ID),
        "generation_id": str(_GENERATION_ID),
        "question": "What is X?",
        "reference_answer": "X is a thing.",
        "contexts": ["X is described here."],
        "reference_context_ids": ["doc.pdf"],
        "expected_citation_ids": ["doc.pdf"],
        "query_type": "factual",
        "difficulty": "easy",
        "workflow": "chat",
    }
    payload.update(overrides)
    return payload


def test_confirm_route_allows_a_good_promotion_without_failure_category(
    client: TestClient, fake_repositories: None
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.post(
        "/api/v1/eval-dashboard/promotion-review/confirm",
        json=_confirm_payload(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"


def test_confirm_route_requires_failure_category_for_failure_direction(
    client: TestClient, fake_repositories: None
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.post(
        "/api/v1/eval-dashboard/promotion-review/confirm",
        json=_confirm_payload(direction="failure"),
    )

    assert response.status_code == 400


def test_confirm_route_rejects_failure_category_on_a_good_promotion(
    client: TestClient, fake_repositories: None
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.post(
        "/api/v1/eval-dashboard/promotion-review/confirm",
        json=_confirm_payload(failure_category="wrong_citation"),
    )

    assert response.status_code == 400


def test_confirm_route_allows_a_failure_promotion_with_failure_category(
    client: TestClient, fake_repositories: None
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.post(
        "/api/v1/eval-dashboard/promotion-review/confirm",
        json=_confirm_payload(direction="failure", failure_category="wrong_citation"),
    )

    assert response.status_code == 200
