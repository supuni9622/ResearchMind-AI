from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.research.checkpointing import postgres_checkpoint_url
from app.ai.runtime.research.lifecycle import transition_run
from app.ai.runtime.research.run_service import ResearchRunService
from app.ai.runtime.research.types import ResearchRunStatus
from app.models.research_run import ResearchRun


def _run(status: ResearchRunStatus = ResearchRunStatus.CREATED) -> ResearchRun:
    return ResearchRun(
        owner_id=uuid4(),
        graph_thread_id=str(uuid4()),
        status=status.value,
    )


def test_transition_records_start_and_terminal_timestamps() -> None:
    run = _run()

    transition_run(run, target=ResearchRunStatus.PLANNING, phase="planning")
    assert run.status == ResearchRunStatus.PLANNING.value
    assert run.started_at is not None

    transition_run(run, target=ResearchRunStatus.RESEARCHING, phase="researching")
    transition_run(run, target=ResearchRunStatus.REVIEWING, phase="reviewing")
    transition_run(run, target=ResearchRunStatus.SYNTHESIZING, phase="synthesizing")
    transition_run(run, target=ResearchRunStatus.COMPLETED, phase="complete")
    assert run.completed_at is not None


def test_terminal_and_invalid_transitions_are_rejected() -> None:
    run = _run()
    with pytest.raises(ValueError, match="Cannot transition"):
        transition_run(run, target=ResearchRunStatus.COMPLETED)

    transition_run(run, target=ResearchRunStatus.CANCELLED)
    with pytest.raises(ValueError, match="Cannot transition"):
        transition_run(run, target=ResearchRunStatus.PLANNING)


def test_failed_run_can_only_transition_to_researching() -> None:
    run = _run(status=ResearchRunStatus.FAILED)

    with pytest.raises(ValueError, match="Cannot transition"):
        transition_run(run, target=ResearchRunStatus.COMPLETED)
    with pytest.raises(ValueError, match="Cannot transition"):
        transition_run(run, target=ResearchRunStatus.PLANNING)

    transition_run(run, target=ResearchRunStatus.RESEARCHING, phase="runtime_retry")
    assert run.status == ResearchRunStatus.RESEARCHING.value


def test_checkpoint_url_uses_psycopg_compatible_scheme() -> None:
    assert postgres_checkpoint_url("postgresql+asyncpg://user:pass@db/research") == (
        "postgresql://user:pass@db/research"
    )


@pytest.mark.asyncio
async def test_idempotency_replays_matching_request_and_rejects_mismatch() -> None:
    existing = _run()
    existing.idempotency_key = "request-1"
    existing.request_fingerprint = "same-request"
    service = ResearchRunService(AsyncMock())
    service._repository.get_by_idempotency_key = AsyncMock(return_value=existing)  # type: ignore[method-assign]

    replayed = await service.create_or_get(
        owner_id=existing.owner_id,
        idempotency_key="request-1",
        request_fingerprint="same-request",
    )
    assert replayed is existing

    with pytest.raises(ValueError, match="reused"):
        await service.create_or_get(
            owner_id=existing.owner_id,
            idempotency_key="request-1",
            request_fingerprint="different-request",
        )
