"""
Sampling-decision function for online scoring (EVALUATION_PLAN.md §14).

Deliberately pure and side-effect-free: `decide_sampling()` takes plain
values plus an injected `random_value` rather than calling `random()`
itself, so every priority-order branch is exercised by unit tests without
mocking randomness. `OnlineScoringJob` is the only real caller.
"""

from __future__ import annotations

from enum import StrEnum

from app.ai.guardrails.enums import GuardrailAction
from app.ai.runtime.research.review import ReviewDecision
from pydantic import BaseModel, ConfigDict, Field


class SamplingCategory(StrEnum):
    """
    Why a generation was (or wasn't) selected for LLM-judge scoring.
    Checked in priority order in `decide_sampling()` -- the first
    matching category wins, matching §14's "100% for whatever's already
    free" framing: a guardrail-flagged, non-PASS-reviewed request is
    scored for that reason even if it would *also* have hit the flat
    baseline roll.
    """

    GUARDRAIL_FLAGGED = "guardrail_flagged"
    NON_PASS_REVIEW = "non_pass_review"
    CONFIG_CANARY = "config_canary"
    BASELINE_SAMPLED = "baseline_sampled"
    NOT_SAMPLED = "not_sampled"


class OnlineScoringConfig(BaseModel):
    """Mirrors `Settings`' `eval_online_*` fields -- kept as a separate,
    plain model so `decide_sampling()` has no dependency on `app.core.
    settings` and stays trivially constructible in tests."""

    model_config = ConfigDict(extra="forbid")

    baseline_sample_rate: float = Field(default=0.075, ge=0.0, le=1.0)
    canary_oversample_rate: float = Field(default=0.5, ge=0.0, le=1.0)
    canary_prompt_version: str | None = None


class SamplingDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: SamplingCategory
    should_score_judges: bool
    reason: str


def decide_sampling(
    *,
    guardrail_final_action: str | None,
    review_decision: str | None,
    prompt_version: str | None,
    config: OnlineScoringConfig,
    random_value: float,
) -> SamplingDecision:
    """
    Free deterministic checks (citation validity, schema validity) are
    not gated by this function at all -- per §14 they run on 100% of
    traffic unconditionally, so `OnlineScoringJob` runs them regardless
    of what this returns. This function only decides whether the
    (comparatively expensive) LLM-judge suite also runs for a given
    generation.
    """

    if guardrail_final_action is not None and guardrail_final_action != GuardrailAction.ALLOW.value:
        return SamplingDecision(
            category=SamplingCategory.GUARDRAIL_FLAGGED,
            should_score_judges=True,
            reason=f"guardrail final_action={guardrail_final_action!r}, always scored",
        )

    if review_decision is not None and review_decision != ReviewDecision.PASS.value:
        return SamplingDecision(
            category=SamplingCategory.NON_PASS_REVIEW,
            should_score_judges=True,
            reason=f"review decision={review_decision!r}, always scored",
        )

    in_canary_window = (
        config.canary_prompt_version is not None and prompt_version == config.canary_prompt_version
    )
    if in_canary_window and random_value < config.canary_oversample_rate:
        return SamplingDecision(
            category=SamplingCategory.CONFIG_CANARY,
            should_score_judges=True,
            reason=(
                f"prompt_version={prompt_version!r} is in the canary window, "
                f"oversampled at {config.canary_oversample_rate:.2f}"
            ),
        )

    if random_value < config.baseline_sample_rate:
        return SamplingDecision(
            category=SamplingCategory.BASELINE_SAMPLED,
            should_score_judges=True,
            reason=f"flat baseline roll at {config.baseline_sample_rate:.3f}",
        )

    return SamplingDecision(
        category=SamplingCategory.NOT_SAMPLED,
        should_score_judges=False,
        reason="no free signal fired and the baseline roll missed",
    )
