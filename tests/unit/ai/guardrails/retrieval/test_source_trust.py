from __future__ import annotations

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.retrieval.source_trust import SourceTrustGuardrail
from app.ai.guardrails.trust.models import SourceType
from app.ai.guardrails.trust.trust_registry import TrustRegistry

from tests.unit.ai.guardrails.factories import make_chunk


async def test_default_source_type_is_user_document_and_trusted() -> None:
    guardrail = SourceTrustGuardrail(TrustRegistry())

    issues = await guardrail.check([make_chunk()])

    assert issues == []


async def test_low_trust_source_type_warns() -> None:
    guardrail = SourceTrustGuardrail(TrustRegistry())

    chunk = make_chunk(metadata={"source_type": "forum"})

    issues = await guardrail.check([chunk])

    assert len(issues) == 1
    assert issues[0].severity == GuardrailSeverity.WARNING
    assert issues[0].category == GuardrailCategory.SOURCE_TRUST
    assert issues[0].metadata["source_type"] == "forum"


async def test_unknown_source_type_string_falls_back_to_user_document() -> None:
    guardrail = SourceTrustGuardrail(TrustRegistry())

    chunk = make_chunk(metadata={"source_type": "not-a-real-type"})

    issues = await guardrail.check([chunk])

    assert issues == []


async def test_registry_override_is_respected() -> None:
    registry = TrustRegistry()
    registry.register_override(SourceType.ACADEMIC, 0.1)

    guardrail = SourceTrustGuardrail(registry)

    chunk = make_chunk(metadata={"source_type": "academic"})

    issues = await guardrail.check([chunk])

    assert len(issues) == 1
