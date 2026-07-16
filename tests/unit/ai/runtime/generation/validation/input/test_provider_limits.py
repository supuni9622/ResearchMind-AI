"""
Unit tests for ProviderLimitsValidator.

Covers:
- Every capability supported -> no issues
- structured_output requested (via output_schema) but unsupported -> WARNING
- response_format=JSON but supports_json_mode is False -> WARNING, distinct
  from the structured_output capability (regression guard: these are two
  different `ProviderCapabilities` flags and must not be conflated)
- tools requested but tool_calling unsupported -> WARNING
- stream=True but streaming unsupported -> WARNING
- Capability fields left as None (unknown) -> not flagged (only an
  explicit False triggers an issue)
"""

from __future__ import annotations

from app.ai.runtime.generation.enums import ResponseFormat
from app.ai.runtime.generation.models import ToolDefinition
from app.ai.runtime.generation.validation.input.provider_limits import ProviderLimitsValidator
from app.ai.runtime.generation.validation.models import (
    InputValidationContext,
    ValidationSeverity,
)

from tests.unit.ai.runtime.generation.validation.factories import make_request

validator = ProviderLimitsValidator()

_FULLY_SUPPORTED = InputValidationContext(
    supports_streaming=True,
    supports_structured_output=True,
    supports_json_mode=True,
    supports_tool_calling=True,
)


async def test_validate_passes_when_everything_is_supported() -> None:
    request = make_request(
        output_schema={"type": "object"},
        response_format=ResponseFormat.JSON,
        tools=[ToolDefinition(name="search", description="search", parameters={})],
        stream=True,
    )

    outcome = await validator.validate(request, _FULLY_SUPPORTED)

    assert outcome.issues == []


async def test_validate_warns_when_structured_output_unsupported() -> None:
    request = make_request(output_schema={"type": "object"})

    context = InputValidationContext(supports_structured_output=False)

    outcome = await validator.validate(request, context)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.WARNING
    assert outcome.issues[0].details["missing_capability"] == "structured_output"


async def test_validate_distinguishes_json_mode_from_structured_output() -> None:
    """
    response_format=JSON with structured_output supported but json_mode
    NOT supported must still be flagged -- and specifically as
    "json_mode", not "structured_output".
    """

    request = make_request(response_format=ResponseFormat.JSON)

    context = InputValidationContext(
        supports_structured_output=True,
        supports_json_mode=False,
    )

    outcome = await validator.validate(request, context)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].details["missing_capability"] == "json_mode"


async def test_validate_warns_when_tool_calling_unsupported() -> None:
    request = make_request(
        tools=[ToolDefinition(name="search", description="search", parameters={})],
    )

    context = InputValidationContext(supports_tool_calling=False)

    outcome = await validator.validate(request, context)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].details["missing_capability"] == "tool_calling"


async def test_validate_warns_when_streaming_unsupported() -> None:
    request = make_request(stream=True)

    context = InputValidationContext(supports_streaming=False)

    outcome = await validator.validate(request, context)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].details["missing_capability"] == "streaming"


async def test_validate_does_not_flag_unknown_capabilities() -> None:
    request = make_request(
        output_schema={"type": "object"},
        tools=[ToolDefinition(name="search", description="search", parameters={})],
        stream=True,
    )

    outcome = await validator.validate(request, InputValidationContext())

    assert outcome.issues == []
