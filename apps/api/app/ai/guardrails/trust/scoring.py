from __future__ import annotations

from app.ai.guardrails.trust.models import SourceTrust

_PEER_REVIEWED_BONUS = 0.05


def compute_trust_score(
    source_trust: SourceTrust,
) -> float:
    """
    Deterministic trust score (PRD §9, Principle 3 -- no ML): the
    source type's base score plus a small peer-review bonus, capped at
    1.0. `publisher` is accepted on `SourceTrust` but not yet scored --
    a documented extension point for future publisher allowlists /
    journal ranking / citation counts (PRD §9 "Future").
    """

    score = source_trust.trust_score

    if source_trust.peer_reviewed:
        score += _PEER_REVIEWED_BONUS

    return min(score, 1.0)
