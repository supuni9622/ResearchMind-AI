from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from app.ai.runtime.research.draft_inspection import (
    PendingDraftUnavailableError,
    ResearchDraftInspectionService,
)
from app.models.research_run import ResearchRun


def _run() -> ResearchRun:
    return ResearchRun(
        id=uuid4(),
        owner_id=uuid4(),
        graph_thread_id=str(uuid4()),
        status="awaiting_approval",
    )


class _FakeCheckpointTuple:
    def __init__(self, channel_values: dict[str, object]) -> None:
        self.checkpoint = {"channel_values": channel_values}


def _draft_dict() -> dict[str, object]:
    return {
        "title": "Report",
        "abstract": "Abstract.",
        "methodology": "Methodology.",
        "findings": [{"heading": "Finding", "content": "Grounded.", "citation_ids": ["S1"]}],
        "discussion": "Discussion.",
        "conclusion": "Conclusion.",
        "citation_ids": ["S1"],
    }


def _evidence_dict() -> dict[str, object]:
    return {"citation_ids": ["S1"], "completed_task_count": 1, "failed_task_count": 0}


def _review_dict() -> dict[str, object]:
    return {"decision": "pass", "citation_integrity_score": 1.0, "completeness_score": 1.0}


def _patch_checkpointer(monkeypatch, checkpoint_tuple: _FakeCheckpointTuple | None) -> None:
    class FakeCheckpointer:
        async def aget_tuple(self, _config: object):
            return checkpoint_tuple

    @asynccontextmanager
    async def fake_checkpointer(_: str):
        yield FakeCheckpointer()

    monkeypatch.setattr(
        "app.ai.runtime.research.draft_inspection.postgres_checkpointer", fake_checkpointer
    )


@pytest.mark.asyncio
async def test_get_pending_draft_returns_the_checkpointed_state(monkeypatch) -> None:
    run = _run()
    _patch_checkpointer(
        monkeypatch,
        _FakeCheckpointTuple(
            {
                "draft": _draft_dict(),
                "evidence_bundle": _evidence_dict(),
                "review": _review_dict(),
            }
        ),
    )
    service = ResearchDraftInspectionService(database_url="postgresql://test")

    pending = await service.get_pending_draft(run)

    assert pending.draft.title == "Report"
    assert pending.evidence.citation_ids == ["S1"]
    assert pending.review.decision.value == "pass"


@pytest.mark.asyncio
async def test_get_pending_draft_raises_when_no_checkpoint_exists(monkeypatch) -> None:
    run = _run()
    _patch_checkpointer(monkeypatch, None)
    service = ResearchDraftInspectionService(database_url="postgresql://test")

    with pytest.raises(PendingDraftUnavailableError, match="no checkpointed graph state"):
        await service.get_pending_draft(run)


@pytest.mark.asyncio
async def test_get_pending_draft_raises_when_the_draft_has_not_synthesized_yet(monkeypatch) -> None:
    run = _run()
    _patch_checkpointer(monkeypatch, _FakeCheckpointTuple({"evidence_bundle": _evidence_dict()}))
    service = ResearchDraftInspectionService(database_url="postgresql://test")

    with pytest.raises(PendingDraftUnavailableError, match="no draft awaiting review"):
        await service.get_pending_draft(run)
