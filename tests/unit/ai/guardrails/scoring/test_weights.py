from __future__ import annotations

from app.ai.guardrails.scoring.weights import STAGE_WEIGHTS


def test_weights_match_prd_formula() -> None:
    assert STAGE_WEIGHTS == {
        "input": 0.30,
        "retrieval": 0.30,
        "generation": 0.20,
        "runtime": 0.20,
    }


def test_weights_sum_to_one() -> None:
    assert sum(STAGE_WEIGHTS.values()) == 1.0
