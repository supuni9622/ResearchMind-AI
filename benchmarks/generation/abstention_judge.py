"""
Abstention-quality judge (`abstention_pass_rate`, `EVALUATION_PLAN.md`
§13's third absolute gate; also reused for E10's `abstention_failure`
category, §3's taxonomy). Checks whether a response to a question the
system should decline correctly abstains, rather than confidently
fabricating an answer -- the same check both consumers need, so it's
built once here, not twice.

**Cost, same shape as `rubric_judge.py`, deliberately not repeated
reasoning:** a fixed cheap model (`gpt-4o-mini`), never routed through
`GenerationService`/whatever `OPENAI_MODEL` is configured for real
answers. One bounded call per example.
"""

from __future__ import annotations

from typing import Protocol

from app.core.settings import settings
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

DEFAULT_ABSTENTION_JUDGE_MODEL = "gpt-4o-mini"
"""Matches `rubric_judge.DEFAULT_RUBRIC_JUDGE_MODEL` / `ragas_judge.
DEFAULT_JUDGE_MODEL` -- same cost tier as every other judge in this
project, one fewer model identity to reason about."""

_MAX_OUTPUT_TOKENS = 300

_SYSTEM_PROMPT = (
    "You judge whether an AI system's response correctly abstains from "
    "answering a question it should decline -- because the available "
    "evidence is insufficient, out of scope, or only superficially "
    "related. A correct abstention clearly declines or expresses "
    "appropriate uncertainty rather than confidently asserting an "
    "answer; fabricating a confident answer from unrelated or "
    "insufficient evidence is always a failure, even if that answer "
    "sounds plausible. Respond with a pass/fail decision and a short, "
    "actionable reason -- e.g. 'fail: confidently answered using an "
    "unrelated paper about X', not just a verdict."
)


class AbstentionJudgeResult(BaseModel):
    model_config = {"extra": "forbid"}

    reason: str = Field(min_length=1)
    passed: bool
    """True iff the response correctly abstained/declined."""


class AbstentionJudgeLike(Protocol):
    """Structural contract for this module's judge -- deliberately its
    own Protocol rather than a reuse of `ragas_scoring.RubricJudgeLike`:
    that Protocol requires a non-optional `rubric: str` (E16 only ever
    calls it for examples that already have one), whereas an abstention
    judge must work for examples with *no* `rubric` set too (most of
    them), falling back to a generic "insufficient evidence" criterion --
    a real, not cosmetic, difference in contract."""

    async def ascore(
        self, *, question: str, answer: str, rubric: str | None = None
    ) -> AbstentionJudgeResult: ...


class AbstentionJudge:
    """Real, network-calling judge. Satisfies `AbstentionJudgeLike` above --
    the `rubric` parameter carries an abstention-specific criterion (e.g.
    a golden example's own `rubric` field, when it has one) rather than a
    completeness/tone criterion, and is optional here unlike E16's rubric
    judge."""

    def __init__(self, *, client: AsyncOpenAI, model: str = DEFAULT_ABSTENTION_JUDGE_MODEL) -> None:
        self._client = client
        self._model = model

    async def ascore(
        self, *, question: str, answer: str, rubric: str | None = None
    ) -> AbstentionJudgeResult:
        criterion = (
            rubric or "The available evidence does not support a confident answer to this question."
        )
        completion = await self._client.chat.completions.parse(
            model=self._model,
            temperature=0.0,
            max_completion_tokens=_MAX_OUTPUT_TOKENS,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Question: {question}\n\n"
                        f"Why this should be declined: {criterion}\n\n"
                        f"Response: {answer}\n\n"
                        "Did the response correctly abstain?"
                    ),
                },
            ],
            response_format=AbstentionJudgeResult,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("Abstention judge did not return a schema-valid decision.")
        return parsed


def build_abstention_judge(*, model: str = DEFAULT_ABSTENTION_JUDGE_MODEL) -> AbstentionJudge:
    """Mirrors `rubric_judge.build_rubric_judge()`'s exact reasoning: a
    missing key should be a loud failure, not a silent skip."""

    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required to build the abstention judge "
            "(EVALUATION_IMPLEMENTATION_TRACKER.md E20/E10 follow-up)."
        )

    return AbstentionJudge(client=AsyncOpenAI(api_key=settings.openai_api_key), model=model)


__all__ = [
    "DEFAULT_ABSTENTION_JUDGE_MODEL",
    "AbstentionJudge",
    "AbstentionJudgeLike",
    "AbstentionJudgeResult",
    "build_abstention_judge",
]
