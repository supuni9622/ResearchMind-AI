from __future__ import annotations

from enum import StrEnum


class RiskPolicy(StrEnum):
    """
    How aggressively the platform should react to a given risk score
    (PRD §12) — used both by `GuardrailService` (stage-level risk) and
    `trust/trust_policies.py` (source-trust risk). Higher policies treat
    lower scores as worth acting on.
    """

    LOW = "low"

    MEDIUM = "medium"

    HIGH = "high"

    CRITICAL = "critical"


RISK_BLOCK_THRESHOLDS: dict[RiskPolicy, float] = {
    RiskPolicy.LOW: 0.9,
    RiskPolicy.MEDIUM: 0.7,
    RiskPolicy.HIGH: 0.5,
    RiskPolicy.CRITICAL: 0.3,
}
"""A risk/severity score at or above this policy's threshold is treated
as block-worthy. E.g. under `RiskPolicy.HIGH`, a score of 0.5+ blocks;
under the more permissive `RiskPolicy.LOW`, only 0.9+ does."""


def exceeds_risk_threshold(
    *,
    score: float,
    policy: RiskPolicy,
) -> bool:

    return score >= RISK_BLOCK_THRESHOLDS[policy]
