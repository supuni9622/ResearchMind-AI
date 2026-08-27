"""
Unit tests for `SchemaValidityBenchmark` (populates `schema_validity_rate`,
`EVALUATION_PLAN.md` §13's fourth absolute gate).

Uses a real `ResearchPlanner` wrapping a fake `GenerationRuntimeInterface`
(`AsyncMock`, same pattern `test_planner.py` already established) rather
than mocking the planner itself -- this benchmark's whole point is
exercising `ResearchPlanner.plan()`'s real schema-validation path, not
just checking that it gets called.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.ai.runtime.research.planner.models import (
    ResearchComplexity,
    ResearchExecutionStrategy,
    ResearchPlan,
    ResearchPlanTask,
)
from app.ai.runtime.research.planner.service import ResearchPlanner

from benchmarks.generation.schema_validity_benchmark import (
    SCHEMA_VALIDITY_DATASET_FILENAME,
    SchemaValidityBenchmark,
)
from benchmarks.generation.schema_validity_dataset import SchemaValidityDataset, SchemaValidityQuery


def _focused_plan() -> ResearchPlan:
    return ResearchPlan(
        goal="How does RAG work?",
        complexity=ResearchComplexity.SIMPLE,
        execution_strategy=ResearchExecutionStrategy.FOCUSED,
        tasks=[ResearchPlanTask(task_id="research", question="How does RAG work?")],
    )


def _over_budget_output() -> dict[str, object]:
    return {
        "goal": "Compare approaches",
        "complexity": "simple",
        "execution_strategy": "decomposed",
        "tasks": [
            {"task_id": "one", "question": "one"},
            {"task_id": "two", "question": "two"},
        ],
    }


def _write_dataset(tmp_path: Path, queries: list[SchemaValidityQuery]) -> Path:
    dataset = SchemaValidityDataset(version="test", queries=queries)
    dataset_dir = tmp_path / "schema_validity"
    dataset_dir.mkdir()
    (dataset_dir / SCHEMA_VALIDITY_DATASET_FILENAME).write_text(
        dataset.model_dump_json(),
        encoding="utf-8",
    )
    return dataset_dir


def _benchmark(runtime: AsyncMock) -> SchemaValidityBenchmark:
    return SchemaValidityBenchmark(planner=ResearchPlanner(runtime))


@pytest.mark.asyncio
async def test_schema_valid_output_scores_the_metric_as_passed(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(tmp_path, [SchemaValidityQuery(query_id="sv1", query="q")])
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(parsed_output=_focused_plan())

    result = await _benchmark(runtime).run(dataset_dir)

    assert result.candidates[0].metrics["schema_validity_rate"] == 1.0
    per_example = result.candidates[0].notes["per_example_scores"]
    assert per_example[0]["passed"] is True


@pytest.mark.asyncio
async def test_schema_invalid_output_scores_the_metric_as_failed(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(tmp_path, [SchemaValidityQuery(query_id="sv1", query="q")])
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(parsed_output=None, content="")

    result = await _benchmark(runtime).run(dataset_dir)

    assert result.candidates[0].metrics["schema_validity_rate"] == 0.0
    per_example = result.candidates[0].notes["per_example_scores"]
    assert per_example[0]["passed"] is False
    assert "schema-valid" in per_example[0]["reason"]


@pytest.mark.asyncio
async def test_over_budget_but_schema_valid_output_does_not_count_against_the_metric(
    tmp_path: Path,
) -> None:
    """A plan that parses cleanly against ResearchPlan but exceeds
    ResearchPlanningPolicy's task-count budget is a policy failure, not a
    schema one -- schema_validity_rate shouldn't be understated for a
    reason it doesn't claim to measure."""

    dataset_dir = _write_dataset(tmp_path, [SchemaValidityQuery(query_id="sv1", query="q")])
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(parsed_output=_over_budget_output())

    result = await _benchmark(runtime).run(dataset_dir)

    assert result.candidates[0].metrics["schema_validity_rate"] == 1.0
    per_example = result.candidates[0].notes["per_example_scores"]
    assert per_example[0]["passed"] is True
    assert "non-schema reason" in per_example[0]["reason"]


@pytest.mark.asyncio
async def test_a_non_planner_error_is_recorded_as_an_error_entry_not_a_crash(
    tmp_path: Path,
) -> None:
    dataset_dir = _write_dataset(tmp_path, [SchemaValidityQuery(query_id="sv1", query="q")])
    runtime = AsyncMock()
    runtime.execute.side_effect = RuntimeError("provider unavailable")

    result = await _benchmark(runtime).run(dataset_dir)

    assert "schema_validity_rate" not in result.candidates[0].metrics
    per_example = result.candidates[0].notes["per_example_scores"]
    assert per_example[0]["metric"] == "error"
    assert "provider unavailable" in per_example[0]["reason"]


@pytest.mark.asyncio
async def test_metric_averages_across_multiple_queries(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(
        tmp_path,
        [
            SchemaValidityQuery(query_id="sv1", query="q1"),
            SchemaValidityQuery(query_id="sv2", query="q2"),
        ],
    )
    runtime = AsyncMock()
    runtime.execute.side_effect = [
        SimpleNamespace(parsed_output=_focused_plan()),
        SimpleNamespace(parsed_output=None, content=""),
    ]

    result = await _benchmark(runtime).run(dataset_dir)

    assert result.candidates[0].metrics["schema_validity_rate"] == 0.5
    assert result.dataset.document_count == 2


@pytest.mark.asyncio
async def test_benchmark_name(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(tmp_path, [])
    runtime = AsyncMock()

    result = await _benchmark(runtime).run(dataset_dir)

    assert result.benchmark_name == "SchemaValidityRegression"
