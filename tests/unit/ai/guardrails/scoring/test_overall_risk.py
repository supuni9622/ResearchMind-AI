from __future__ import annotations

from app.ai.guardrails.scoring.overall_risk import compute_overall_risk


def test_returns_none_when_no_stage_scored() -> None:
    assert (
        compute_overall_risk(
            input_score=None,
            retrieval_score=None,
            generation_score=None,
            runtime_score=None,
        )
        is None
    )


def test_weighted_average_when_all_stages_present() -> None:
    risk = compute_overall_risk(
        input_score=1.0,
        retrieval_score=1.0,
        generation_score=1.0,
        runtime_score=1.0,
    )

    assert risk == 1.0


def test_renormalizes_over_available_stages() -> None:
    # Only input (weight .30) has a score -- renormalized, it should
    # fully determine the result rather than being diluted as if the
    # missing stages contributed 0.
    risk = compute_overall_risk(
        input_score=0.5,
        retrieval_score=None,
        generation_score=None,
        runtime_score=None,
    )

    assert risk == 0.5


def test_mixed_scores_are_weighted_correctly() -> None:
    risk = compute_overall_risk(
        input_score=1.0,
        retrieval_score=0.0,
        generation_score=None,
        runtime_score=None,
    )

    # renormalized over input(.30) + retrieval(.30) => equal weight
    assert risk == 0.5
