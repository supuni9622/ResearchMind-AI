from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.research.run_service import ResearchRunService
from app.ai.runtime.research.types import ResearchRunStatus
from app.models.research_run import ResearchRun


def _run(*, status: ResearchRunStatus, cancellation_requested: bool = False) -> ResearchRun:
    return ResearchRun(
        id=uuid4(),
        owner_id=uuid4(),
        graph_thread_id=str(uuid4()),
        status=status.value,
        cancellation_requested=cancellation_requested,
    )


@pytest.mark.asyncio
async def test_request_cancellation_flags_a_non_terminal_run() -> None:
    run = _run(status=ResearchRunStatus.RESEARCHING)
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    result = await service.request_cancellation(run_id=run.id, owner_id=run.owner_id)

    assert result is run
    assert run.cancellation_requested is True
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_cancellation_is_a_no_op_for_an_already_terminal_run() -> None:
    run = _run(status=ResearchRunStatus.COMPLETED)
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    result = await service.request_cancellation(run_id=run.id, owner_id=run.owner_id)

    assert result is run
    assert run.cancellation_requested is False
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_request_cancellation_is_idempotent_for_an_already_flagged_run() -> None:
    run = _run(status=ResearchRunStatus.RESEARCHING, cancellation_requested=True)
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    result = await service.request_cancellation(run_id=run.id, owner_id=run.owner_id)

    assert result is run
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_request_cancellation_returns_none_for_an_unknown_or_unowned_run() -> None:
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=None)  # type: ignore[method-assign]

    result = await service.request_cancellation(run_id=uuid4(), owner_id=uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_is_cancellation_requested_reads_through_the_repository() -> None:
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.is_cancellation_requested = AsyncMock(return_value=True)  # type: ignore[method-assign]

    assert await service.is_cancellation_requested(run_id=uuid4()) is True


@pytest.mark.asyncio
async def test_record_report_decision_persists_approval_and_reopens_the_dispatch() -> None:
    run = _run(status=ResearchRunStatus.AWAITING_APPROVAL)
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]
    service._dispatches.reopen = AsyncMock()  # type: ignore[method-assign]

    result = await service.record_report_decision(
        run_id=run.id, owner_id=run.owner_id, approved=True
    )

    assert result is run
    assert run.budget_usage["report_decision"] == {"decision": "approved", "reason": None}
    service._dispatches.reopen.assert_awaited_once_with(run_id=run.id)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_report_decision_persists_rejection_with_a_reason() -> None:
    run = _run(status=ResearchRunStatus.AWAITING_APPROVAL)
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]
    service._dispatches.reopen = AsyncMock()  # type: ignore[method-assign]

    result = await service.record_report_decision(
        run_id=run.id, owner_id=run.owner_id, approved=False, reason="Missing a key citation."
    )

    assert result is run
    assert run.budget_usage["report_decision"] == {
        "decision": "rejected",
        "reason": "Missing a key citation.",
    }


@pytest.mark.asyncio
async def test_record_report_decision_rejects_a_run_not_awaiting_approval() -> None:
    run = _run(status=ResearchRunStatus.RESEARCHING)
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="not awaiting"):
        await service.record_report_decision(run_id=run.id, owner_id=run.owner_id, approved=True)

    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_report_decision_returns_none_for_an_unknown_or_unowned_run() -> None:
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=None)  # type: ignore[method-assign]

    result = await service.record_report_decision(run_id=uuid4(), owner_id=uuid4(), approved=True)

    assert result is None


@pytest.mark.asyncio
async def test_expire_stale_awaiting_approval_cancels_each_stale_run() -> None:
    stale_runs = [
        _run(status=ResearchRunStatus.AWAITING_APPROVAL),
        _run(status=ResearchRunStatus.AWAITING_APPROVAL),
    ]
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.list_stale_awaiting_approval = AsyncMock(  # type: ignore[method-assign]
        return_value=stale_runs
    )
    service._event_journal.publish = AsyncMock()  # type: ignore[method-assign]

    count = await service.expire_stale_awaiting_approval()

    assert count == 2
    for run in stale_runs:
        assert run.status == ResearchRunStatus.CANCELLED.value
        assert run.terminal_reason == "awaiting_approval_expired"
    assert service._event_journal.publish.await_count == 2
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_expire_stale_awaiting_approval_uses_a_custom_ttl_for_the_cutoff() -> None:
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.list_stale_awaiting_approval = AsyncMock(return_value=[])  # type: ignore[method-assign]

    await service.expire_stale_awaiting_approval(older_than_hours=1)

    _, kwargs = service._repository.list_stale_awaiting_approval.call_args
    assert (datetime.now(UTC) - kwargs["older_than"]) < timedelta(hours=1, minutes=1)


@pytest.mark.asyncio
async def test_expire_stale_awaiting_approval_is_a_no_op_when_nothing_is_stale() -> None:
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.list_stale_awaiting_approval = AsyncMock(return_value=[])  # type: ignore[method-assign]

    count = await service.expire_stale_awaiting_approval()

    assert count == 0
    session.commit.assert_awaited_once()
