from __future__ import annotations

#
# PRD §15 weights. `runtime` is included for when runtime validators
# ship (PRD §11) even though no stage populates it yet — see
# `compute_overall_score`.
#

STAGE_WEIGHTS: dict[str, float] = {
    "input": 0.15,
    "output": 0.35,
    "hallucination": 0.30,
    "runtime": 0.20,
}


def compute_overall_score(
    *,
    input_score: float | None,
    output_score: float | None,
    hallucination_score: float | None,
    runtime_score: float | None = None,
) -> float | None:
    """
    Weighted average of whichever stage scores are actually available.

    Stages with no score (most validators only emit issues, not a
    score — see `ValidatorOutcome`) are dropped and the remaining
    weights renormalized, rather than treating a missing score as 0.
    Returns `None` when no stage produced a score at all.
    """

    scores = {
        "input": input_score,
        "output": output_score,
        "hallucination": hallucination_score,
        "runtime": runtime_score,
    }

    available = {stage: score for stage, score in scores.items() if score is not None}

    if not available:
        return None

    total_weight = sum(STAGE_WEIGHTS[stage] for stage in available)

    if total_weight == 0:
        return None

    return sum(score * STAGE_WEIGHTS[stage] for stage, score in available.items()) / total_weight
