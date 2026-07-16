from __future__ import annotations

from app.ai.runtime.generation.enums import (
    ResponseFormat,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
)
from app.ai.runtime.generation.validation.interfaces import (
    InputValidatorInterface,
)
from app.ai.runtime.generation.validation.models import (
    InputValidationContext,
    ValidationIssue,
    ValidationSeverity,
    ValidatorOutcome,
)

_STRUCTURED_FORMATS = (
    ResponseFormat.JSON,
    ResponseFormat.STRUCTURED,
)


class ProviderLimitsValidator(
    InputValidatorInterface,
):
    """
    Checks the request against what the resolved provider's
    `ProviderCapabilities` actually supports: streaming, structured
    output, and tool calling.

    This mirrors `GenerationService._check_capability_support()`
    (which only logs) rather than replacing it — that method predates
    the Validation Platform and other callers still depend on its
    log-only, always-degrade-gracefully behavior. This validator makes
    the same signal available as a `ValidationIssue` so it can be
    surfaced in a `ValidationReport` and reused by runtimes that don't
    go through `GenerationService` at all.

    Every finding here is a WARNING: a missing capability degrades
    gracefully (e.g. a provider without native structured output still
    returns text, which the repair/parsing pipeline attempts to
    salvage) rather than failing the request outright.
    """

    @property
    def name(
        self,
    ) -> str:
        return "provider_limits"

    async def validate(
        self,
        request: GenerationRequest,
        context: InputValidationContext,
    ) -> ValidatorOutcome:

        issues: list[ValidationIssue] = []

        wants_structured = (
            request.output_schema is not None or request.response_format in _STRUCTURED_FORMATS
        )

        if wants_structured and context.supports_structured_output is False:
            issues.append(
                self._capability_issue(
                    capability="structured_output",
                    detail=(
                        "A response_schema/output_model was requested but the "
                        "resolved provider does not support native structured output."
                    ),
                )
            )

        if request.response_format == ResponseFormat.JSON and context.supports_json_mode is False:
            issues.append(
                self._capability_issue(
                    capability="json_mode",
                    detail=(
                        "response_format is JSON but the resolved provider does "
                        "not support native structured/JSON output."
                    ),
                )
            )

        if request.tools and context.supports_tool_calling is False:
            issues.append(
                self._capability_issue(
                    capability="tool_calling",
                    detail=(
                        f"{len(request.tools)} tool(s) were requested but the "
                        "resolved provider does not support tool calling."
                    ),
                )
            )

        if request.stream and context.supports_streaming is False:
            issues.append(
                self._capability_issue(
                    capability="streaming",
                    detail=(
                        "stream=True was requested but the resolved provider "
                        "does not support streaming."
                    ),
                )
            )

        return ValidatorOutcome(
            issues=issues,
        )

    def _capability_issue(
        self,
        *,
        capability: str,
        detail: str,
    ) -> ValidationIssue:

        return ValidationIssue(
            validator=self.name,
            severity=ValidationSeverity.WARNING,
            message=detail,
            details={
                "missing_capability": capability,
            },
        )
