from __future__ import annotations

from pathlib import Path

import pytest

from benchmarks.memory.benchmark import score_memory_candidate
from benchmarks.memory.dataset import (
    MemoryEvaluationDataset,
    MemoryEvaluationQuery,
    load_memory_evaluation_dataset,
)
from benchmarks.memory.results import MemoryCandidateResults, MemoryQueryResult


def _dataset() -> MemoryEvaluationDataset:
    return MemoryEvaluationDataset(
        name="memory-test",
        version="1",
        queries=[
            MemoryEvaluationQuery(
                query_id="project-a",
                query="project facts",
                category="project_isolation",
                relevant_memory_ids=["a"],
                allowed_memory_ids=["a", "personal"],
                stale_memory_ids=["stale"],
                contradictory_memory_ids=["old"],
                unsafe_memory_ids=["injection"],
            ),
            MemoryEvaluationQuery(
                query_id="empty",
                query="unrelated",
                category="no_relevant_memory",
                relevant_memory_ids=[],
                allowed_memory_ids=["personal"],
            ),
        ],
    )


def _results() -> MemoryCandidateResults:
    return MemoryCandidateResults(
        candidate="candidate",
        version="abc",
        dataset_version="1",
        results=[
            MemoryQueryResult(
                query_id="project-a",
                retrieved_memory_ids=["a"],
                selected_memory_ids=["a"],
                latency_ms=10,
                selected_tokens=12,
            ),
            MemoryQueryResult(
                query_id="empty",
                retrieved_memory_ids=[],
                selected_memory_ids=[],
                latency_ms=20,
                selected_tokens=0,
            ),
        ],
    )


def test_scores_quality_safety_scope_and_budget_metrics() -> None:
    report = score_memory_candidate(dataset=_dataset(), captured=_results())

    candidate = report.candidates[0]
    assert candidate.metrics["recall_at_5"] == 1
    assert candidate.metrics["mrr"] == 1
    assert candidate.metrics["scope_leak_rate"] == 0
    assert candidate.metrics["unsafe_memory_injection_rate"] == 0
    assert candidate.metrics["avg_latency_ms"] == 15
    assert candidate.metrics["avg_selected_tokens"] == 6
    assert candidate.notes["per_query"]["project-a"]["scope_leak_count"] == 0


def test_scope_leak_and_unsafe_selection_are_visible() -> None:
    results = _results()
    results.results[0].retrieved_memory_ids.append("project-b-secret")
    results.results[0].selected_memory_ids.append("injection")

    metrics = score_memory_candidate(dataset=_dataset(), captured=results).candidates[0].metrics

    assert float(metrics["scope_leak_rate"]) > 0
    assert float(metrics["unsafe_memory_injection_rate"]) > 0


def test_rejects_missing_or_mismatched_results() -> None:
    results = _results()
    results.results.pop()
    with pytest.raises(ValueError, match="must match dataset exactly"):
        score_memory_candidate(dataset=_dataset(), captured=results)

    results = _results().model_copy(update={"dataset_version": "other"})
    with pytest.raises(ValueError, match="does not match"):
        score_memory_candidate(dataset=_dataset(), captured=results)


def test_seed_dataset_is_valid_and_versioned() -> None:
    root = Path(__file__).resolve().parents[4]
    dataset = load_memory_evaluation_dataset(root / "benchmarks/datasets/memory/v1/dataset.json")

    assert dataset.version == "1.1.0"
    assert {query.category for query in dataset.queries} >= {
        "exact_recall",
        "semantic_recall",
        "contradictory_preference",
        "stale_fact",
        "no_relevant_memory",
        "project_isolation",
        "owner_isolation",
        "prompt_injection_shaped_memory",
    }
