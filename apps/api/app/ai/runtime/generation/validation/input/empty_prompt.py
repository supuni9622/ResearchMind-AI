from __future__ import annotations

import re

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

#
# Matches `PromptBuilder.extract_variables()` (generation/prompts/builder.py)
# — `{variable}` placeholders left unrendered in a template. By the time a
# `GenerationRequest` reaches here, `PromptService.render_messages()` should
# already have substituted every one; a surviving placeholder means a
# variable was missing at render time.
#

_UNRENDERED_PLACEHOLDER_RE = re.compile(
    r"\{[^{}]+\}",
)


class EmptyPromptValidator(
    InputValidatorInterface,
):
    """
    Checks for an empty/whitespace-only user or system prompt, and for
    template placeholders left unrendered (a missing prompt variable).

    `GenerationService._validate()` already hard-rejects an empty
    `user_prompt` before any validator runs, so that specific case is
    unreachable through that caller — this validator exists so other,
    future callers of the Validation Platform (runtimes without that
    same hard gate) get the same check as a soft `ValidationIssue`.
    """

    @property
    def name(
        self,
    ) -> str:
        return "empty_prompt"

    async def validate(
        self,
        request: GenerationRequest,
        context: InputValidationContext,
    ) -> ValidatorOutcome:

        issues: list[ValidationIssue] = []

        if not request.user_prompt.strip():
            issues.append(
                ValidationIssue(
                    validator=self.name,
                    severity=ValidationSeverity.ERROR,
                    message="user_prompt is empty or whitespace-only.",
                )
            )
        else:
            issues.extend(
                self._unrendered_placeholder_issues(
                    field="user_prompt",
                    text=request.user_prompt,
                )
            )

        if request.system_prompt is not None:
            if not request.system_prompt.strip():
                issues.append(
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.WARNING,
                        message=(
                            "system_prompt was explicitly set but is empty or "
                            "whitespace-only; omit it entirely if there's no "
                            "system prompt."
                        ),
                    )
                )
            else:
                issues.extend(
                    self._unrendered_placeholder_issues(
                        field="system_prompt",
                        text=request.system_prompt,
                    )
                )

        return ValidatorOutcome(
            issues=issues,
        )

    def _unrendered_placeholder_issues(
        self,
        *,
        field: str,
        text: str,
    ) -> list[ValidationIssue]:

        placeholders = sorted(
            set(
                _UNRENDERED_PLACEHOLDER_RE.findall(
                    text,
                )
            )
        )

        if not placeholders:
            return []

        return [
            ValidationIssue(
                validator=self.name,
                severity=ValidationSeverity.WARNING,
                message=(
                    f"{field} contains what look like unrendered template "
                    f"placeholders: {', '.join(placeholders)}."
                ),
                details={
                    "field": field,
                    "placeholders": placeholders,
                },
            )
        ]
