"""
Unit tests for compute_overall_score.

Covers:
- All four stage scores present -> full weighted average
- No scores at all -> None
- Only some stages scored -> weights renormalized over the ones present
  (a single 1.0 score should return 1.0 regardless of that stage's raw
  weight, since it's the only contributor)
- runtime_score, though no validator produces it today, still
  participates in the formula if supplied
"""

from __future__ import annotations

import pytest
from app.ai.runtime.generation.validation.scoring import compute_overall_score


def test_returns_none_when_no_scores_present() -> None:
    assert (
        compute_overall_score(
            input_score=None,
            output_score=None,
            hallucination_score=None,
        )
        is None
    )


def test_weighted_average_with_all_stages_present() -> None:
    score = compute_overall_score(
        input_score=1.0,
        output_score=1.0,
        hallucination_score=1.0,
        runtime_score=1.0,
    )

    assert score == 1.0


def test_renormalizes_over_only_the_stages_that_scored() -> None:
    # Only output scored; its weight (0.35) is the only one in the
    # denominator, so the lone score should pass through unchanged.
    score = compute_overall_score(
        input_score=None,
        output_score=0.8,
        hallucination_score=None,
    )

    assert score == pytest.approx(0.8)


def test_two_present_stages_are_weighted_relative_to_each_other() -> None:
    # output weight 0.35, hallucination weight 0.30 -> output should
    # pull the average slightly toward itself.
    score = compute_overall_score(
        input_score=None,
        output_score=1.0,
        hallucination_score=0.0,
    )

    assert score is not None
    assert 0.5 < score < 0.55


def test_runtime_score_participates_when_supplied() -> None:
    score = compute_overall_score(
        input_score=None,
        output_score=None,
        hallucination_score=None,
        runtime_score=0.4,
    )

    assert score == pytest.approx(0.4)
