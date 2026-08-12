"""
Unit tests for `app.services.segment_analysis.aggregate_offline_by_content_segment`
(E9's offline half, EVALUATION_IMPLEMENTATION_TRACKER.md).

Uses a small, hand-written golden dataset fixture (not the real 115-example
one) so this stays a fast, isolated unit test -- the real dataset is
exercised end-to-end by `tests/evaluation/test_citation_validity.py` and
the integration suite.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.models.eval_score import EvalScore
from app.services import segment_analysis


def _write_dataset(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": "test",
                "examples": [
                    {
                        "example_id": "g1",
                        "question": "q1",
                        "query_type": "factual",
                        "difficulty": "easy",
                        "workflow": "chat",
                    },
                    {
                        "example_id": "g2",
                        "question": "q2",
                        "query_type": "comparison",
                        "difficulty": "hard",
                        "workflow": "linear_research",
                    },
                    {
                        "example_id": "g3",
                        "question": "q3",
                        "query_type": "comparison",
                        "difficulty": "medium",
                        "workflow": "linear_research",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _score(
    *, dataset_example_id: str | None, score: float | None, passed: bool | None
) -> EvalScore:
    return EvalScore(
        id=uuid4(),
        dataset_example_id=dataset_example_id,
        score=score,
        passed=passed,
        source="offline_benchmark",
        metric_name="faithfulness",
    )


def test_groups_by_query_type_and_computes_aggregates(tmp_path, monkeypatch) -> None:
    dataset_path = tmp_path / "golden" / "rag_answer_gold.json"
    _write_dataset(dataset_path)
    monkeypatch.setattr(segment_analysis, "GOLDEN_DATASET_PATH", dataset_path)

    rows = [
        _score(dataset_example_id="g1", score=0.9, passed=True),
        _score(dataset_example_id="g2", score=0.5, passed=False),
        _score(dataset_example_id="g3", score=0.7, passed=True),
    ]

    result = segment_analysis.aggregate_offline_by_content_segment(rows, segment_field="query_type")
    by_segment = {aggregate.segment_value: aggregate for aggregate in result}

    assert by_segment["factual"].count == 1
    assert by_segment["factual"].avg_score == 0.9
    assert by_segment["factual"].pass_rate == 1.0

    assert by_segment["comparison"].count == 2
    assert by_segment["comparison"].avg_score == 0.6
    assert by_segment["comparison"].pass_rate == 0.5


def test_groups_by_difficulty(tmp_path, monkeypatch) -> None:
    dataset_path = tmp_path / "golden" / "rag_answer_gold.json"
    _write_dataset(dataset_path)
    monkeypatch.setattr(segment_analysis, "GOLDEN_DATASET_PATH", dataset_path)

    rows = [_score(dataset_example_id="g2", score=0.4, passed=False)]

    result = segment_analysis.aggregate_offline_by_content_segment(rows, segment_field="difficulty")

    assert len(result) == 1
    assert result[0].segment_value == "hard"
    assert result[0].count == 1


def test_skips_rows_with_no_dataset_example_id(tmp_path, monkeypatch) -> None:
    dataset_path = tmp_path / "golden" / "rag_answer_gold.json"
    _write_dataset(dataset_path)
    monkeypatch.setattr(segment_analysis, "GOLDEN_DATASET_PATH", dataset_path)

    rows = [_score(dataset_example_id=None, score=0.9, passed=True)]

    result = segment_analysis.aggregate_offline_by_content_segment(rows, segment_field="query_type")

    assert result == []


def test_skips_rows_whose_example_id_is_no_longer_in_the_dataset(tmp_path, monkeypatch) -> None:
    """The golden set is allowed to grow/change over time -- an orphaned
    historical row referencing a since-removed example shouldn't break
    this view."""

    dataset_path = tmp_path / "golden" / "rag_answer_gold.json"
    _write_dataset(dataset_path)
    monkeypatch.setattr(segment_analysis, "GOLDEN_DATASET_PATH", dataset_path)

    rows = [_score(dataset_example_id="does-not-exist", score=0.9, passed=True)]

    result = segment_analysis.aggregate_offline_by_content_segment(rows, segment_field="query_type")

    assert result == []


def test_scores_and_passed_can_be_partially_null(tmp_path, monkeypatch) -> None:
    dataset_path = tmp_path / "golden" / "rag_answer_gold.json"
    _write_dataset(dataset_path)
    monkeypatch.setattr(segment_analysis, "GOLDEN_DATASET_PATH", dataset_path)

    rows = [
        _score(dataset_example_id="g1", score=None, passed=None),
        _score(dataset_example_id="g1", score=0.8, passed=True),
    ]

    result = segment_analysis.aggregate_offline_by_content_segment(rows, segment_field="query_type")

    assert result[0].count == 2
    assert result[0].avg_score == 0.8
    assert result[0].pass_rate == 1.0


def test_results_are_sorted_by_segment_value(tmp_path, monkeypatch) -> None:
    dataset_path = tmp_path / "golden" / "rag_answer_gold.json"
    _write_dataset(dataset_path)
    monkeypatch.setattr(segment_analysis, "GOLDEN_DATASET_PATH", dataset_path)

    rows = [
        _score(dataset_example_id="g2", score=0.5, passed=True),
        _score(dataset_example_id="g1", score=0.5, passed=True),
    ]

    result = segment_analysis.aggregate_offline_by_content_segment(rows, segment_field="query_type")

    assert [aggregate.segment_value for aggregate in result] == ["comparison", "factual"]


# -- failure_category (E9 follow-up, only production_failures examples have one) --


def _write_production_failures(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": "test",
                "examples": [
                    {
                        "example_id": "pf1",
                        "question": "q1",
                        "query_type": "factual",
                        "difficulty": "easy",
                        "workflow": "chat",
                        "failure_category": "wrong_citation",
                    },
                    {
                        "example_id": "pf2",
                        "question": "q2",
                        "query_type": "factual",
                        "difficulty": "easy",
                        "workflow": "chat",
                        "failure_category": "hallucination",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def test_groups_by_failure_category_from_the_production_failures_dataset(
    tmp_path, monkeypatch
) -> None:
    golden_path = tmp_path / "golden" / "rag_answer_gold.json"
    failures_path = tmp_path / "production_failures" / "production_failures.json"
    _write_dataset(golden_path)
    _write_production_failures(failures_path)
    monkeypatch.setattr(segment_analysis, "GOLDEN_DATASET_PATH", golden_path)
    monkeypatch.setattr(segment_analysis, "PRODUCTION_FAILURES_DATASET_PATH", failures_path)

    rows = [
        _score(dataset_example_id="pf1", score=0.2, passed=False),
        _score(dataset_example_id="pf2", score=0.1, passed=False),
    ]

    result = segment_analysis.aggregate_offline_by_content_segment(
        rows, segment_field="failure_category"
    )
    by_segment = {aggregate.segment_value: aggregate for aggregate in result}

    assert by_segment["wrong_citation"].count == 1
    assert by_segment["hallucination"].count == 1


def test_rag_answer_gold_rows_never_appear_in_the_failure_category_slice(
    tmp_path, monkeypatch
) -> None:
    """rag_answer_gold examples have no failure_category at all -- must
    be excluded entirely, not grouped under a bogus "None" bucket."""

    golden_path = tmp_path / "golden" / "rag_answer_gold.json"
    failures_path = tmp_path / "production_failures" / "production_failures.json"
    _write_dataset(golden_path)
    _write_production_failures(failures_path)
    monkeypatch.setattr(segment_analysis, "GOLDEN_DATASET_PATH", golden_path)
    monkeypatch.setattr(segment_analysis, "PRODUCTION_FAILURES_DATASET_PATH", failures_path)

    rows = [_score(dataset_example_id="g1", score=0.9, passed=True)]

    result = segment_analysis.aggregate_offline_by_content_segment(
        rows, segment_field="failure_category"
    )

    assert result == []


def test_missing_production_failures_file_does_not_error(tmp_path, monkeypatch) -> None:
    golden_path = tmp_path / "golden" / "rag_answer_gold.json"
    _write_dataset(golden_path)
    monkeypatch.setattr(segment_analysis, "GOLDEN_DATASET_PATH", golden_path)
    monkeypatch.setattr(
        segment_analysis, "PRODUCTION_FAILURES_DATASET_PATH", tmp_path / "does-not-exist.json"
    )

    rows = [_score(dataset_example_id="g1", score=0.9, passed=True)]

    result = segment_analysis.aggregate_offline_by_content_segment(rows, segment_field="query_type")

    assert result[0].segment_value == "factual"
