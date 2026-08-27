"""
Unit tests for `GoldenSetBenchmark` (E6, EVALUATION_PLAN.md §7 release-
candidate tier) -- the runnable driver that runs `rag_answer_gold`
through a live generation call and the real Ragas judge, which E1 built
the pieces for but never wired into anything runnable.

Runs against an ordered provider fallback chain, not one candidate per
registered provider (a real Groq run hit a daily-token-limit 429
mid-pass, which would have poisoned that whole candidate -- see
`golden_set_benchmark.py`'s own module docstring) -- these tests cover
that fallback behavior specifically: per-example provider fallback, and
what happens when every provider in the chain fails.

No live LLM/embedding calls anywhere in this file: `generation_service`
is a `MagicMock`/`AsyncMock` standing in for `GenerationService`
(matches tests/unit/services/test_feedback_service.py's convention for
faking a concrete class), and the judge is the same structural fake
pattern `tests/evaluation/test_faithfulness.py` already established for
`GenerationJudge`.
"""

from __future__ import annotations

import asyncio
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


def _answerable_example(
    example_id: str,
    *,
    workflow: Workflow = Workflow.LINEAR_RESEARCH,
    rubric: str | None = None,
) -> GoldenExample:
    # Defaults to linear_research, not chat: citations are expected
    # (checked) for linear_research/deep_research examples, not for
    # chat (see `expects_citations` in golden_set_benchmark.py) -- most
    # tests in this file want the citation entry present, so that's the
    # more useful default; tests specifically about chat's exclusion
    # pass `workflow=Workflow.CHAT` explicitly.
    return GoldenExample(
        example_id=example_id,
        question=f"What is {example_id}?",
        reference_answer=f"{example_id} is a thing.",
        query_type=QueryType.FACTUAL,
        difficulty=Difficulty.EASY,
        workflow=workflow,
        expected_behavior=ExpectedBehavior.ANSWER,
        contexts=[f"{example_id} context passage."],
        rubric=rubric,
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
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    benchmark = GoldenSetBenchmark(
        generation_service=generation_service,
        judge=_FakeJudge(),
        providers=[GenerationProvider.OPENAI],
    )
    result = await benchmark.run(dataset_dir)

    assert result.dataset.document_count == 1
    generation_service.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_per_example_scores_are_recorded_in_notes(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(tmp_path, [_answerable_example("a1")])
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    benchmark = GoldenSetBenchmark(
        generation_service=generation_service,
        judge=_FakeJudge(score=0.75),
        providers=[GenerationProvider.OPENAI],
    )
    result = await benchmark.run(dataset_dir)

    candidate = result.candidates[0]
    per_example = candidate.notes[PER_EXAMPLE_SCORES_NOTE_KEY]
    assert {entry["metric"] for entry in per_example} == {
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
        "fabricated_citation_rate",
    }
    for entry in per_example:
        assert entry["example_id"] == "a1"
        assert entry["provider"] == "openai"

    ragas_entries = [
        entry for entry in per_example if entry["metric"] != "fabricated_citation_rate"
    ]
    for entry in ragas_entries:
        assert entry["score"] == pytest.approx(0.75)

    # The fake generation content has no `[S1]`-style citation markers, so
    # E20's citation check correctly reports zero fabrication (nothing was
    # cited at all, not "something was cited and it was wrong").
    citation_entry = next(
        entry for entry in per_example if entry["metric"] == "fabricated_citation_rate"
    )
    assert citation_entry["score"] == pytest.approx(0.0)
    assert citation_entry["passed"] is True


@pytest.mark.asyncio
async def test_correctly_cited_content_reports_zero_fabrication(tmp_path: Path) -> None:
    """`_answerable_example` has exactly one context passage, so
    `CitationService.build()` assigns it citation id "S1" -- citing it
    correctly must not be flagged."""

    dataset_dir = _write_dataset(tmp_path, [_answerable_example("a1")])
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(
        return_value=_fake_result(content="a1 is a thing [S1].")
    )

    benchmark = GoldenSetBenchmark(
        generation_service=generation_service,
        judge=_FakeJudge(),
        providers=[GenerationProvider.OPENAI],
    )
    result = await benchmark.run(dataset_dir)

    per_example = result.candidates[0].notes[PER_EXAMPLE_SCORES_NOTE_KEY]
    citation_entry = next(
        entry for entry in per_example if entry["metric"] == "fabricated_citation_rate"
    )
    assert citation_entry["score"] == pytest.approx(0.0)
    assert citation_entry["passed"] is True


@pytest.mark.asyncio
async def test_fabricated_citation_is_flagged(tmp_path: Path) -> None:
    """Citing "S99", which was never assigned to any chunk, must be
    caught -- this is the case `thresholds.py`'s
    `fabricated_citation_rate` absolute gate exists to fail a build on."""

    dataset_dir = _write_dataset(tmp_path, [_answerable_example("a1")])
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(
        return_value=_fake_result(content="a1 is a thing [S99].")
    )

    benchmark = GoldenSetBenchmark(
        generation_service=generation_service,
        judge=_FakeJudge(),
        providers=[GenerationProvider.OPENAI],
    )
    result = await benchmark.run(dataset_dir)

    per_example = result.candidates[0].notes[PER_EXAMPLE_SCORES_NOTE_KEY]
    citation_entry = next(
        entry for entry in per_example if entry["metric"] == "fabricated_citation_rate"
    )
    assert citation_entry["score"] == pytest.approx(1.0)
    assert citation_entry["passed"] is False
    assert "S99" in citation_entry["reason"]


@pytest.mark.asyncio
async def test_chat_workflow_examples_are_not_instructed_to_cite_or_checked(
    tmp_path: Path,
) -> None:
    """Chat is intentionally citation-free in production (direct
    instruction, 2026-08-12) -- instructing chat-workflow golden examples
    to cite would test a scenario that can never occur in real Chat
    traffic. No `fabricated_citation_rate` entry, and no citation
    instruction sent to the model at all."""

    dataset_dir = _write_dataset(tmp_path, [_answerable_example("a1", workflow=Workflow.CHAT)])
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    benchmark = GoldenSetBenchmark(
        generation_service=generation_service,
        judge=_FakeJudge(),
        providers=[GenerationProvider.OPENAI],
    )
    result = await benchmark.run(dataset_dir)

    per_example = result.candidates[0].notes[PER_EXAMPLE_SCORES_NOTE_KEY]
    assert "fabricated_citation_rate" not in {entry["metric"] for entry in per_example}

    sent_request = generation_service.generate.await_args.kwargs["request"]
    assert sent_request.system_prompt is None


@pytest.mark.asyncio
async def test_aggregate_metrics_average_across_examples(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(
        tmp_path,
        [_answerable_example("a1"), _answerable_example("a2")],
    )
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    benchmark = GoldenSetBenchmark(
        generation_service=generation_service,
        judge=_FakeJudge(score=0.8),
        providers=[GenerationProvider.OPENAI],
    )
    result = await benchmark.run(dataset_dir)

    candidate = result.candidates[0]
    assert candidate.metrics["examples_evaluated"] == 2
    assert candidate.metrics["faithfulness"] == pytest.approx(0.8)
    assert candidate.metrics["examples_via_openai"] == 2


@pytest.mark.asyncio
async def test_produces_exactly_one_candidate_named_after_the_fallback_chain(
    tmp_path: Path,
) -> None:
    dataset_dir = _write_dataset(tmp_path, [_answerable_example("a1")])
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    benchmark = GoldenSetBenchmark(
        generation_service=generation_service,
        judge=_FakeJudge(),
        providers=[GenerationProvider.OPENAI, GenerationProvider.CLAUDE],
    )
    result = await benchmark.run(dataset_dir)

    assert len(result.candidates) == 1
    assert result.candidates[0].name == "openai+claude"


@pytest.mark.asyncio
async def test_falls_back_to_the_next_provider_when_the_first_fails(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(tmp_path, [_answerable_example("a1")])
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(
        side_effect=[RuntimeError("rate limited"), _fake_result()]
    )

    benchmark = GoldenSetBenchmark(
        generation_service=generation_service,
        judge=_FakeJudge(),
        providers=[GenerationProvider.OPENAI, GenerationProvider.CLAUDE],
    )
    result = await benchmark.run(dataset_dir)

    candidate = result.candidates[0]
    per_example = candidate.notes[PER_EXAMPLE_SCORES_NOTE_KEY]
    assert all(entry["metric"] != "error" for entry in per_example)
    assert all(entry["provider"] == "claude" for entry in per_example)
    assert candidate.metrics["examples_via_claude"] == 1
    assert generation_service.generate.await_count == 2


@pytest.mark.asyncio
async def test_one_examples_generation_failure_does_not_abort_the_run(tmp_path: Path) -> None:
    """`a1` exhausts the entire fallback chain (both providers fail); `a2`
    succeeds on the first provider. `a1`'s failure must not prevent `a2`
    from being evaluated.

    `generate()`'s side effect is content-based (inspects `request.
    user_prompt` for which example this is), not a positional list --
    examples now run concurrently (bounded by `max_concurrency`), so
    which example's call reaches the mock first isn't guaranteed the way
    it was under the old fully-sequential design. A positional
    `side_effect=[...]` list would make this test's pass/fail depend on
    incidental mock/event-loop scheduling order rather than on the
    behavior actually being tested.
    """

    dataset_dir = _write_dataset(
        tmp_path,
        [_answerable_example("a1"), _answerable_example("a2")],
    )

    def _generate_side_effect(*, request, provider):  # noqa: ANN001, ANN202
        if "a1" in request.user_prompt:
            raise RuntimeError(f"{provider.value} down")
        return _fake_result()

    generation_service = MagicMock()
    generation_service.generate = AsyncMock(side_effect=_generate_side_effect)

    benchmark = GoldenSetBenchmark(
        generation_service=generation_service,
        judge=_FakeJudge(),
        providers=[GenerationProvider.OPENAI, GenerationProvider.CLAUDE],
    )
    result = await benchmark.run(dataset_dir)

    candidate = result.candidates[0]
    per_example = candidate.notes[PER_EXAMPLE_SCORES_NOTE_KEY]

    error_entries = [entry for entry in per_example if entry["example_id"] == "a1"]
    assert len(error_entries) == 1
    assert error_entries[0]["metric"] == "error"
    assert error_entries[0]["passed"] is False
    assert "openai: openai down" in error_entries[0]["reason"]
    assert "claude: claude down" in error_entries[0]["reason"]

    success_entries = [entry for entry in per_example if entry["example_id"] == "a2"]
    assert len(success_entries) == 5  # 4 Ragas metrics + E20's fabricated_citation_rate
    assert all(entry["provider"] == "openai" for entry in success_entries)


@pytest.mark.asyncio
async def test_examples_run_concurrently_up_to_max_concurrency(tmp_path: Path) -> None:
    """Proves two things at once: examples genuinely overlap in flight
    (not accidentally still sequential), and the overlap never exceeds
    `max_concurrency` -- an unbounded `asyncio.gather` over all 10
    examples would let `max_in_flight` hit 10, not stay capped at 3."""

    examples = [_answerable_example(f"a{i}") for i in range(10)]
    dataset_dir = _write_dataset(tmp_path, examples)

    in_flight = 0
    max_in_flight = 0

    async def _generate_side_effect(*, request: object, provider: object) -> GenerationResult:
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return _fake_result()

    generation_service = MagicMock()
    generation_service.generate = AsyncMock(side_effect=_generate_side_effect)

    benchmark = GoldenSetBenchmark(
        generation_service=generation_service,
        judge=_FakeJudge(),
        providers=[GenerationProvider.OPENAI],
        max_concurrency=3,
    )
    await benchmark.run(dataset_dir)

    assert 1 < max_in_flight <= 3


class _FakeRubricResult:
    def __init__(self, passed: bool, reason: str) -> None:
        self.passed = passed
        self.reason = reason


class _FakeRubricJudge:
    def __init__(self, *, passed: bool = True, reason: str = "satisfies the rubric") -> None:
        self.passed = passed
        self.reason = reason
        self.calls: list[dict[str, object]] = []

    async def ascore(self, *, question: str, answer: str, rubric: str) -> _FakeRubricResult:
        self.calls.append({"question": question, "answer": answer, "rubric": rubric})
        return _FakeRubricResult(self.passed, self.reason)


@pytest.mark.asyncio
async def test_rubric_adherence_is_scored_when_example_has_a_rubric_and_judge_is_wired(
    tmp_path: Path,
) -> None:
    dataset_dir = _write_dataset(
        tmp_path, [_answerable_example("a1", rubric="must mention the six components")]
    )
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())
    rubric_judge = _FakeRubricJudge(passed=False, reason="only mentions three of six")

    benchmark = GoldenSetBenchmark(
        generation_service=generation_service,
        judge=_FakeJudge(),
        providers=[GenerationProvider.OPENAI],
        rubric_judge=rubric_judge,
    )
    result = await benchmark.run(dataset_dir)

    per_example = result.candidates[0].notes[PER_EXAMPLE_SCORES_NOTE_KEY]
    rubric_entry = next(e for e in per_example if e["metric"] == "rubric_adherence")
    assert rubric_entry["passed"] is False
    assert rubric_entry["reason"] == "only mentions three of six"
    assert rubric_judge.calls == [
        {
            "question": "What is a1?",
            "answer": "a generated answer",
            "rubric": "must mention the six components",
        }
    ]


@pytest.mark.asyncio
async def test_rubric_adherence_absent_when_no_rubric_judge_wired(tmp_path: Path) -> None:
    """Backward-compat default: an example with a rubric but no
    rubric_judge configured (e.g. GoldenSetBenchmark built without one)
    must not error or silently fabricate a score."""

    dataset_dir = _write_dataset(tmp_path, [_answerable_example("a1", rubric="must be concise")])
    generation_service = MagicMock()
    generation_service.generate = AsyncMock(return_value=_fake_result())

    benchmark = GoldenSetBenchmark(
        generation_service=generation_service,
        judge=_FakeJudge(),
        providers=[GenerationProvider.OPENAI],
    )
    result = await benchmark.run(dataset_dir)

    per_example = result.candidates[0].notes[PER_EXAMPLE_SCORES_NOTE_KEY]
    assert "rubric_adherence" not in {e["metric"] for e in per_example}


def test_default_max_concurrency_is_five_when_not_specified() -> None:
    benchmark = GoldenSetBenchmark(
        generation_service=MagicMock(),
        judge=_FakeJudge(),
        providers=[GenerationProvider.OPENAI],
    )

    assert benchmark._max_concurrency == 5


def test_write_dataset_helper_round_trips_via_json(tmp_path: Path) -> None:
    """Sanity check on this file's own fixture helper, not the benchmark
    itself -- guards against a future edit silently breaking the
    load_golden_dataset() round trip every other test here depends on."""

    dataset_dir = _write_dataset(tmp_path, [_answerable_example(str(uuid4()))])
    raw = json.loads((dataset_dir / GOLDEN_DATASET_FILENAME).read_text())
    assert raw["examples"][0]["expected_behavior"] == "answer"
