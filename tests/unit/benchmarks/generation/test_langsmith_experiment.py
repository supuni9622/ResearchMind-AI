"""
Unit tests for `benchmarks/generation/langsmith_experiment.py` (E19's
remaining Experiment-logging subtask).

No live LangSmith calls -- `get_langsmith_client` is monkeypatched to a
`MagicMock`, matching `test_langsmith_sync.py`'s established pattern.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from benchmarks.generation import langsmith_experiment, langsmith_sync
from benchmarks.generation.golden_set_benchmark import PER_EXAMPLE_SCORES_NOTE_KEY
from benchmarks.models.report import BenchmarkCandidate, BenchmarkDataset, BenchmarkReport


def _report(
    *, per_example: list[dict[str, object]] | None = None, candidates=None
) -> BenchmarkReport:
    if candidates is None:
        candidates = [
            BenchmarkCandidate(
                name="openai+claude",
                version="gpt-5",
                metrics={"faithfulness": 0.8},
                notes={PER_EXAMPLE_SCORES_NOTE_KEY: per_example if per_example is not None else []},
            )
        ]
    return BenchmarkReport(
        benchmark_name="GoldenSetGeneration",
        generated_at=datetime(2026, 8, 12, 9, 30, 0, tzinfo=UTC),
        dataset=BenchmarkDataset(name="golden", document_count=1),
        candidates=candidates,
    )


def _make_client(*, dataset_id: uuid.UUID | None = None) -> MagicMock:
    client = MagicMock()
    client.read_dataset.return_value = MagicMock(id=dataset_id or uuid.uuid4())
    return client


def test_raises_when_langsmith_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(langsmith_experiment, "get_langsmith_client", lambda: None)

    with pytest.raises(langsmith_experiment.LangSmithNotConfiguredError):
        langsmith_experiment.log_experiment(_report(per_example=[{"example_id": "g1"}]))


def test_raises_when_report_has_no_candidates(monkeypatch) -> None:
    client = _make_client()
    monkeypatch.setattr(langsmith_experiment, "get_langsmith_client", lambda: client)

    with pytest.raises(ValueError, match="no candidates"):
        langsmith_experiment.log_experiment(_report(candidates=[]))


def test_raises_when_report_has_no_per_example_scores(monkeypatch) -> None:
    client = _make_client()
    monkeypatch.setattr(langsmith_experiment, "get_langsmith_client", lambda: client)

    with pytest.raises(ValueError, match="no per-example scores"):
        langsmith_experiment.log_experiment(_report(per_example=[]))


def test_creates_a_project_linked_to_the_dataset(monkeypatch) -> None:
    dataset_id = uuid.uuid4()
    client = _make_client(dataset_id=dataset_id)
    monkeypatch.setattr(langsmith_experiment, "get_langsmith_client", lambda: client)

    report = _report(
        per_example=[
            {
                "example_id": "g1",
                "metric": "faithfulness",
                "score": 0.9,
                "passed": True,
                "reason": "grounded",
                "provider": "openai",
            }
        ]
    )
    langsmith_experiment.log_experiment(report, dataset_name="rag_answer_gold")

    client.read_dataset.assert_called_once_with(dataset_name="rag_answer_gold")
    client.create_project.assert_called_once()
    assert client.create_project.call_args.kwargs["reference_dataset_id"] == dataset_id


def test_default_experiment_name_includes_benchmark_name_and_timestamp(monkeypatch) -> None:
    client = _make_client()
    monkeypatch.setattr(langsmith_experiment, "get_langsmith_client", lambda: client)

    report = _report(
        per_example=[
            {
                "example_id": "g1",
                "metric": "faithfulness",
                "score": 0.9,
                "passed": True,
                "reason": "ok",
            }
        ]
    )
    name = langsmith_experiment.log_experiment(report)

    assert name.startswith("GoldenSetGeneration-2026-08-12")
    assert client.create_project.call_args.kwargs["project_name"] == name


def test_custom_experiment_name_overrides_the_default(monkeypatch) -> None:
    client = _make_client()
    monkeypatch.setattr(langsmith_experiment, "get_langsmith_client", lambda: client)

    report = _report(
        per_example=[
            {
                "example_id": "g1",
                "metric": "faithfulness",
                "score": 0.9,
                "passed": True,
                "reason": "ok",
            }
        ]
    )
    name = langsmith_experiment.log_experiment(report, experiment_name="my-experiment")

    assert name == "my-experiment"


def test_creates_one_run_per_example_not_per_metric(monkeypatch) -> None:
    client = _make_client()
    monkeypatch.setattr(langsmith_experiment, "get_langsmith_client", lambda: client)

    report = _report(
        per_example=[
            {
                "example_id": "g1",
                "metric": "faithfulness",
                "score": 0.9,
                "passed": True,
                "reason": "a",
            },
            {
                "example_id": "g1",
                "metric": "answer_relevancy",
                "score": 0.8,
                "passed": True,
                "reason": "b",
            },
            {
                "example_id": "g2",
                "metric": "faithfulness",
                "score": 0.4,
                "passed": False,
                "reason": "c",
            },
        ]
    )
    langsmith_experiment.log_experiment(report)

    assert client.create_run.call_count == 2
    run_names = {call.kwargs["name"] for call in client.create_run.call_args_list}
    assert run_names == {"g1", "g2"}


def test_run_is_linked_to_its_dataset_example_via_reference_example_id(monkeypatch) -> None:
    client = _make_client()
    monkeypatch.setattr(langsmith_experiment, "get_langsmith_client", lambda: client)

    report = _report(
        per_example=[
            {
                "example_id": "g1",
                "metric": "faithfulness",
                "score": 0.9,
                "passed": True,
                "reason": "a",
            },
        ]
    )
    langsmith_experiment.log_experiment(report, dataset_name="rag_answer_gold")

    call_kwargs = client.create_run.call_args.kwargs
    assert call_kwargs["reference_example_id"] == langsmith_sync.example_id_to_langsmith_id("g1")


def test_every_scored_metric_becomes_its_own_feedback_entry(monkeypatch) -> None:
    client = _make_client()
    monkeypatch.setattr(langsmith_experiment, "get_langsmith_client", lambda: client)

    report = _report(
        per_example=[
            {
                "example_id": "g1",
                "metric": "faithfulness",
                "score": 0.9,
                "passed": True,
                "reason": "a",
            },
            {
                "example_id": "g1",
                "metric": "rubric_adherence",
                "score": 1.0,
                "passed": True,
                "reason": "b",
            },
        ]
    )
    langsmith_experiment.log_experiment(report)

    assert client.create_feedback.call_count == 2
    keys = {call.kwargs["key"] for call in client.create_feedback.call_args_list}
    assert keys == {"faithfulness", "rubric_adherence"}


def test_error_entries_are_excluded_from_outputs_and_feedback(monkeypatch) -> None:
    """An example whose whole score_generation() call failed (see
    golden_set_benchmark.py's own error-entry shape) still gets a run --
    just with no real metrics and passed=False -- rather than being
    silently dropped from the experiment entirely."""

    client = _make_client()
    monkeypatch.setattr(langsmith_experiment, "get_langsmith_client", lambda: client)

    report = _report(
        per_example=[
            {
                "example_id": "g9",
                "metric": "error",
                "score": None,
                "passed": False,
                "reason": "every provider failed",
            },
        ]
    )
    langsmith_experiment.log_experiment(report)

    client.create_run.assert_called_once()
    outputs = client.create_run.call_args.kwargs["outputs"]
    assert outputs["passed"] is False
    assert outputs["metrics"] == {}
    client.create_feedback.assert_not_called()


def test_a_failed_metric_makes_the_run_output_passed_false(monkeypatch) -> None:
    client = _make_client()
    monkeypatch.setattr(langsmith_experiment, "get_langsmith_client", lambda: client)

    report = _report(
        per_example=[
            {
                "example_id": "g1",
                "metric": "faithfulness",
                "score": 0.9,
                "passed": True,
                "reason": "a",
            },
            {
                "example_id": "g1",
                "metric": "rubric_adherence",
                "score": 0.0,
                "passed": False,
                "reason": "b",
            },
        ]
    )
    langsmith_experiment.log_experiment(report)

    outputs = client.create_run.call_args.kwargs["outputs"]
    assert outputs["passed"] is False
