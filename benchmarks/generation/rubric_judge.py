"""
Rubric-adherence judge (E16, `PRIORITIZED_ROADMAP.md` Wave 1 row 16 --
roadmap-only addition, consistent with `PHASE_2_3_ROADMAP.md` Part 3
items 4/10/11). Covers the one dimension Ragas's fixed metric set
doesn't: does the answer satisfy an example-specific rubric (tone,
completeness against named requirements) -- the `rubric` field already
in `EVALUATION_PLAN.md` §3's schema, previously written but never read
by anything.

**Cost, deliberately bounded, not an afterthought:**
- Only ever runs when a golden example actually has a `rubric` set (12 of
  115 in `rag_answer_gold.json` as of 2026-08-12; `production_failures.json`
  examples can carry one too via `sync_promoted_examples.py`, but that
  file starts empty). Sampled production traffic has no rubric concept at
  all, so this judge never runs there -- see `ragas_scoring.score_generation()`'s
  own docstring for why that's structurally guaranteed, not just a
  convention.
- Deliberately **not** routed through `GenerationService`/the provider
  registry, which would use whichever model `OPENAI_MODEL` happens to be
  configured to for real answers (a genuinely more expensive model in
  practice, e.g. this deployment's own `.env` at the time this was
  written) -- a judge's cost should never silently track the answer
  model's cost. Calls OpenAI directly with a fixed, cheap model
  (`DEFAULT_RUBRIC_JUDGE_MODEL`), matching `ragas_judge.py`'s own
  `DEFAULT_JUDGE_MODEL` exactly -- same reasoning, same cost tier, one
  fewer model identity to reason about.
- One bounded call per example (max_tokens capped, temperature 0), same
  shape as `app/.../comment_classification/service.py`'s judge pattern.
"""

from __future__ import annotations

from app.core.settings import settings
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

DEFAULT_RUBRIC_JUDGE_MODEL = "gpt-4o-mini"
"""Matches `ragas_judge.DEFAULT_JUDGE_MODEL` -- same cost tier as the
Ragas judges, deliberately not this deployment's real-answer model."""

_MAX_OUTPUT_TOKENS = 300
"""Generous relative to the schema's tiny worst case (~50-80 tokens for
a bool + one-sentence reason) -- matches
`comment_classification/service.py`'s sizing rationale for the same
class of bounded judge call."""

_SYSTEM_PROMPT = (
    "You judge whether an AI-generated answer satisfies one specific rubric "
    "criterion for a golden evaluation example. Respond with a pass/fail "
    "decision and a short, actionable reason a reviewer can read -- e.g. "
    "'fail: missing two of the four named roles the rubric requires', not "
    "just a verdict. Judge only the stated criterion, not general answer "
    "quality."
)


class RubricJudgeResult(BaseModel):
    model_config = {"extra": "forbid"}

    # `reason` declared before `passed` deliberately: structured/JSON-
    # schema output is generated in field order, so this asks the model
    # to reason through the evidence *before* committing to a verdict --
    # standard "reasoning before verdict" practice, since the reverse
    # order lets the model state a verdict first and then write a reason
    # that merely justifies it rather than one that derived it.
    reason: str = Field(min_length=1)
    passed: bool


class RubricJudge:
    """Real, network-calling judge for the `rubric` field on a golden
    example. Structurally satisfies `ragas_scoring.RubricJudgeLike`."""

    def __init__(self, *, client: AsyncOpenAI, model: str = DEFAULT_RUBRIC_JUDGE_MODEL) -> None:
        self._client = client
        self._model = model

    async def ascore(self, *, question: str, answer: str, rubric: str) -> RubricJudgeResult:
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
                        f"Answer: {answer}\n\n"
                        f"Rubric criterion: {rubric}\n\n"
                        "Does the answer satisfy this rubric criterion?"
                    ),
                },
            ],
            response_format=RubricJudgeResult,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("Rubric judge did not return a schema-valid decision.")
        return parsed


def build_rubric_judge(*, model: str = DEFAULT_RUBRIC_JUDGE_MODEL) -> RubricJudge:
    """
    Raises if no OpenAI key is configured rather than silently degrading
    -- mirrors `ragas_judge.build_openai_ragas_judge()`'s exact reasoning:
    judge identity matters for reproducibility, so a missing key should
    be loud, not a silent skip.
    """

    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required to build the rubric judge (E16, "
            "EVALUATION_IMPLEMENTATION_TRACKER.md)."
        )

    return RubricJudge(client=AsyncOpenAI(api_key=settings.openai_api_key), model=model)


__all__ = [
    "DEFAULT_RUBRIC_JUDGE_MODEL",
    "RubricJudge",
    "RubricJudgeResult",
    "build_rubric_judge",
]
