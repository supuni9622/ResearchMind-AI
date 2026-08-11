"""
Integration tests for auth/access-control on the internal eval dashboard
routes (E7, EVALUATION_PLAN.md §16 phase 8).

Covers:
- Requires authentication (401 without a bearer token)
- Requires the caller's email to be on `settings.eval_dashboard_admin_emails`
  (403 otherwise) -- this is the one thing that makes these routes
  different from every other authenticated endpoint in the app
- An allowlisted caller reaches the repository and gets real data back
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from app.auth.dependencies import get_current_user
from app.core.settings import settings
from app.dependencies.eval_score import get_eval_score_repository
from app.dependencies.research import get_research_run_repository
from app.main import app
from app.models.user import User
from app.services.benchmark_reports import list_benchmark_reports
from fastapi.testclient import TestClient

from benchmarks.models.report import BenchmarkCandidate, BenchmarkDataset, BenchmarkReport

_ADMIN_EMAIL = "admin@example.com"
_OWNER_ID = str(uuid.uuid4())


class _FakeEvalScoreRepository:
    async def search_owners_with_scores(self, *, search, limit, offset):  # noqa: ANN001
        return [], 0

    async def list_for_owner_page(self, owner_id, *, metric_name, source, since, limit, offset):  # noqa: ANN001
        return [], 0

    async def search_offline_examples(self, *, search, limit, offset):  # noqa: ANN001
        return [], 0

    async def list_offline_page(self, *, dataset_example_id, metric_name, limit, offset):  # noqa: ANN001
        return [], 0

    async def aggregate_online_by_fingerprint(self, *, metric_name, fingerprint_field):  # noqa: ANN001
        return [("chat-v1", 2, 0.8, 1.0)]

    async def list_offline_scores_for_metric(self, *, metric_name, limit=5000):  # noqa: ANN001
        return []


class _FakeResearchRunRepository:
    async def review_decision_counts_for_owner(self, owner_id):  # noqa: ANN001
        return {"pass": 3, "revise_synthesis": 1}


def _fake_benchmark_report() -> BenchmarkReport:
    return BenchmarkReport(
        benchmark_name="Embeddings",
        dataset=BenchmarkDataset(name="fixtures", document_count=3),
        candidates=[
            BenchmarkCandidate(name="openai", metrics={"throughput_embeddings_per_second": 12.5}),
        ],
    )


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
    app.dependency_overrides[get_eval_score_repository] = lambda: _FakeEvalScoreRepository()
    app.dependency_overrides[get_research_run_repository] = lambda: _FakeResearchRunRepository()
    app.dependency_overrides[list_benchmark_reports] = lambda: [_fake_benchmark_report()]

    original_admin_emails = settings.eval_dashboard_admin_emails
    settings.eval_dashboard_admin_emails = _ADMIN_EMAIL

    yield

    settings.eval_dashboard_admin_emails = original_admin_emails
    app.dependency_overrides.pop(get_eval_score_repository, None)
    app.dependency_overrides.pop(get_research_run_repository, None)
    app.dependency_overrides.pop(list_benchmark_reports, None)
    app.dependency_overrides.pop(get_current_user, None)


def test_owners_route_requires_authentication(
    client: TestClient,
    fake_repositories: None,
) -> None:
    response = client.get("/api/v1/eval-dashboard/owners")

    assert response.status_code == 401


def test_owners_route_rejects_a_non_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as("not-an-admin@example.com")

    response = client.get("/api/v1/eval-dashboard/owners")

    assert response.status_code == 403


def test_owners_route_allows_an_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.get("/api/v1/eval-dashboard/owners")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_admin_email_check_is_case_insensitive(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as(_ADMIN_EMAIL.upper())

    response = client.get("/api/v1/eval-dashboard/owners")

    assert response.status_code == 200


def test_scores_route_rejects_a_non_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as("not-an-admin@example.com")

    response = client.get(
        "/api/v1/eval-dashboard/scores",
        params={"owner_id": _OWNER_ID},
    )

    assert response.status_code == 403


def test_scores_route_allows_an_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.get(
        "/api/v1/eval-dashboard/scores",
        params={"owner_id": _OWNER_ID},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_review_decisions_route_allows_an_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.get(
        "/api/v1/eval-dashboard/review-decisions",
        params={"owner_id": _OWNER_ID},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["counts"] == {"pass": 3, "revise_synthesis": 1}


def test_review_decisions_route_rejects_a_non_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as("not-an-admin@example.com")

    response = client.get(
        "/api/v1/eval-dashboard/review-decisions",
        params={"owner_id": _OWNER_ID},
    )

    assert response.status_code == 403


def test_offline_examples_route_rejects_a_non_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as("not-an-admin@example.com")

    response = client.get("/api/v1/eval-dashboard/offline-examples")

    assert response.status_code == 403


def test_offline_examples_route_allows_an_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.get("/api/v1/eval-dashboard/offline-examples")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_offline_scores_route_rejects_a_non_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as("not-an-admin@example.com")

    response = client.get("/api/v1/eval-dashboard/offline-scores")

    assert response.status_code == 403


def test_offline_scores_route_allows_an_allowlisted_user_with_no_filters(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.get("/api/v1/eval-dashboard/offline-scores")

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_offline_scores_route_does_not_require_an_owner_id(
    client: TestClient,
    fake_repositories: None,
) -> None:
    """The gap this route closes: /scores requires owner_id and offline
    rows have none, so it's a structurally separate endpoint, not just a
    filter on /scores."""

    _authenticate_as(_ADMIN_EMAIL)

    response = client.get(
        "/api/v1/eval-dashboard/offline-scores",
        params={"dataset_example_id": "g14"},
    )

    assert response.status_code == 200


def test_benchmark_reports_route_rejects_a_non_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as("not-an-admin@example.com")

    response = client.get("/api/v1/eval-dashboard/benchmark-reports")

    assert response.status_code == 403


def test_benchmark_reports_route_allows_an_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.get("/api/v1/eval-dashboard/benchmark-reports")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["benchmark_name"] == "Embeddings"
    assert body[0]["candidates"][0]["metrics"]["throughput_embeddings_per_second"] == 12.5


def test_segment_analysis_online_route_rejects_a_non_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as("not-an-admin@example.com")

    response = client.get(
        "/api/v1/eval-dashboard/segment-analysis/online",
        params={"metric_name": "faithfulness", "fingerprint_field": "prompt_version"},
    )

    assert response.status_code == 403


def test_segment_analysis_online_route_allows_an_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.get(
        "/api/v1/eval-dashboard/segment-analysis/online",
        params={"metric_name": "faithfulness", "fingerprint_field": "prompt_version"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == [
        {"fingerprint_value": "chat-v1", "count": 2, "avg_score": 0.8, "pass_rate": 1.0}
    ]


def test_segment_analysis_online_route_rejects_an_unknown_fingerprint_field(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.get(
        "/api/v1/eval-dashboard/segment-analysis/online",
        params={"metric_name": "faithfulness", "fingerprint_field": "not_a_real_field"},
    )

    assert response.status_code == 422


def test_segment_analysis_offline_route_rejects_a_non_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as("not-an-admin@example.com")

    response = client.get(
        "/api/v1/eval-dashboard/segment-analysis/offline",
        params={"metric_name": "faithfulness", "segment_field": "query_type"},
    )

    assert response.status_code == 403


def test_segment_analysis_offline_route_allows_an_allowlisted_user(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.get(
        "/api/v1/eval-dashboard/segment-analysis/offline",
        params={"metric_name": "faithfulness", "segment_field": "query_type"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []


def test_segment_analysis_offline_route_rejects_an_unknown_segment_field(
    client: TestClient,
    fake_repositories: None,
) -> None:
    _authenticate_as(_ADMIN_EMAIL)

    response = client.get(
        "/api/v1/eval-dashboard/segment-analysis/offline",
        params={"metric_name": "faithfulness", "segment_field": "not_a_real_field"},
    )

    assert response.status_code == 422
