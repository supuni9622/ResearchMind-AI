"""
Unit tests for `AbstentionBenchmark` (populates `abstention_pass_rate`,
`EVALUATION_PLAN.md` §13's third absolute gate -- declared in
`thresholds.py` but never emitted by any benchmark run until this file).

Reuses the exact fake-generation-service pattern
`test_golden_set_benchmark.py` already established. No live OpenAI
calls -- `_FakeAbstentionJudge` stands in for the real judge.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import GenerationResult

from benchmarks.generation.abstention_benchmark import AbstentionBenchmark
from benchmarks.generation.abstention_judge import AbstentionJudgeResult
from benchmarks.generation.golden_dataset import (
    Difficulty,
    ExpectedBehavior,
    GoldenDataset,
    GoldenExample,
    QueryType,
    Workflow,
)
from benchmarks.generation.golden_set_benchmark import GOLDEN_DATASET_FILENAME


class _FakeAbstentionJudge:
    def __init__(self, *, passed: bool = True) -> None:
        self._passed = passed
        self.calls: list[tuple[str, str, str | None]] = []

    async def ascore(
        self, *, question: str, answer: str, rubric: str | None = None
    ) -> AbstentionJudgeResult:
        self.calls.append((question, answer, rubric))
        return AbstentionJudgeResult(passed=self._passed, reason="fake abstention verdict")


class _RaisingAbstentionJudge:
    async def ascore(
        self, *, question: str, answer: str, rubric: str | None = None
    ) -> AbstentionJudgeResult:
        raise RuntimeError("judge unavailable")


def _answerable_example(example_id: str) -> GoldenExample:
    return GoldenExample(
        example_id=example_id,
        question=f"What is {example_id}?",
        reference_answer=f"{example_id} is a thing.",
        query_type=QueryType.FACTUAL,
        difficulty=Difficulty.EASY,
        workflow=Workflow.LINEAR_RESEARCH,
        expected_behavior=ExpectedBehavior.ANSWER,
        contexts=[f"{example_id} context passage."],
    )


def _unanswerable_example(example_id: str, *, rubric: str | None = None) -> GoldenExample:
    return GoldenExample(
        example_id=example_id,
        question=f"What is {example_id}?",
        query_type=QueryType.UNANSWERABLE,
        difficulty=Difficulty.EASY,
        workflow=Workflow.CHAT,
        expected_behavior=ExpectedBehavior.ABSTAIN,
        rubric=rubric,
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


def _fake_result(
    *, content: str = "I don't have enough information to answer that."
) -> GenerationResult:
    result = MagicMock(spec=GenerationResult)
    result.content = content
    result.model = "fake-model"
    return result


def _benchmark(
    generation_service: MagicMock, abstention_judge: _FakeAbstentionJudge | _RaisingAbstentionJudge
) -> AbstentionBenchmark:
    return AbstentionBenchmark(
        generation_service=generation_service,
        abstention_judge=abstention_judge,
        providers=[GenerationProvider.OPENAI],
    )


@pytest.mark.asyncio
async def test_only_unanswerable_examples_are_evaluated(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(
        tmp_path,
        [_answerable_example("a1"), _unanswerable_example("u1")],
    )
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    result = await _benchmark(generation_service, _FakeAbstentionJudge()).run(dataset_dir)

    assert result.dataset.document_count == 1
    assert generation_service.generate.await_count == 1


@pytest.mark.asyncio
async def test_passed_verdicts_populate_the_abstention_pass_rate_metric(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(
        tmp_path, [_unanswerable_example("u1"), _unanswerable_example("u2")]
    )
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    result = await _benchmark(generation_service, _FakeAbstentionJudge(passed=True)).run(
        dataset_dir
    )

    assert result.candidates[0].metrics["abstention_pass_rate"] == 1.0


@pytest.mark.asyncio
async def test_failed_verdicts_populate_the_abstention_pass_rate_metric(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(tmp_path, [_unanswerable_example("u1")])
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(
        return_value=_fake_result(content="Here is a confident (fabricated) answer.")
    )

    result = await _benchmark(generation_service, _FakeAbstentionJudge(passed=False)).run(
        dataset_dir
    )

    assert result.candidates[0].metrics["abstention_pass_rate"] == 0.0


@pytest.mark.asyncio
async def test_examples_use_no_retrieved_context(tmp_path: Path) -> None:
    """Unlike GoldenSetBenchmark's answerable path, no ContextChunk/
    Citation machinery is built -- there's nothing to be faithful to for
    a question that should be declined."""

    dataset_dir = _write_dataset(tmp_path, [_unanswerable_example("u1")])
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    await _benchmark(generation_service, _FakeAbstentionJudge()).run(dataset_dir)

    request = generation_service.generate.await_args.kwargs["request"]
    assert request.prompt_context.chunks == []
    assert request.prompt_context.context == ""


@pytest.mark.asyncio
async def test_examples_own_rubric_is_passed_to_the_judge_as_the_abstention_criterion(
    tmp_path: Path,
) -> None:
    dataset_dir = _write_dataset(
        tmp_path,
        [_unanswerable_example("u1", rubric="corpus has no breast-cancer coverage")],
    )
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())
    judge = _FakeAbstentionJudge()

    await _benchmark(generation_service, judge).run(dataset_dir)

    assert judge.calls[0][2] == "corpus has no breast-cancer coverage"


@pytest.mark.asyncio
async def test_every_provider_failing_produces_an_error_entry_not_a_crash(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(tmp_path, [_unanswerable_example("u1")])
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(side_effect=RuntimeError("provider down"))

    result = await _benchmark(generation_service, _FakeAbstentionJudge()).run(dataset_dir)

    per_example = result.candidates[0].notes["per_example_scores"]
    assert per_example[0]["metric"] == "error"
    assert "provider down" in per_example[0]["reason"]


@pytest.mark.asyncio
async def test_judge_failure_produces_an_error_entry_not_a_crash(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(tmp_path, [_unanswerable_example("u1")])
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    result = await _benchmark(generation_service, _RaisingAbstentionJudge()).run(dataset_dir)

    per_example = result.candidates[0].notes["per_example_scores"]
    assert per_example[0]["metric"] == "error"
    assert "judge unavailable" in per_example[0]["reason"]


@pytest.mark.asyncio
async def test_benchmark_name_is_reported_separately(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(tmp_path, [])
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    result = await _benchmark(generation_service, _FakeAbstentionJudge()).run(dataset_dir)

    assert result.benchmark_name == "AbstentionRegression"
