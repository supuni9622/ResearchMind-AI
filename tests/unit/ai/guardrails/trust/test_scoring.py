from __future__ import annotations

from app.ai.guardrails.trust.models import SourceTrust, SourceType
from app.ai.guardrails.trust.scoring import compute_trust_score


def test_base_score_with_no_peer_review_bonus() -> None:
    trust = SourceTrust(source_type=SourceType.WEB, trust_score=0.4, peer_reviewed=False)

    assert compute_trust_score(trust) == 0.4


def test_peer_reviewed_adds_a_bonus() -> None:
    trust = SourceTrust(source_type=SourceType.JOURNAL, trust_score=0.85, peer_reviewed=True)

    assert compute_trust_score(trust) == 0.90


def test_score_is_capped_at_one() -> None:
    trust = SourceTrust(source_type=SourceType.ACADEMIC, trust_score=0.99, peer_reviewed=True)

    assert compute_trust_score(trust) == 1.0
