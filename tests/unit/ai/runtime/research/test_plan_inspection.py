from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from app.ai.runtime.research.plan_inspection import (
    PendingPlanUnavailableError,
    ResearchPlanInspectionService,
)
from app.models.research_run import ResearchRun


def _run() -> ResearchRun:
    return ResearchRun(
        id=uuid4(),
        owner_id=uuid4(),
        graph_thread_id=str(uuid4()),
        status="awaiting_plan_approval",
    )


class _FakeCheckpointTuple:
    def __init__(self, channel_values: dict[str, object]) -> None:
        self.checkpoint = {"channel_values": channel_values}


def _plan_dict() -> dict[str, object]:
    return {
        "goal": "How does music affect mood?",
        "rewritten_goal": "How does music listening affect mood regulation?",
        "complexity": "moderate",
        "execution_strategy": "decomposed",
        "tasks": [{"task_id": "task_one", "question": "What genres improve mood?"}],
    }


def _evidence_dict() -> dict[str, object]:
    return {"citation_ids": ["S1"], "completed_task_count": 1, "failed_task_count": 0}


def _patch_checkpointer(monkeypatch, checkpoint_tuple: _FakeCheckpointTuple | None) -> None:
    class FakeCheckpointer:
        async def aget_tuple(self, _config: object):
            return checkpoint_tuple

    @asynccontextmanager
    async def fake_checkpointer(_: str):
        yield FakeCheckpointer()

    monkeypatch.setattr(
        "app.ai.runtime.research.plan_inspection.postgres_checkpointer", fake_checkpointer
    )


@pytest.mark.asyncio
async def test_get_pending_plan_returns_the_checkpointed_state(monkeypatch) -> None:
    run = _run()
    _patch_checkpointer(
        monkeypatch,
        _FakeCheckpointTuple({"plan": _plan_dict(), "evidence_bundle": _evidence_dict()}),
    )
    service = ResearchPlanInspectionService(database_url="postgresql://test")

    pending = await service.get_pending_plan(run)

    assert pending.plan.goal == "How does music affect mood?"
    assert pending.plan.rewritten_goal == "How does music listening affect mood regulation?"
    assert pending.evidence.completed_task_count == 1


@pytest.mark.asyncio
async def test_get_pending_plan_raises_when_no_checkpoint_exists(monkeypatch) -> None:
    run = _run()
    _patch_checkpointer(monkeypatch, None)
    service = ResearchPlanInspectionService(database_url="postgresql://test")

    with pytest.raises(PendingPlanUnavailableError, match="no checkpointed graph state"):
        await service.get_pending_plan(run)


@pytest.mark.asyncio
async def test_get_pending_plan_raises_when_evidence_has_not_aggregated_yet(monkeypatch) -> None:
    run = _run()
    _patch_checkpointer(monkeypatch, _FakeCheckpointTuple({"plan": _plan_dict()}))
    service = ResearchPlanInspectionService(database_url="postgresql://test")

    with pytest.raises(PendingPlanUnavailableError, match="no evidence awaiting plan review"):
        await service.get_pending_plan(run)
