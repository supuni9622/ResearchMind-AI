from __future__ import annotations

from app.ai.guardrails.trust.models import SourceType

_DEFAULT_TRUST_SCORES: dict[SourceType, float] = {
    SourceType.ACADEMIC: 0.95,
    SourceType.JOURNAL: 0.85,
    SourceType.USER_DOCUMENT: 0.70,
    SourceType.NEWS: 0.60,
    SourceType.WEB: 0.40,
    SourceType.BLOG: 0.30,
    SourceType.FORUM: 0.25,
}
"""
Deliberately opinionated defaults (PRD §9) -- academic/peer-reviewed
sources are trusted most, unattributed forum/blog content least.
`USER_DOCUMENT` sits above general news since ResearchMind today only
ingests documents the user themself uploaded (see
`retrieval/source_trust.py`'s default-source-type note). Overridable
per-instance via `register_override` for future enterprise trust
policies (PRD §9 "Future: enterprise trust").
"""


class TrustRegistry:
    """Static trust-score-by-source-type lookup (PRD §9)."""

    def __init__(
        self,
    ) -> None:
        self._scores: dict[SourceType, float] = dict(
            _DEFAULT_TRUST_SCORES,
        )

    def score_for(
        self,
        source_type: SourceType,
    ) -> float:
        return self._scores[source_type]

    def register_override(
        self,
        source_type: SourceType,
        score: float,
    ) -> None:
        self._scores[source_type] = score
