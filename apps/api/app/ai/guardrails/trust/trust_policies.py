from __future__ import annotations

from app.ai.guardrails.enums import GuardrailAction
from app.ai.guardrails.policies.risk_policy import RiskPolicy, exceeds_risk_threshold


def action_for_trust_score(
    *,
    trust_score: float,
    risk_policy: RiskPolicy,
) -> GuardrailAction:
    """
    Maps a source's trust score to a `GuardrailAction` under the
    configured `RiskPolicy` (PRD §12). Trust and risk are inverses --
    `1 - trust_score` is what's compared against `RiskPolicy`'s
    block thresholds (`policies/risk_policy.py`), so a `RiskPolicy.HIGH`
    treats even moderately low-trust sources (e.g. an uncited web page)
    as worth blocking on, while `RiskPolicy.LOW` only reacts to
    near-zero-trust sources.
    """

    risk = 1.0 - trust_score

    if exceeds_risk_threshold(score=risk, policy=risk_policy):
        return GuardrailAction.BLOCK

    if risk > 0.0:
        return GuardrailAction.WARN

    return GuardrailAction.ALLOW
