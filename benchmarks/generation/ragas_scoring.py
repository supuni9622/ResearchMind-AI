"""
Generation scoring function (EVALUATION_PLAN.md §7, §16 phase 1).

Given a `(question, contexts, answer[, reference])` tuple, runs Ragas's
faithfulness/answer_relevancy/context_precision/context_recall and
returns scores in the pass/fail + reason shape §18 mandates for judges --
Ragas's own `MetricResult` already carries an optional judge-written
`reason`; this is surfaced rather than discarded down to a bare float.

`score_generation()` depends on `GenerationJudge`, a structural
`Protocol` -- not the concrete `ragas`-backed `RagasJudge`
(`ragas_judge.py`). This is deliberate: it keeps this module's actual
scoring/reporting logic (the part worth unit-testing) importable and
testable with a lightweight fake judge, with no dependency on `ragas`
itself or a live LLM call. `ragas_judge.py` is where the real,
network-calling implementation lives; only callers that need a real
judge import it.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

PROVISIONAL_PASS_THRESHOLD = 0.5
"""
Uncalibrated pass/fail cutoff, deliberately conservative and explicitly
provisional. EVALUATION_PLAN.md §13: "Don't set an arbitrary target like
'faithfulness must exceed 0.90' before calibrating judges against human
labels." This threshold exists only so `MetricCheckResult.passed` has a
value at all before that calibration work (§17/§18, Mature tier) happens
-- revisit once real production volume exists to calibrate against.
"""


class _MetricResultLike(Protocol):
    """Structurally matches `ragas.metrics.result.MetricResult` -- a
    float-convertible score with an optional judge-written reason."""

    def __float__(self) -> float: ...

    reason: str | None


# Four separate Protocols, not one shared `ascore(**kwargs)` -- each real
# ragas metric class declares a genuinely different, specific `ascore`
# signature (checked against ragas 0.4.3 directly: `Faithfulness.ascore`
# takes `user_input, response, retrieved_contexts`; `AnswerRelevancy.ascore`
# takes only `user_input, response`; `ContextPrecision`/`ContextRecall`
# take `reference` plus `retrieved_contexts` in different orders). A
# generic `**kwargs: object` signature doesn't structurally satisfy any
# of these under mypy's Protocol method matching (verified empirically --
# `**kwargs: object` is not accepted as a substitute for named,
# positional-or-keyword parameters), so the precise shapes are declared
# here instead.
class _FaithfulnessLike(Protocol):
    async def ascore(
        self, user_input: str, response: str, retrieved_contexts: list[str]
    ) -> _MetricResultLike: ...


class _AnswerRelevancyLike(Protocol):
    async def ascore(self, user_input: str, response: str) -> _MetricResultLike: ...


class _ContextPrecisionLike(Protocol):
    async def ascore(
        self, user_input: str, reference: str, retrieved_contexts: list[str]
    ) -> _MetricResultLike: ...


class _ContextRecallLike(Protocol):
    async def ascore(
        self, user_input: str, retrieved_contexts: list[str], reference: str
    ) -> _MetricResultLike: ...


class GenerationJudge(Protocol):
    """
    Structural contract for anything that can score a generation --
    satisfied by `ragas_judge.RagasJudge` without importing it, and by
    any test double with the same four attributes.

    Declared as read-only properties, not plain attributes: mypy checks
    plain Protocol attributes invariantly (a consumer could reassign
    them), which rejects a structurally-compatible-but-not-identical
    fake type in tests. Properties are read-only, so mypy checks them
    covariantly instead -- exactly what's needed here, since nothing
    ever assigns to `judge.faithfulness` etc.
    """

    @property
    def faithfulness(self) -> _FaithfulnessLike: ...

    @property
    def answer_relevancy(self) -> _AnswerRelevancyLike: ...

    @property
    def context_precision(self) -> _ContextPrecisionLike: ...

    @property
    def context_recall(self) -> _ContextRecallLike: ...


class MetricCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    score: float = Field(ge=0, le=1)
    passed: bool
    reason: str


class GenerationScoreReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checks: list[MetricCheckResult]

    skipped_metrics: list[str] = Field(default_factory=list)
    """
    Metrics not computed for this example -- e.g. all three context-
    dependent metrics for a no-context Chat turn (§7's exception), or
    just context_precision/context_recall when no `reference_answer`
    exists to compare against.
    """

    passed: bool
    """True iff every *computed* check passed. Skipped metrics don't
    count against this -- there's nothing to fail if it was never
    computable for this example."""


def _to_check(name: str, result: _MetricResultLike) -> MetricCheckResult:
    score = float(result)
    reason = getattr(result, "reason", None) or (
        f"{name} scored {score:.2f} against the provisional, uncalibrated "
        f"pass threshold of {PROVISIONAL_PASS_THRESHOLD:.2f} (EVALUATION_PLAN.md §18)."
    )
    return MetricCheckResult(
        metric=name,
        score=score,
        passed=score >= PROVISIONAL_PASS_THRESHOLD,
        reason=reason,
    )


async def score_generation(
    *,
    question: str,
    answer: str,
    contexts: list[str],
    reference: str | None,
    judge: GenerationJudge,
) -> GenerationScoreReport:
    """
    Score one generation against the full Ragas RAG suite where
    computable, degrading gracefully otherwise:

    - `answer_relevancy` always runs -- needs only the question and answer.
    - `faithfulness`/`context_precision`/`context_recall` need retrieved
      context; skipped entirely when `contexts` is empty (§7's Chat
      no-tool-use exception -- there's no retrieved context to be
      faithful to, so faithfulness/precision/recall aren't meaningful,
      not just unavailable).
    - `context_precision`/`context_recall` additionally need a
      `reference` answer to compare against; skipped when none exists
      (most golden-set examples have one, sampled production traces
      rarely do -- EVALUATION_PLAN.md §7's Mature-tier note).
    """

    checks = [
        _to_check(
            "answer_relevancy",
            await judge.answer_relevancy.ascore(
                user_input=question,
                response=answer,
            ),
        )
    ]

    if not contexts:
        return GenerationScoreReport(
            checks=checks,
            skipped_metrics=["faithfulness", "context_precision", "context_recall"],
            passed=all(check.passed for check in checks),
        )

    checks.append(
        _to_check(
            "faithfulness",
            await judge.faithfulness.ascore(
                user_input=question,
                response=answer,
                retrieved_contexts=contexts,
            ),
        )
    )

    skipped: list[str] = []

    if reference:
        checks.append(
            _to_check(
                "context_precision",
                await judge.context_precision.ascore(
                    user_input=question,
                    reference=reference,
                    retrieved_contexts=contexts,
                ),
            )
        )
        checks.append(
            _to_check(
                "context_recall",
                await judge.context_recall.ascore(
                    user_input=question,
                    retrieved_contexts=contexts,
                    reference=reference,
                ),
            )
        )
    else:
        skipped.extend(["context_precision", "context_recall"])

    return GenerationScoreReport(
        checks=checks,
        skipped_metrics=skipped,
        passed=all(check.passed for check in checks),
    )


__all__ = [
    "PROVISIONAL_PASS_THRESHOLD",
    "GenerationJudge",
    "GenerationScoreReport",
    "MetricCheckResult",
    "score_generation",
]
