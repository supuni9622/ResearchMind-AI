from __future__ import annotations

from app.ai.guardrails.scoring.weights import STAGE_WEIGHTS


def compute_overall_risk(
    *,
    input_score: float | None,
    retrieval_score: float | None,
    generation_score: float | None,
    runtime_score: float | None = None,
) -> float | None:
    """
    Weighted average of whichever stage risk scores are actually
    available (PRD §13).

    Stages with no score (a stage with zero issues has no risk to
    report — see `GuardrailResult.score`) are dropped and the remaining
    weights renormalized, rather than treating a missing score as 0.
    Returns `None` when no stage produced a score at all. Mirrors
    `validation/scoring.py`'s `compute_overall_score`.
    """

    scores = {
        "input": input_score,
        "retrieval": retrieval_score,
        "generation": generation_score,
        "runtime": runtime_score,
    }

    available = {stage: score for stage, score in scores.items() if score is not None}

    if not available:
        return None

    total_weight = sum(STAGE_WEIGHTS[stage] for stage in available)

    if total_weight == 0:
        return None

    return sum(score * STAGE_WEIGHTS[stage] for stage, score in available.items()) / total_weight
