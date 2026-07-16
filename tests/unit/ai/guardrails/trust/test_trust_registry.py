from __future__ import annotations

from app.ai.guardrails.trust.models import SourceType
from app.ai.guardrails.trust.trust_registry import TrustRegistry


def test_default_scores_rank_academic_above_forum() -> None:
    registry = TrustRegistry()

    assert registry.score_for(SourceType.ACADEMIC) > registry.score_for(SourceType.FORUM)


def test_all_source_types_have_a_default_score() -> None:
    registry = TrustRegistry()

    for source_type in SourceType:
        score = registry.score_for(source_type)
        assert 0.0 <= score <= 1.0


def test_register_override_replaces_the_default() -> None:
    registry = TrustRegistry()

    registry.register_override(SourceType.FORUM, 0.99)

    assert registry.score_for(SourceType.FORUM) == 0.99
