from __future__ import annotations

import pytest
from app.ai.guardrails.trust.models import SourceTrust, SourceType
from pydantic import ValidationError


def test_source_trust_construction() -> None:
    trust = SourceTrust(source_type=SourceType.ACADEMIC, trust_score=0.9, peer_reviewed=True)

    assert trust.source_type == SourceType.ACADEMIC
    assert trust.trust_score == 0.9
    assert trust.peer_reviewed is True
    assert trust.publisher is None


def test_source_trust_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SourceTrust(
            source_type=SourceType.WEB,
            trust_score=0.5,
            unexpected="x",  # type: ignore[call-arg]
        )
