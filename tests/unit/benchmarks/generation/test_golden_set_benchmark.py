"""
Unit tests for `GoldenSetBenchmark` (E6, EVALUATION_PLAN.md §7 release-
candidate tier) -- the runnable driver that runs `rag_answer_gold`
through a live generation call and the real Ragas judge, which E1 built
the pieces for but never wired into anything runnable.

No live LLM/embedding calls anywhere in this file: `generation_service`
is a `MagicMock`/`AsyncMock` standing in for `GenerationService`
(matches tests/unit/services/test_feedback_service.py's convention for
faking a concrete class), and the judge is the same structural fake
pattern `tests/evaluation/test_faithfulness.py` already established for
`GenerationJudge`.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import GenerationResult

from benchmarks.generation.golden_dataset import (
    Difficulty,
    ExpectedBehavior,
    GoldenDataset,
    GoldenExample,
    QueryType,
    Workflow,
)
from benchmarks.generation.golden_set_benchmark import (
    GOLDEN_DATASET_FILENAME,
    PER_EXAMPLE_SCORES_NOTE_KEY,
    GoldenSetBenchmark,
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
    def __init__(self, *, score: float = 0.9) -> None:
        self.faithfulness = _FakeFaithfulness(score)
        self.answer_relevancy = _FakeAnswerRelevancy(score)
        self.context_precision = _FakeContextPrecision(score)
        self.context_recall = _FakeContextRecall(score)


def _answerable_example(example_id: str) -> GoldenExample:
    return GoldenExample(
        example_id=example_id,
        question=f"What is {example_id}?",
        reference_answer=f"{example_id} is a thing.",
        query_type=QueryType.FACTUAL,
        difficulty=Difficulty.EASY,
        workflow=Workflow.CHAT,
        expected_behavior=ExpectedBehavior.ANSWER,
        contexts=[f"{example_id} context passage."],
    )


def _unanswerable_example(example_id: str) -> GoldenExample:
    return GoldenExample(
        example_id=example_id,
        question=f"What is {example_id}?",
        query_type=QueryType.UNANSWERABLE,
        difficulty=Difficulty.EASY,
        workflow=Workflow.CHAT,
        expected_behavior=ExpectedBehavior.ABSTAIN,
    )


def _write_dataset(tmp_path: Path, examples: list[GoldenExample]) -> Path:
    dataset = GoldenDataset(version="test", examples=examples)
    dataset_dir = tmp_path / "golden"
    dataset_dir.mkdir()
    (dataset_dir / GOLDEN_DATASET_FILENAME).write_text(
        dataset.model_dump_json(),
        encoding="utf-8",
    )
    return dataset_dir


def _fake_result(*, content: str = "a generated answer") -> GenerationResult:
    result = MagicMock(spec=GenerationResult)
    result.content = content
    result.model = "fake-model"
    return result


@pytest.mark.asyncio
async def test_only_answerable_examples_are_evaluated(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(
        tmp_path,
        [_answerable_example("a1"), _unanswerable_example("u1")],
    )
    registry = MagicMock()
    registry.providers = [GenerationProvider.GROQ]
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    benchmark = GoldenSetBenchmark(
        registry=registry,
        generation_service=generation_service,
        judge=_FakeJudge(),
    )
    report = benchmark  # keep name short below
    result = await report.run(dataset_dir)

    assert result.dataset.document_count == 1
    generation_service.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_per_example_scores_are_recorded_in_notes(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(tmp_path, [_answerable_example("a1")])
    registry = MagicMock()
    registry.providers = [GenerationProvider.GROQ]
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    benchmark = GoldenSetBenchmark(
        registry=registry,
        generation_service=generation_service,
        judge=_FakeJudge(score=0.75),
    )
    result = await benchmark.run(dataset_dir)

    candidate = result.candidates[0]
    per_example = candidate.notes[PER_EXAMPLE_SCORES_NOTE_KEY]
    assert {entry["metric"] for entry in per_example} == {
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
    }
    for entry in per_example:
        assert entry["example_id"] == "a1"
        assert entry["score"] == pytest.approx(0.75)


@pytest.mark.asyncio
async def test_aggregate_metrics_average_across_examples(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(
        tmp_path,
        [_answerable_example("a1"), _answerable_example("a2")],
    )
    registry = MagicMock()
    registry.providers = [GenerationProvider.GROQ]
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    benchmark = GoldenSetBenchmark(
        registry=registry,
        generation_service=generation_service,
        judge=_FakeJudge(score=0.8),
    )
    result = await benchmark.run(dataset_dir)

    candidate = result.candidates[0]
    assert candidate.metrics["examples_evaluated"] == 2
    assert candidate.metrics["faithfulness"] == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_one_examples_generation_failure_does_not_abort_the_run(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(
        tmp_path,
        [_answerable_example("a1"), _answerable_example("a2")],
    )
    registry = MagicMock()
    registry.providers = [GenerationProvider.GROQ]
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(
        side_effect=[RuntimeError("provider exploded"), _fake_result()]
    )

    benchmark = GoldenSetBenchmark(
        registry=registry,
        generation_service=generation_service,
        judge=_FakeJudge(),
    )
    result = await benchmark.run(dataset_dir)

    candidate = result.candidates[0]
    per_example = candidate.notes[PER_EXAMPLE_SCORES_NOTE_KEY]
    error_entries = [entry for entry in per_example if entry["example_id"] == "a1"]
    assert error_entries == [
        {
            "example_id": "a1",
            "metric": "error",
            "score": None,
            "passed": False,
            "reason": "provider exploded",
        }
    ]
    success_entries = [entry for entry in per_example if entry["example_id"] == "a2"]
    assert len(success_entries) == 4


@pytest.mark.asyncio
async def test_produces_one_candidate_per_registered_provider(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(tmp_path, [_answerable_example("a1")])
    registry = MagicMock()
    registry.providers = [GenerationProvider.GROQ, GenerationProvider.OPENAI]
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    benchmark = GoldenSetBenchmark(
        registry=registry,
        generation_service=generation_service,
        judge=_FakeJudge(),
    )
    result = await benchmark.run(dataset_dir)

    assert {candidate.name for candidate in result.candidates} == {"groq", "openai"}


def test_write_dataset_helper_round_trips_via_json(tmp_path: Path) -> None:
    """Sanity check on this file's own fixture helper, not the benchmark
    itself -- guards against a future edit silently breaking the
    load_golden_dataset() round trip every other test here depends on."""

    dataset_dir = _write_dataset(tmp_path, [_answerable_example(str(uuid4()))])
    raw = json.loads((dataset_dir / GOLDEN_DATASET_FILENAME).read_text())
    assert raw["examples"][0]["expected_behavior"] == "answer"
