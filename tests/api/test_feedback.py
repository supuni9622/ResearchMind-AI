"""
Integration tests for auth and owner scoping on POST /feedback
(EVALUATION_PLAN.md §16 phase 3).

Covers:
- Requires authentication (401 without a bearer token)
- A submission is always scoped to the authenticated user: owner_id
  comes from current_user.id, never from the request body (the schema
  doesn't even accept one)
- Resubmitting for the same generation_id upserts rather than creating
  a second record, matching `Feedback`'s unique constraint
- Invalid payloads (bad rating/surface value) are rejected with 422
  before ever reaching the service
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app.auth.dependencies import get_current_user
from app.dependencies.feedback import get_feedback_service
from app.main import app
from app.models.enums import FeedbackRating, FeedbackSurface
from app.models.feedback import Feedback
from app.models.user import User
from app.services.feedback import FeedbackService
from fastapi.testclient import TestClient

_OWNER_1_ID = str(uuid.uuid4())
_OWNER_2_ID = str(uuid.uuid4())
_GENERATION_ID = str(uuid.uuid4())


class _FakeFeedbackService(FeedbackService):
    """
    Stands in for FeedbackService with an in-memory upsert, so these
    tests don't need a live Postgres instance (see
    `tests/api/test_retrieval_filters.py` for the same convention).
    """

    def __init__(self) -> None:  # no session/repository needed
        self.received_calls: list[dict[str, object]] = []
        self._store: dict[tuple[uuid.UUID, uuid.UUID], Feedback] = {}

    async def submit(
        self,
        *,
        owner_id: uuid.UUID,
        generation_id: uuid.UUID,
        surface: FeedbackSurface,
        rating: FeedbackRating,
        comment: str | None,
    ) -> Feedback:
        self.received_calls.append(
            {
                "owner_id": owner_id,
                "generation_id": generation_id,
                "surface": surface,
                "rating": rating,
                "comment": comment,
            }
        )

        key = (owner_id, generation_id)
        existing = self._store.get(key)

        feedback = Feedback(
            id=existing.id if existing else uuid.uuid4(),
            owner_id=owner_id,
            generation_id=generation_id,
            surface=surface.value,
            rating=rating.value,
            comment=comment,
            created_at=existing.created_at if existing else datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._store[key] = feedback
        return feedback


def _fake_user(owner_id: str) -> User:
    return User(
        id=uuid.UUID(owner_id),
        auth_provider="test",
        provider_user_id=owner_id,
        email=f"{owner_id}@example.com",
    )


def _authenticate_as(owner_id: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: _fake_user(owner_id)


@pytest.fixture
def fake_feedback_service() -> Iterator[_FakeFeedbackService]:
    service = _FakeFeedbackService()
    app.dependency_overrides[get_feedback_service] = lambda: service

    yield service

    app.dependency_overrides.pop(get_feedback_service, None)
    app.dependency_overrides.pop(get_current_user, None)


def _payload(**overrides: object) -> dict[str, object]:
    return {
        "generation_id": _GENERATION_ID,
        "surface": "chat",
        "rating": "down",
        "comment": "cited the wrong paper",
        **overrides,
    }


def test_missing_authentication_returns_401(
    client: TestClient,
    fake_feedback_service: _FakeFeedbackService,
) -> None:
    response = client.post("/api/v1/feedback", json=_payload())

    assert response.status_code == 401
    assert fake_feedback_service.received_calls == []


def test_submission_is_scoped_to_the_authenticated_user(
    client: TestClient,
    fake_feedback_service: _FakeFeedbackService,
) -> None:
    _authenticate_as(_OWNER_1_ID)

    response = client.post("/api/v1/feedback", json=_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["generation_id"] == _GENERATION_ID
    assert body["rating"] == "down"
    assert body["surface"] == "chat"
    assert body["comment"] == "cited the wrong paper"

    assert fake_feedback_service.received_calls[-1]["owner_id"] == uuid.UUID(_OWNER_1_ID)


def test_request_body_has_no_owner_id_field_to_spoof(
    client: TestClient,
    fake_feedback_service: _FakeFeedbackService,
) -> None:
    # Unlike retrieval's `filters.owner_id`, the feedback schema has no
    # owner-identifying field at all -- a client-supplied "owner_id" is
    # simply rejected as an unknown field (model_config extra="forbid").
    _authenticate_as(_OWNER_1_ID)

    response = client.post(
        "/api/v1/feedback",
        json=_payload(owner_id=_OWNER_2_ID),
    )

    assert response.status_code == 422


def test_resubmitting_for_the_same_generation_updates_rather_than_duplicates(
    client: TestClient,
    fake_feedback_service: _FakeFeedbackService,
) -> None:
    _authenticate_as(_OWNER_1_ID)

    first = client.post("/api/v1/feedback", json=_payload(rating="down"))
    second = client.post("/api/v1/feedback", json=_payload(rating="up", comment=None))

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["rating"] == "up"
    assert second.json()["comment"] is None
    assert len(fake_feedback_service.received_calls) == 2


def test_two_owners_rating_the_same_generation_do_not_collide(
    client: TestClient,
    fake_feedback_service: _FakeFeedbackService,
) -> None:
    _authenticate_as(_OWNER_1_ID)
    first = client.post("/api/v1/feedback", json=_payload(rating="down"))

    _authenticate_as(_OWNER_2_ID)
    second = client.post("/api/v1/feedback", json=_payload(rating="up"))

    assert first.json()["id"] != second.json()["id"]


@pytest.mark.parametrize(
    "field,value",
    [("rating", "sideways"), ("surface", "carrier_pigeon")],
)
def test_invalid_enum_values_are_rejected_before_reaching_the_service(
    client: TestClient,
    fake_feedback_service: _FakeFeedbackService,
    field: str,
    value: str,
) -> None:
    _authenticate_as(_OWNER_1_ID)

    response = client.post("/api/v1/feedback", json=_payload(**{field: value}))

    assert response.status_code == 422
    assert fake_feedback_service.received_calls == []
