from __future__ import annotations

from app.ai.guardrails.enums import GuardrailAction
from app.ai.guardrails.policies.risk_policy import RiskPolicy
from app.ai.guardrails.trust.trust_policies import action_for_trust_score


def test_high_trust_score_allows() -> None:
    assert (
        action_for_trust_score(trust_score=1.0, risk_policy=RiskPolicy.MEDIUM)
        == GuardrailAction.ALLOW
    )


def test_moderate_trust_score_warns_under_low_risk_policy() -> None:
    assert (
        action_for_trust_score(trust_score=0.6, risk_policy=RiskPolicy.LOW) == GuardrailAction.WARN
    )


def test_low_trust_score_blocks_under_high_risk_policy() -> None:
    assert (
        action_for_trust_score(trust_score=0.2, risk_policy=RiskPolicy.HIGH)
        == GuardrailAction.BLOCK
    )
