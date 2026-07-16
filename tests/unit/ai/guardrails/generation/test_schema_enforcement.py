"""
Uses the real SchemaValidator/JsonValidator (Validation Platform) rather
than fakes -- cheap, deterministic, and this is exactly the composition
this guardrail is responsible for getting right.
"""

from __future__ import annotations

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.generation.schema_enforcement import SchemaEnforcementGuardrail
from app.ai.runtime.generation.enums import ResponseFormat
from app.ai.runtime.generation.validation.output.json_validator import JsonValidator
from app.ai.runtime.generation.validation.output.schema_validator import SchemaValidator

from tests.unit.ai.guardrails.factories import make_request, make_result

_SCHEMA = {
    "type": "object",
    "properties": {"x": {"type": "string"}},
    "required": ["x"],
}


async def test_valid_output_produces_no_issues() -> None:
    guardrail = SchemaEnforcementGuardrail(SchemaValidator(), JsonValidator())

    request = make_request(output_schema=_SCHEMA, response_format=ResponseFormat.JSON)
    result = make_result(request=request, content='{"x": "hello"}', parsed_output={"x": "hello"})

    assert await guardrail.check(result) == []


async def test_schema_mismatch_errors() -> None:
    guardrail = SchemaEnforcementGuardrail(SchemaValidator(), JsonValidator())

    request = make_request(output_schema=_SCHEMA, response_format=ResponseFormat.JSON)
    result = make_result(request=request, content='{"y": 1}', parsed_output={"y": 1})

    issues = await guardrail.check(result)

    assert len(issues) == 1
    assert issues[0].severity == GuardrailSeverity.ERROR
    assert issues[0].category == GuardrailCategory.SCHEMA


async def test_invalid_json_content_errors() -> None:
    guardrail = SchemaEnforcementGuardrail(SchemaValidator(), JsonValidator())

    request = make_request(response_format=ResponseFormat.JSON)
    result = make_result(request=request, content="not valid json {{{")

    issues = await guardrail.check(result)

    assert len(issues) == 1
    assert issues[0].category == GuardrailCategory.SCHEMA


async def test_json_validator_is_optional() -> None:
    guardrail = SchemaEnforcementGuardrail(SchemaValidator())

    request = make_request(response_format=ResponseFormat.JSON)
    result = make_result(request=request, content="not valid json {{{")

    # JsonValidator not wired in -- only SchemaValidator runs, and it has
    # no output_schema to check against, so nothing is flagged.
    assert await guardrail.check(result) == []
