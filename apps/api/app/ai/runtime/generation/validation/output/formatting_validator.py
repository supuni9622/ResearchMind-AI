from __future__ import annotations

import xml.etree.ElementTree as ElementTree

from app.ai.runtime.generation.enums import (
    ResponseFormat,
)
from app.ai.runtime.generation.models import (
    GenerationResult,
)
from app.ai.runtime.generation.validation.interfaces import (
    OutputValidatorInterface,
)
from app.ai.runtime.generation.validation.models import (
    ValidationIssue,
    ValidationSeverity,
    ValidatorOutcome,
)

_CODE_FENCE = "```"


class FormattingValidator(
    OutputValidatorInterface,
):
    """
    Checks `GenerationResult.content` is well-formed for the response
    format that was actually requested: balanced Markdown code fences
    for `ResponseFormat.MARKDOWN`, parseable XML for `ResponseFormat.
    XML`. JSON/STRUCTURED formatting is left to `JsonValidator` (it
    already owns that check, including repair-attempt scoring) —
    running a second, cruder JSON check here would just duplicate it.

    Runs only when a format with real structural rules was requested;
    plain `ResponseFormat.TEXT` has no format to violate.
    """

    @property
    def name(
        self,
    ) -> str:
        return "formatting"

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:

        response_format = result.request.response_format

        if response_format == ResponseFormat.MARKDOWN:
            return self._validate_markdown(
                result.content,
            )

        if response_format == ResponseFormat.XML:
            return self._validate_xml(
                result.content,
            )

        return ValidatorOutcome()

    def _validate_markdown(
        self,
        content: str,
    ) -> ValidatorOutcome:

        fence_count = content.count(
            _CODE_FENCE,
        )

        if fence_count % 2 != 0:
            return ValidatorOutcome(
                issues=[
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.ERROR,
                        message=(
                            "Markdown response has an unbalanced number of ``` "
                            f"code fences ({fence_count})."
                        ),
                        details={
                            "fence_count": fence_count,
                        },
                    )
                ],
                score=0.0,
            )

        return ValidatorOutcome(
            score=1.0,
        )

    def _validate_xml(
        self,
        content: str,
    ) -> ValidatorOutcome:

        text = content.strip()

        try:
            ElementTree.fromstring(
                text,
            )

            return ValidatorOutcome(
                score=1.0,
            )
        except ElementTree.ParseError:
            pass

        #
        # A response may legitimately contain multiple sibling XML
        # elements with no single root -- wrap it before giving up, the
        # same tolerance StructuredOutputRepair applies to JSON braces.
        #

        try:
            ElementTree.fromstring(
                f"<root>{text}</root>",
            )

            return ValidatorOutcome(
                score=1.0,
            )
        except ElementTree.ParseError as exc:
            return ValidatorOutcome(
                issues=[
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.ERROR,
                        message=f"Response content is not well-formed XML: {exc}",
                    )
                ],
                score=0.0,
            )
