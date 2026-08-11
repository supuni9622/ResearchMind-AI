"""Unit tests for `benchmarks.generation.persist_golden_set_scores` (E6)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from benchmarks.generation.golden_set_benchmark import PER_EXAMPLE_SCORES_NOTE_KEY
from benchmarks.generation.persist_golden_set_scores import extract_offline_scores, persist
from benchmarks.models.report import BenchmarkCandidate, BenchmarkDataset, BenchmarkReport


def _report(*, notes: dict[str, object]) -> BenchmarkReport:
    return BenchmarkReport(
        benchmark_name="GoldenSetGeneration",
        dataset=BenchmarkDataset(name="golden", document_count=1),
        candidates=[BenchmarkCandidate(name="groq", metrics={}, notes=notes)],
    )


def test_extract_offline_scores_flattens_every_candidates_entries() -> None:
    report = _report(
        notes={
            PER_EXAMPLE_SCORES_NOTE_KEY: [
                {
                    "example_id": "a1",
                    "metric": "faithfulness",
                    "score": 0.9,
                    "passed": True,
                    "reason": "grounded",
                },
                {
                    "example_id": "a1",
                    "metric": "answer_relevancy",
                    "score": 0.8,
                    "passed": True,
                    "reason": "relevant",
                },
            ]
        }
    )

    entries = extract_offline_scores(report)

    assert [entry.metric for entry in entries] == ["faithfulness", "answer_relevancy"]
    assert all(entry.example_id == "a1" for entry in entries)


def test_extract_offline_scores_drops_error_placeholder_entries() -> None:
    report = _report(
        notes={
            PER_EXAMPLE_SCORES_NOTE_KEY: [
                {
                    "example_id": "a1",
                    "metric": "error",
                    "score": None,
                    "passed": False,
                    "reason": "provider exploded",
                },
                {
                    "example_id": "a2",
                    "metric": "faithfulness",
                    "score": 0.9,
                    "passed": True,
                    "reason": "grounded",
                },
            ]
        }
    )

    entries = extract_offline_scores(report)

    assert len(entries) == 1
    assert entries[0].example_id == "a2"


def test_extract_offline_scores_handles_a_candidate_with_no_notes() -> None:
    report = _report(notes={})

    entries = extract_offline_scores(report)

    assert entries == []


@pytest.mark.asyncio
async def test_persist_writes_one_row_per_extracted_entry() -> None:
    report = _report(
        notes={
            PER_EXAMPLE_SCORES_NOTE_KEY: [
                {
                    "example_id": "a1",
                    "metric": "faithfulness",
                    "score": 0.9,
                    "passed": True,
                    "reason": "grounded",
                },
                {
                    "example_id": "a1",
                    "metric": "answer_relevancy",
                    "score": 0.8,
                    "passed": True,
                    "reason": "relevant",
                },
            ]
        }
    )
    repository = MagicMock()
    repository.record_offline_example = AsyncMock()

    count = await persist(report, repository=repository)

    assert count == 2
    assert repository.record_offline_example.await_count == 2
    repository.record_offline_example.assert_any_await(
        dataset_example_id="a1",
        metric_name="faithfulness",
        score=0.9,
        passed=True,
        reason="grounded",
    )
