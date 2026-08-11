"""
Ragas LLM-judge scoring function (EVALUATION_PLAN.md §7's release-candidate
tier, §18 Level 1) -- `benchmarks/generation/ragas_scoring.score_generation()`
and the `rag_answer_gold` golden dataset it scores against.

No live LLM/embedding calls are made anywhere in this file -- `score_generation()`
is tested against a fake `GenerationJudge` (a plain object satisfying the
structural `Protocol`, no `ragas` import needed at all -- see
`ragas_scoring.py`'s own module docstring for why that separation exists).
This also means these tests never require `OPENAI_API_KEY` to be set.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from benchmarks.generation.golden_dataset import (
    ExpectedBehavior,
    QueryType,
    Workflow,
    load_golden_dataset,
)
from benchmarks.generation.ragas_scoring import (
    PROVISIONAL_PASS_THRESHOLD,
    score_generation,
)

GOLDEN_DATASET_PATH = (
    Path(__file__).resolve().parents[2] / "datasets" / "golden" / "rag_answer_gold.json"
)


class _FakeMetricResult:
    def __init__(self, value: float, reason: str | None = None) -> None:
        self.value = value
        self.reason = reason

    def __float__(self) -> float:
        return self.value


class _RecordingFake:
    """Shared call-recording behavior for the four fakes below."""

    def __init__(self, score: float, reason: str | None = None) -> None:
        self.score = score
        self.reason = reason
        self.calls: list[dict[str, object]] = []

    def _result(self) -> _FakeMetricResult:
        return _FakeMetricResult(self.score, self.reason)


# Four distinct fakes, not one generic `**kwargs` fake -- each matches its
# real ragas metric's exact `ascore` signature (see `ragas_scoring.py`'s
# comment on `_FaithfulnessLike`/etc. for why a shared `**kwargs: object`
# signature doesn't satisfy mypy's Protocol method matching here).
class _FakeFaithfulness(_RecordingFake):
    async def ascore(
        self, user_input: str, response: str, retrieved_contexts: list[str]
    ) -> _FakeMetricResult:
        self.calls.append(
            {
                "user_input": user_input,
                "response": response,
                "retrieved_contexts": retrieved_contexts,
            }
        )
        return self._result()


class _FakeAnswerRelevancy(_RecordingFake):
    async def ascore(self, user_input: str, response: str) -> _FakeMetricResult:
        self.calls.append({"user_input": user_input, "response": response})
        return self._result()


class _FakeContextPrecision(_RecordingFake):
    async def ascore(
        self, user_input: str, reference: str, retrieved_contexts: list[str]
    ) -> _FakeMetricResult:
        self.calls.append(
            {
                "user_input": user_input,
                "reference": reference,
                "retrieved_contexts": retrieved_contexts,
            }
        )
        return self._result()


class _FakeContextRecall(_RecordingFake):
    async def ascore(
        self, user_input: str, retrieved_contexts: list[str], reference: str
    ) -> _FakeMetricResult:
        self.calls.append(
            {
                "user_input": user_input,
                "retrieved_contexts": retrieved_contexts,
                "reference": reference,
            }
        )
        return self._result()


class _FakeJudge:
    def __init__(
        self,
        *,
        faithfulness: float = 0.9,
        answer_relevancy: float = 0.9,
        context_precision: float = 0.9,
        context_recall: float = 0.9,
    ) -> None:
        self.faithfulness = _FakeFaithfulness(faithfulness)
        self.answer_relevancy = _FakeAnswerRelevancy(answer_relevancy)
        self.context_precision = _FakeContextPrecision(context_precision)
        self.context_recall = _FakeContextRecall(context_recall)


# -- score_generation() contract -----------------------------------------


@pytest.mark.asyncio
async def test_full_suite_runs_when_context_and_reference_are_both_present() -> None:
    judge = _FakeJudge()

    report = await score_generation(
        question="What are the six components?",
        answer="Goal representation, state model, action executor.",
        contexts=["The six-component framework consists of..."],
        reference="Goal representation, state model, action executor, ...",
        judge=judge,
    )

    computed = {check.metric for check in report.checks}
    assert computed == {"faithfulness", "answer_relevancy", "context_precision", "context_recall"}
    assert report.skipped_metrics == []
    assert report.passed


@pytest.mark.asyncio
async def test_chat_no_context_exception_only_runs_answer_relevancy() -> None:
    """EVALUATION_PLAN.md §7: Chat with no retrieved context has nothing to
    be faithful to -- only answer_relevancy is meaningful."""

    judge = _FakeJudge()

    report = await score_generation(
        question="What is the capital of France?",
        answer="Paris.",
        contexts=[],
        reference=None,
        judge=judge,
    )

    computed = {check.metric for check in report.checks}
    assert computed == {"answer_relevancy"}
    assert set(report.skipped_metrics) == {"faithfulness", "context_precision", "context_recall"}
    assert judge.faithfulness.calls == []
    assert judge.context_precision.calls == []
    assert judge.context_recall.calls == []


@pytest.mark.asyncio
async def test_context_precision_and_recall_skipped_without_a_reference_answer() -> None:
    """Most golden-set examples have a reference_answer; sampled production
    traces rarely do (EVALUATION_PLAN.md §7's Mature-tier note) -- both
    reference-dependent metrics must degrade gracefully, not crash."""

    judge = _FakeJudge()

    report = await score_generation(
        question="Summarize this document.",
        answer="It's about loop engineering.",
        contexts=["Loop engineering is a framework for AI agents."],
        reference=None,
        judge=judge,
    )

    computed = {check.metric for check in report.checks}
    assert computed == {"faithfulness", "answer_relevancy"}
    assert set(report.skipped_metrics) == {"context_precision", "context_recall"}


@pytest.mark.asyncio
async def test_report_fails_when_any_computed_check_falls_below_threshold() -> None:
    judge = _FakeJudge(faithfulness=0.1)

    report = await score_generation(
        question="q",
        answer="a fabricated answer",
        contexts=["real context"],
        reference=None,
        judge=judge,
    )

    faithfulness_check = next(c for c in report.checks if c.metric == "faithfulness")
    assert not faithfulness_check.passed
    assert faithfulness_check.score < PROVISIONAL_PASS_THRESHOLD
    assert not report.passed


@pytest.mark.asyncio
async def test_skipped_metrics_do_not_count_against_the_overall_pass() -> None:
    """A no-context Chat turn that scores well on answer_relevancy should
    pass overall -- the three skipped metrics aren't failures, they're N/A."""

    judge = _FakeJudge(answer_relevancy=0.95)

    report = await score_generation(
        question="q", answer="a", contexts=[], reference=None, judge=judge
    )

    assert report.passed


@pytest.mark.asyncio
async def test_judge_provided_reason_is_surfaced_verbatim() -> None:
    judge = _FakeJudge()
    judge.faithfulness.reason = "fail — cites a claim not present in the retrieved context"

    report = await score_generation(
        question="q", answer="a", contexts=["c"], reference=None, judge=judge
    )

    faithfulness_check = next(c for c in report.checks if c.metric == "faithfulness")
    assert faithfulness_check.reason == "fail — cites a claim not present in the retrieved context"


@pytest.mark.asyncio
async def test_missing_reason_falls_back_to_a_synthesized_one_referencing_the_score() -> None:
    judge = _FakeJudge(faithfulness=0.42)

    report = await score_generation(
        question="q", answer="a", contexts=["c"], reference=None, judge=judge
    )

    faithfulness_check = next(c for c in report.checks if c.metric == "faithfulness")
    assert "0.42" in faithfulness_check.reason


@pytest.mark.asyncio
async def test_metrics_are_called_with_the_expected_arguments() -> None:
    judge = _FakeJudge()

    await score_generation(
        question="What are the components?",
        answer="Goal, state, action.",
        contexts=["ctx-1"],
        reference="ref-answer",
        judge=judge,
    )

    assert judge.faithfulness.calls[0] == {
        "user_input": "What are the components?",
        "response": "Goal, state, action.",
        "retrieved_contexts": ["ctx-1"],
    }
    assert judge.answer_relevancy.calls[0] == {
        "user_input": "What are the components?",
        "response": "Goal, state, action.",
    }
    assert judge.context_precision.calls[0] == {
        "user_input": "What are the components?",
        "reference": "ref-answer",
        "retrieved_contexts": ["ctx-1"],
    }
    assert judge.context_recall.calls[0] == {
        "user_input": "What are the components?",
        "retrieved_contexts": ["ctx-1"],
        "reference": "ref-answer",
    }


# -- rag_answer_gold contract ----------------------------------------------


@pytest.fixture(scope="module")
def golden_dataset():
    return load_golden_dataset(GOLDEN_DATASET_PATH)


def test_golden_dataset_meets_the_minimum_size_for_phase_1(golden_dataset) -> None:
    """
    Not yet at EVALUATION_PLAN.md §3's 50-150 target -- see
    EVALUATION_IMPLEMENTATION_TRACKER.md E1 for why. This floor just
    guards against silent shrinkage below Phase 1's real, deliberate size.
    """

    assert len(golden_dataset.examples) >= 20


def test_golden_dataset_covers_every_query_type(golden_dataset) -> None:
    covered = {example.query_type for example in golden_dataset.examples}

    assert covered == set(QueryType)


def test_golden_dataset_covers_every_workflow(golden_dataset) -> None:
    covered = {example.workflow for example in golden_dataset.examples}

    assert covered == set(Workflow)


def test_unanswerable_examples_expect_abstention_and_carry_no_reference_answer(
    golden_dataset,
) -> None:
    unanswerable = [
        example
        for example in golden_dataset.examples
        if example.query_type == QueryType.UNANSWERABLE
    ]

    assert unanswerable
    for example in unanswerable:
        assert example.expected_behavior == ExpectedBehavior.ABSTAIN
        assert example.reference_answer is None
        assert example.contexts == []


def test_answerable_examples_carry_a_reference_answer_and_contexts(golden_dataset) -> None:
    answerable = [
        example
        for example in golden_dataset.examples
        if example.expected_behavior == ExpectedBehavior.ANSWER
    ]

    assert answerable
    for example in answerable:
        assert example.reference_answer
        assert example.contexts


@pytest.mark.asyncio
async def test_score_generation_runs_against_every_answerable_golden_example(
    golden_dataset,
) -> None:
    """
    End-to-end contract check: every answerable example in the real
    dataset can actually be scored by `score_generation()` without
    raising, using a fake judge standing in for the real LLM call.
    """

    judge = _FakeJudge()

    for example in golden_dataset.examples:
        if example.expected_behavior != ExpectedBehavior.ANSWER:
            continue

        report = await score_generation(
            question=example.question,
            answer=example.reference_answer or "",
            contexts=example.contexts,
            reference=example.reference_answer,
            judge=judge,
        )

        assert report.checks
