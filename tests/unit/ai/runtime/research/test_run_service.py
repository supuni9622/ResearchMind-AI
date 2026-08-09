from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.research.draft_inspection import PendingDraftSnapshot
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.review import ResearchReview, ReviewDecision
from app.ai.runtime.research.run_service import ResearchRunService
from app.ai.runtime.research.synthesis.models import ResearchDraft, ResearchDraftSection
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


def _pending_draft() -> PendingDraftSnapshot:
    return PendingDraftSnapshot(
        draft=ResearchDraft(
            title="Original title",
            abstract="Original abstract.",
            methodology="Original methodology.",
            findings=[
                ResearchDraftSection(
                    heading="Original heading",
                    content="Original content.",
                    citation_ids=["S1"],
                )
            ],
            discussion="Original discussion.",
            conclusion="Original conclusion.",
            citation_ids=["S1"],
            limitations=["Small sample size."],
        ),
        evidence=ResearchEvidenceBundle(
            citation_ids=["S1"], completed_task_count=1, failed_task_count=0
        ),
        review=ResearchReview(
            decision=ReviewDecision.PASS, citation_integrity_score=1.0, completeness_score=1.0
        ),
    )


@pytest.mark.asyncio
async def test_record_report_decision_merges_an_edited_draft_onto_the_original() -> None:
    run = _run(status=ResearchRunStatus.AWAITING_APPROVAL)
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]
    service._dispatches.reopen = AsyncMock()  # type: ignore[method-assign]
    draft_inspection = AsyncMock()
    draft_inspection.get_pending_draft.return_value = _pending_draft()

    edited_draft = {
        "title": "Edited title",
        "abstract": "Edited abstract.",
        "methodology": "Edited methodology.",
        "findings": [{"heading": "Edited heading", "content": "Edited content."}],
        "discussion": "Edited discussion.",
        "conclusion": "Edited conclusion.",
    }

    result = await service.record_report_decision(
        run_id=run.id,
        owner_id=run.owner_id,
        approved=True,
        edited_draft=edited_draft,
        draft_inspection=draft_inspection,
    )

    assert result is run
    stored = run.budget_usage["report_decision"]["edited_draft"]
    # Edited free-text fields land as given...
    assert stored["title"] == "Edited title"
    assert stored["findings"][0]["heading"] == "Edited heading"
    assert stored["findings"][0]["content"] == "Edited content."
    # ...while fields the reviewer can't edit are carried over from the original,
    # so citation integrity can't be broken by an edit.
    assert stored["citation_ids"] == ["S1"]
    assert stored["findings"][0]["citation_ids"] == ["S1"]
    assert stored["limitations"] == ["Small sample size."]


@pytest.mark.asyncio
async def test_record_report_decision_rejects_an_edited_draft_with_a_different_finding_count() -> (
    None
):
    run = _run(status=ResearchRunStatus.AWAITING_APPROVAL)
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]
    draft_inspection = AsyncMock()
    draft_inspection.get_pending_draft.return_value = _pending_draft()

    edited_draft = {
        "title": "Edited title",
        "abstract": "Edited abstract.",
        "methodology": "Edited methodology.",
        "findings": [
            {"heading": "One", "content": "First."},
            {"heading": "Two", "content": "Second."},
        ],
        "discussion": "Edited discussion.",
        "conclusion": "Edited conclusion.",
    }

    with pytest.raises(ValueError, match="same number of findings"):
        await service.record_report_decision(
            run_id=run.id,
            owner_id=run.owner_id,
            approved=True,
            edited_draft=edited_draft,
            draft_inspection=draft_inspection,
        )

    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_report_decision_ignores_an_edited_draft_on_rejection() -> None:
    """An edit only makes sense alongside approval -- a rejection with a
    (presumably stale, e.g. left over from switching from Approve to
    Reject in the UI) `edited_draft` attached should not need a working
    `draft_inspection` collaborator at all."""

    run = _run(status=ResearchRunStatus.AWAITING_APPROVAL)
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]
    service._dispatches.reopen = AsyncMock()  # type: ignore[method-assign]

    result = await service.record_report_decision(
        run_id=run.id,
        owner_id=run.owner_id,
        approved=False,
        reason="not accurate",
        edited_draft={"title": "should be ignored"},
        draft_inspection=None,
    )

    assert result is run
    assert "edited_draft" not in run.budget_usage["report_decision"]


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
async def test_record_plan_decision_persists_approval_and_reopens_the_dispatch() -> None:
    run = _run(status=ResearchRunStatus.AWAITING_PLAN_APPROVAL)
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]
    service._dispatches.reopen = AsyncMock()  # type: ignore[method-assign]

    result = await service.record_plan_decision(run_id=run.id, owner_id=run.owner_id, approved=True)

    assert result is run
    assert run.budget_usage["plan_decision"] == {"decision": "approved", "reason": None}
    service._dispatches.reopen.assert_awaited_once_with(run_id=run.id)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_plan_decision_persists_an_edited_goal_alongside_approval() -> None:
    run = _run(status=ResearchRunStatus.AWAITING_PLAN_APPROVAL)
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]
    service._dispatches.reopen = AsyncMock()  # type: ignore[method-assign]

    result = await service.record_plan_decision(
        run_id=run.id,
        owner_id=run.owner_id,
        approved=True,
        edited_goal="Focus specifically on classical music.",
    )

    assert result is run
    assert run.budget_usage["plan_decision"] == {
        "decision": "approved",
        "reason": None,
        "edited_plan": {"rewritten_goal": "Focus specifically on classical music."},
    }


@pytest.mark.asyncio
async def test_record_plan_decision_persists_rejection_with_a_reason() -> None:
    run = _run(status=ResearchRunStatus.AWAITING_PLAN_APPROVAL)
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]
    service._dispatches.reopen = AsyncMock()  # type: ignore[method-assign]

    result = await service.record_plan_decision(
        run_id=run.id, owner_id=run.owner_id, approved=False, reason="Evidence looks too thin."
    )

    assert result is run
    assert run.budget_usage["plan_decision"] == {
        "decision": "rejected",
        "reason": "Evidence looks too thin.",
    }


@pytest.mark.asyncio
async def test_record_plan_decision_ignores_an_edited_goal_on_rejection() -> None:
    run = _run(status=ResearchRunStatus.AWAITING_PLAN_APPROVAL)
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]
    service._dispatches.reopen = AsyncMock()  # type: ignore[method-assign]

    result = await service.record_plan_decision(
        run_id=run.id,
        owner_id=run.owner_id,
        approved=False,
        reason="not accurate",
        edited_goal="should be ignored",
    )

    assert result is run
    assert "edited_plan" not in run.budget_usage["plan_decision"]


@pytest.mark.asyncio
async def test_record_plan_decision_rejects_a_run_not_awaiting_plan_approval() -> None:
    run = _run(status=ResearchRunStatus.RESEARCHING)
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="not awaiting"):
        await service.record_plan_decision(run_id=run.id, owner_id=run.owner_id, approved=True)

    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_plan_decision_returns_none_for_an_unknown_or_unowned_run() -> None:
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=None)  # type: ignore[method-assign]

    result = await service.record_plan_decision(run_id=uuid4(), owner_id=uuid4(), approved=True)

    assert result is None


@pytest.mark.asyncio
async def test_retry_run_transitions_a_failed_run_and_reopens_the_dispatch() -> None:
    run = _run(status=ResearchRunStatus.FAILED)
    run.completed_at = datetime.now(UTC)
    run.terminal_reason = "runtime_or_compatibility_bridge_failed"
    run.error_summary = {"type": "RuntimeError", "message": "boom"}
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]
    service._dispatches.reopen = AsyncMock()  # type: ignore[method-assign]

    result = await service.retry_run(run_id=run.id, owner_id=run.owner_id)

    assert result is run
    assert run.status == ResearchRunStatus.RESEARCHING.value
    assert run.retry_count == 1
    assert run.completed_at is None
    assert run.terminal_reason is None
    assert run.error_summary == {}
    service._dispatches.reopen.assert_awaited_once_with(run_id=run.id)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_retry_run_rejects_a_run_that_is_not_failed() -> None:
    run = _run(status=ResearchRunStatus.RESEARCHING)
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="not in a failed state"):
        await service.retry_run(run_id=run.id, owner_id=run.owner_id)

    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_run_rejects_once_the_retry_cap_is_reached() -> None:
    run = _run(status=ResearchRunStatus.FAILED)
    run.retry_count = 2
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=run)  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="exhausted its retry attempts"):
        await service.retry_run(run_id=run.id, owner_id=run.owner_id)

    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_run_returns_none_for_an_unknown_or_unowned_run() -> None:
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.get_by_id_for_owner = AsyncMock(return_value=None)  # type: ignore[method-assign]

    result = await service.retry_run(run_id=uuid4(), owner_id=uuid4())

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
async def test_expire_stale_awaiting_approval_uses_a_distinct_reason_for_plan_approval() -> None:
    stale_run = _run(status=ResearchRunStatus.AWAITING_PLAN_APPROVAL)
    session = AsyncMock()
    service = ResearchRunService(session)
    service._repository.list_stale_awaiting_approval = AsyncMock(  # type: ignore[method-assign]
        return_value=[stale_run]
    )
    service._event_journal.publish = AsyncMock()  # type: ignore[method-assign]

    count = await service.expire_stale_awaiting_approval()

    assert count == 1
    assert stale_run.status == ResearchRunStatus.CANCELLED.value
    assert stale_run.terminal_reason == "awaiting_plan_approval_expired"


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
