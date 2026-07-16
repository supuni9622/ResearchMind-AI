from __future__ import annotations

from app.ai.guardrails.policies.risk_policy import RiskPolicy, exceeds_risk_threshold


def test_higher_policy_treats_lower_scores_as_exceeding() -> None:
    assert exceeds_risk_threshold(score=0.55, policy=RiskPolicy.HIGH) is True
    assert exceeds_risk_threshold(score=0.55, policy=RiskPolicy.LOW) is False


def test_score_at_exact_threshold_exceeds() -> None:
    assert exceeds_risk_threshold(score=0.7, policy=RiskPolicy.MEDIUM) is True


def test_score_below_threshold_does_not_exceed() -> None:
    assert exceeds_risk_threshold(score=0.1, policy=RiskPolicy.CRITICAL) is False
