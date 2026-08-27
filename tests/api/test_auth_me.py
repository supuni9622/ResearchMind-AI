"""
Tests for `GET /api/v1/auth/me`'s `eval_dashboard_access` field (E7
follow-up) -- presentation-only, drives whether the frontend shows the
internal eval dashboard nav link. The real access gate is
`require_eval_dashboard_access`, covered separately in
`tests/api/test_eval_dashboard.py`.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from app.auth.dependencies import get_current_user
from app.core.settings import settings
from app.main import app
from app.models.user import User
from fastapi.testclient import TestClient

_ADMIN_EMAIL = "admin@example.com"


def _fake_user(*, email: str) -> User:
    return User(
        id=uuid.uuid4(),
        auth_provider="test",
        provider_user_id=email,
        email=email,
    )


@pytest.fixture
def admin_allowlist() -> Iterator[None]:
    original = settings.eval_dashboard_admin_emails
    settings.eval_dashboard_admin_emails = _ADMIN_EMAIL
    yield
    settings.eval_dashboard_admin_emails = original
    app.dependency_overrides.pop(get_current_user, None)


def test_eval_dashboard_access_is_true_for_an_allowlisted_email(
    client: TestClient,
    admin_allowlist: None,
) -> None:
    app.dependency_overrides[get_current_user] = lambda: _fake_user(email=_ADMIN_EMAIL)

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["eval_dashboard_access"] is True


def test_eval_dashboard_access_is_false_for_a_non_allowlisted_email(
    client: TestClient,
    admin_allowlist: None,
) -> None:
    app.dependency_overrides[get_current_user] = lambda: _fake_user(
        email="not-an-admin@example.com"
    )

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["eval_dashboard_access"] is False


def test_eval_dashboard_access_matches_case_insensitively(
    client: TestClient,
    admin_allowlist: None,
) -> None:
    app.dependency_overrides[get_current_user] = lambda: _fake_user(email=_ADMIN_EMAIL.upper())

    response = client.get("/api/v1/auth/me")

    assert response.json()["eval_dashboard_access"] is True
