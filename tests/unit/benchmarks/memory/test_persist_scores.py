from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from benchmarks.memory.benchmark import score_memory_candidate
from benchmarks.memory.dataset import MemoryEvaluationDataset, MemoryEvaluationQuery
from benchmarks.memory.persist_scores import extract_memory_offline_scores, persist_memory_scores
from benchmarks.memory.results import MemoryCandidateResults, MemoryQueryResult


def _report():  # noqa: ANN202
    dataset = MemoryEvaluationDataset(
        name="test",
        version="1",
        queries=[
            MemoryEvaluationQuery(
                query_id="q1",
                query="query",
                category="exact_recall",
                relevant_memory_ids=["m1"],
                allowed_memory_ids=["m1"],
            )
        ],
    )
    captured = MemoryCandidateResults(
        candidate="candidate",
        version="sha",
        dataset_version="1",
        results=[
            MemoryQueryResult(
                query_id="q1",
                retrieved_memory_ids=["m1"],
                selected_memory_ids=["m1"],
                latency_ms=1,
                selected_tokens=2,
            )
        ],
    )
    return score_memory_candidate(dataset=dataset, captured=captured)


def test_extracts_per_query_scores_for_eval_dashboard() -> None:
    scores = extract_memory_offline_scores(_report())

    assert {(score.query_id, score.metric) for score in scores} == {
        ("q1", "memory_recall_at_5"),
        ("q1", "memory_precision_at_5"),
        ("q1", "memory_mrr"),
        ("q1", "memory_scope_leak_count"),
    }


@pytest.mark.asyncio
async def test_persists_through_existing_offline_eval_repository() -> None:
    repository = MagicMock(record_offline_example=AsyncMock())

    count = await persist_memory_scores(_report(), repository=repository)

    assert count == 4
    assert repository.record_offline_example.await_count == 4
    scope_call = next(
        call
        for call in repository.record_offline_example.await_args_list
        if call.kwargs["metric_name"] == "memory_scope_leak_count"
    )
    assert scope_call.kwargs["passed"] is True
