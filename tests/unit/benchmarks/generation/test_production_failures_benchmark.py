"""
Unit tests for `ProductionFailuresBenchmark` (Evaluation Platform Gap 2 --
E10's "both directions" loop only actually closed for the "good"
direction until this file: `GoldenSetBenchmark` never read
`production_failures.json`).

Reuses the exact fake-judge/fake-generation-service pattern
`test_golden_set_benchmark.py` already established -- this file only
covers what's actually different: which dataset file gets read, and the
`failure_category` inclusion filter.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import GenerationResult

from benchmarks.generation.abstention_judge import AbstentionJudgeResult
from benchmarks.generation.golden_dataset import (
    Difficulty,
    ExpectedBehavior,
    GoldenDataset,
    GoldenExample,
    QueryType,
    Workflow,
)
from benchmarks.generation.production_failures_benchmark import (
    PRODUCTION_FAILURES_DATASET_FILENAME,
    ProductionFailuresBenchmark,
)


class _FakeMetricResult:
    def __init__(self, value: float, reason: str | None = None) -> None:
        self.value = value
        self.reason = reason

    def __float__(self) -> float:
        return self.value


class _FakeFaithfulness:
    def __init__(self, score: float) -> None:
        self.score = score

    async def ascore(
        self, user_input: str, response: str, retrieved_contexts: list[str]
    ) -> _FakeMetricResult:
        return _FakeMetricResult(self.score)


class _FakeAnswerRelevancy:
    def __init__(self, score: float) -> None:
        self.score = score

    async def ascore(self, user_input: str, response: str) -> _FakeMetricResult:
        return _FakeMetricResult(self.score)


class _FakeContextPrecision:
    def __init__(self, score: float) -> None:
        self.score = score

    async def ascore(
        self, user_input: str, reference: str, retrieved_contexts: list[str]
    ) -> _FakeMetricResult:
        return _FakeMetricResult(self.score)


class _FakeContextRecall:
    def __init__(self, score: float) -> None:
        self.score = score

    async def ascore(
        self, user_input: str, retrieved_contexts: list[str], reference: str
    ) -> _FakeMetricResult:
        return _FakeMetricResult(self.score)


class _FakeJudge:
    """Mirrors `test_golden_set_benchmark.py`'s `_FakeJudge` exactly -- a
    single fixed score across all four Ragas metrics is enough here,
    since these tests are about which examples run, not judge-score
    aggregation."""

    def __init__(self, *, score: float = 0.9) -> None:
        self.faithfulness = _FakeFaithfulness(score)
        self.answer_relevancy = _FakeAnswerRelevancy(score)
        self.context_precision = _FakeContextPrecision(score)
        self.context_recall = _FakeContextRecall(score)


def _failure_example(
    example_id: str,
    *,
    failure_category: str,
    workflow: Workflow = Workflow.LINEAR_RESEARCH,
    expected_behavior: ExpectedBehavior = ExpectedBehavior.ANSWER,
) -> GoldenExample:
    return GoldenExample(
        example_id=example_id,
        question=f"What is {example_id}?",
        reference_answer=f"{example_id} is a thing.",
        query_type=QueryType.FACTUAL,
        difficulty=Difficulty.EASY,
        workflow=workflow,
        expected_behavior=expected_behavior,
        contexts=[f"{example_id} context passage."],
        failure_category=failure_category,
    )


def _write_dataset(tmp_path: Path, examples: list[GoldenExample]) -> Path:
    dataset = GoldenDataset(version="test", examples=examples)
    dataset_dir = tmp_path / "production_failures"
    dataset_dir.mkdir()
    (dataset_dir / PRODUCTION_FAILURES_DATASET_FILENAME).write_text(
        dataset.model_dump_json(),
        encoding="utf-8",
    )
    return dataset_dir


def _fake_result(*, content: str = "a generated answer") -> GenerationResult:
    result = MagicMock(spec=GenerationResult)
    result.content = content
    result.model = "fake-model"
    return result


class _FakeAbstentionJudge:
    def __init__(self, *, passed: bool = True) -> None:
        self._passed = passed

    async def ascore(
        self, *, question: str, answer: str, rubric: str | None = None
    ) -> AbstentionJudgeResult:
        return AbstentionJudgeResult(passed=self._passed, reason="fake abstention verdict")


def _benchmark(
    generation_service: MagicMock, *, abstention_judge: _FakeAbstentionJudge | None = None
) -> ProductionFailuresBenchmark:
    return ProductionFailuresBenchmark(
        generation_service=generation_service,
        judge=_FakeJudge(),
        providers=[GenerationProvider.OPENAI],
        abstention_judge=abstention_judge,
    )


@pytest.mark.asyncio
async def test_included_failure_categories_are_evaluated(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(
        tmp_path,
        [
            _failure_example("f1", failure_category="wrong_citation"),
            _failure_example("f2", failure_category="hallucination"),
            _failure_example("f3", failure_category="retrieval_miss"),
            _failure_example("f4", failure_category="injection_success"),
        ],
    )
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    result = await _benchmark(generation_service).run(dataset_dir)

    assert result.dataset.document_count == 4
    assert generation_service.generate.await_count == 4


@pytest.mark.asyncio
async def test_architecturally_infeasible_failure_categories_are_not_evaluated(
    tmp_path: Path,
) -> None:
    """workflow_loop/schema_violation/unnecessary_tool_use don't fit this
    benchmark's single-generation-call-per-example model at all (see
    INCLUDED_FAILURE_CATEGORIES's own docstring) -- excluded until their
    own check logic exists, not silently mis-scored as if they were
    citation/faithfulness failures."""

    dataset_dir = _write_dataset(
        tmp_path,
        [
            _failure_example("f1", failure_category="workflow_loop"),
            _failure_example("f2", failure_category="schema_violation"),
            _failure_example("f3", failure_category="unnecessary_tool_use"),
        ],
    )
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    result = await _benchmark(generation_service).run(dataset_dir)

    assert result.dataset.document_count == 0
    generation_service.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_abstention_failure_examples_are_skipped_without_an_abstention_judge(
    tmp_path: Path,
) -> None:
    """Same opt-in shape as rubric_judge: no abstention_judge wired means
    abstention_failure examples are left out of the report, not
    mis-scored via the Ragas path."""

    dataset_dir = _write_dataset(
        tmp_path,
        [
            _failure_example(
                "f1",
                failure_category="abstention_failure",
                expected_behavior=ExpectedBehavior.ABSTAIN,
            ),
        ],
    )
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    result = await _benchmark(generation_service).run(dataset_dir)

    assert result.dataset.document_count == 0
    generation_service.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_abstention_failure_examples_are_scored_via_the_abstention_judge(
    tmp_path: Path,
) -> None:
    dataset_dir = _write_dataset(
        tmp_path,
        [
            _failure_example("f1", failure_category="wrong_citation"),
            _failure_example(
                "f2",
                failure_category="abstention_failure",
                expected_behavior=ExpectedBehavior.ABSTAIN,
            ),
        ],
    )
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    result = await _benchmark(
        generation_service, abstention_judge=_FakeAbstentionJudge(passed=True)
    ).run(dataset_dir)

    assert result.dataset.document_count == 2
    assert generation_service.generate.await_count == 2
    assert result.candidates[0].metrics["abstention_pass_rate"] == 1.0
    per_example = result.candidates[0].notes["per_example_scores"]
    assert any(
        entry["example_id"] == "f2" and entry["metric"] == "abstention_pass_rate"
        for entry in per_example
    )


@pytest.mark.asyncio
async def test_runs_cleanly_against_an_empty_dataset(tmp_path: Path) -> None:
    """production_failures.json starts empty (no promotions confirmed
    yet, E10) -- must produce a valid report, not error, so this can be
    wired into CI unconditionally from day one."""

    dataset_dir = _write_dataset(tmp_path, [])
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    result = await _benchmark(generation_service).run(dataset_dir)

    assert result.dataset.document_count == 0
    assert result.candidates[0].metrics["examples_evaluated"] == 0
    generation_service.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_benchmark_name_is_reported_separately_from_golden_set(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(tmp_path, [])
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    result = await _benchmark(generation_service).run(dataset_dir)

    assert result.benchmark_name == "ProductionFailuresRegression"
