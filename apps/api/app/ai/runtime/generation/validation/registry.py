from __future__ import annotations

from app.ai.runtime.generation.validation.interfaces import (
    InputValidatorInterface,
    OutputValidatorInterface,
)


class ValidationRegistry:
    """
    Dynamic validator registration (PRD §13).

    Groups validators by stage so `ValidationService` can run each
    stage independently. A plain list under the hood — registration
    order is preserve order, which is also the order validators run in
    and the order their issues appear in `ValidationResult.issues`.
    """

    def __init__(
        self,
    ) -> None:
        self._input_validators: list[InputValidatorInterface] = []

        self._output_validators: list[OutputValidatorInterface] = []

        self._hallucination_validators: list[OutputValidatorInterface] = []

    # ==========================================================
    # Registration
    # ==========================================================

    def register_input_validator(
        self,
        validator: InputValidatorInterface,
    ) -> None:
        self._input_validators.append(
            validator,
        )

    def register_output_validator(
        self,
        validator: OutputValidatorInterface,
    ) -> None:
        self._output_validators.append(
            validator,
        )

    def register_hallucination_validator(
        self,
        validator: OutputValidatorInterface,
    ) -> None:
        self._hallucination_validators.append(
            validator,
        )

    # ==========================================================
    # Lookup
    # ==========================================================

    @property
    def input_validators(
        self,
    ) -> list[InputValidatorInterface]:
        return list(
            self._input_validators,
        )

    @property
    def output_validators(
        self,
    ) -> list[OutputValidatorInterface]:
        return list(
            self._output_validators,
        )

    @property
    def hallucination_validators(
        self,
    ) -> list[OutputValidatorInterface]:
        return list(
            self._hallucination_validators,
        )
