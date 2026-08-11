"""Integration tests for `ResearchRunRepository.review_decision_counts_for_owner` (E7)."""

from __future__ import annotations

import uuid

import pytest
from app.models.research_run import ResearchRun
from app.models.user import User
from app.repositories.research_run import ResearchRunRepository


async def _make_owner(session) -> uuid.UUID:
    user = User(
        auth_provider="cognito",
        provider_user_id=str(uuid.uuid4()),
        email=f"{uuid.uuid4()}@example.com",
    )
    session.add(user)
    await session.flush()
    return user.id


def _make_run(*, owner_id: uuid.UUID, review_decision: str | None) -> ResearchRun:
    return ResearchRun(
        owner_id=owner_id,
        graph_thread_id=str(uuid.uuid4()),
        status="completed",
        budget_usage=({"review_decision": review_decision} if review_decision else {}),
    )


@pytest.mark.asyncio
async def test_review_decision_counts_groups_by_decision_value(db_session) -> None:
    owner_id = await _make_owner(db_session)
    db_session.add_all(
        [
            _make_run(owner_id=owner_id, review_decision="pass"),
            _make_run(owner_id=owner_id, review_decision="pass"),
            _make_run(owner_id=owner_id, review_decision="revise_synthesis"),
        ]
    )
    await db_session.flush()

    repository = ResearchRunRepository(db_session)
    counts = await repository.review_decision_counts_for_owner(owner_id)

    assert counts == {"pass": 2, "revise_synthesis": 1}


@pytest.mark.asyncio
async def test_review_decision_counts_excludes_runs_with_no_decision_yet(db_session) -> None:
    owner_id = await _make_owner(db_session)
    db_session.add_all(
        [
            _make_run(owner_id=owner_id, review_decision="pass"),
            _make_run(owner_id=owner_id, review_decision=None),
        ]
    )
    await db_session.flush()

    repository = ResearchRunRepository(db_session)
    counts = await repository.review_decision_counts_for_owner(owner_id)

    assert counts == {"pass": 1}


@pytest.mark.asyncio
async def test_review_decision_counts_is_scoped_to_the_given_owner(db_session) -> None:
    owner_id = await _make_owner(db_session)
    other_owner_id = await _make_owner(db_session)
    db_session.add_all(
        [
            _make_run(owner_id=owner_id, review_decision="pass"),
            _make_run(owner_id=other_owner_id, review_decision="fail"),
        ]
    )
    await db_session.flush()

    repository = ResearchRunRepository(db_session)
    counts = await repository.review_decision_counts_for_owner(owner_id)

    assert counts == {"pass": 1}


@pytest.mark.asyncio
async def test_review_decision_counts_returns_empty_dict_for_an_owner_with_no_runs(
    db_session,
) -> None:
    owner_id = await _make_owner(db_session)

    repository = ResearchRunRepository(db_session)
    counts = await repository.review_decision_counts_for_owner(owner_id)

    assert counts == {}
