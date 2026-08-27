"""Unit tests for the pure online-scoring sampling decision (E5, EVALUATION_PLAN.md §14)."""

from __future__ import annotations

from app.ai.guardrails.enums import GuardrailAction
from app.ai.runtime.generation.online_scoring.sampling import (
    OnlineScoringConfig,
    SamplingCategory,
    decide_sampling,
)
from app.ai.runtime.research.review import ReviewDecision


def _config(**overrides: object) -> OnlineScoringConfig:
    defaults: dict[str, object] = {
        "baseline_sample_rate": 0.1,
        "canary_oversample_rate": 0.5,
        "canary_prompt_version": None,
    }
    defaults.update(overrides)
    return OnlineScoringConfig(**defaults)


def test_guardrail_flagged_takes_priority_over_everything_else() -> None:
    decision = decide_sampling(
        guardrail_final_action=GuardrailAction.WARN.value,
        review_decision=ReviewDecision.PASS.value,
        prompt_version="canary-v2",
        config=_config(canary_prompt_version="canary-v2", baseline_sample_rate=0.0),
        random_value=0.99,
    )

    assert decision.category == SamplingCategory.GUARDRAIL_FLAGGED
    assert decision.should_score_judges is True


def test_allow_final_action_is_not_flagged() -> None:
    decision = decide_sampling(
        guardrail_final_action=GuardrailAction.ALLOW.value,
        review_decision=None,
        prompt_version=None,
        config=_config(baseline_sample_rate=0.0),
        random_value=0.99,
    )

    assert decision.category != SamplingCategory.GUARDRAIL_FLAGGED


def test_none_guardrail_action_is_not_flagged() -> None:
    """`None` means guardrails never ran for this call -- not evaluated,
    distinct from a known-safe `allow`; either way it's not "flagged"."""

    decision = decide_sampling(
        guardrail_final_action=None,
        review_decision=None,
        prompt_version=None,
        config=_config(baseline_sample_rate=0.0),
        random_value=0.99,
    )

    assert decision.category != SamplingCategory.GUARDRAIL_FLAGGED


def test_non_pass_review_decision_is_always_scored() -> None:
    decision = decide_sampling(
        guardrail_final_action=GuardrailAction.ALLOW.value,
        review_decision=ReviewDecision.REVISE_SYNTHESIS.value,
        prompt_version=None,
        config=_config(baseline_sample_rate=0.0),
        random_value=0.99,
    )

    assert decision.category == SamplingCategory.NON_PASS_REVIEW
    assert decision.should_score_judges is True


def test_pass_review_decision_is_not_flagged() -> None:
    decision = decide_sampling(
        guardrail_final_action=None,
        review_decision=ReviewDecision.PASS.value,
        prompt_version=None,
        config=_config(baseline_sample_rate=0.0),
        random_value=0.99,
    )

    assert decision.category != SamplingCategory.NON_PASS_REVIEW


def test_review_decision_only_applies_to_deep_research_rows_via_none() -> None:
    """Chat/Linear Research rows pass `review_decision=None` (no review
    step exists for those surfaces) -- must never be misread as PASS or
    as a flag."""

    decision = decide_sampling(
        guardrail_final_action=None,
        review_decision=None,
        prompt_version=None,
        config=_config(baseline_sample_rate=0.0),
        random_value=0.99,
    )

    assert decision.category == SamplingCategory.NOT_SAMPLED


def test_canary_window_oversamples_when_prompt_version_matches() -> None:
    decision = decide_sampling(
        guardrail_final_action=None,
        review_decision=None,
        prompt_version="chat-v2",
        config=_config(canary_prompt_version="chat-v2", canary_oversample_rate=0.5),
        random_value=0.4,
    )

    assert decision.category == SamplingCategory.CONFIG_CANARY
    assert decision.should_score_judges is True


def test_canary_window_does_not_fire_above_its_oversample_rate() -> None:
    decision = decide_sampling(
        guardrail_final_action=None,
        review_decision=None,
        prompt_version="chat-v2",
        config=_config(
            canary_prompt_version="chat-v2", canary_oversample_rate=0.5, baseline_sample_rate=0.0
        ),
        random_value=0.6,
    )

    assert decision.category == SamplingCategory.NOT_SAMPLED


def test_non_matching_prompt_version_does_not_enter_canary_window() -> None:
    decision = decide_sampling(
        guardrail_final_action=None,
        review_decision=None,
        prompt_version="chat-v1",
        config=_config(
            canary_prompt_version="chat-v2", canary_oversample_rate=1.0, baseline_sample_rate=0.0
        ),
        random_value=0.01,
    )

    assert decision.category == SamplingCategory.NOT_SAMPLED


def test_baseline_sampling_fires_below_the_configured_rate() -> None:
    decision = decide_sampling(
        guardrail_final_action=None,
        review_decision=None,
        prompt_version=None,
        config=_config(baseline_sample_rate=0.1),
        random_value=0.05,
    )

    assert decision.category == SamplingCategory.BASELINE_SAMPLED
    assert decision.should_score_judges is True


def test_baseline_sampling_misses_above_the_configured_rate() -> None:
    decision = decide_sampling(
        guardrail_final_action=None,
        review_decision=None,
        prompt_version=None,
        config=_config(baseline_sample_rate=0.1),
        random_value=0.5,
    )

    assert decision.category == SamplingCategory.NOT_SAMPLED
    assert decision.should_score_judges is False


def test_canary_window_takes_priority_over_baseline_even_when_baseline_would_have_missed() -> None:
    decision = decide_sampling(
        guardrail_final_action=None,
        review_decision=None,
        prompt_version="chat-v2",
        config=_config(
            canary_prompt_version="chat-v2", canary_oversample_rate=0.9, baseline_sample_rate=0.01
        ),
        random_value=0.5,
    )

    assert decision.category == SamplingCategory.CONFIG_CANARY
