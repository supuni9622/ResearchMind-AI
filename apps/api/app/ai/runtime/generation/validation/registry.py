from __future__ import annotations

from app.ai.runtime.generation.validation.interfaces import (
    InputValidatorInterface,
    OutputValidatorInterface,
)
from app.ai.runtime.generation.validation.runtime.interfaces import (
    RuntimeContractInterface,
    RuntimeValidatorInterface,
)
from app.ai.runtime.generation.validation.runtime.registry import (
    RuntimeRegistry,
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

        self._runtime_registry = RuntimeRegistry()

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

    def register_runtime_validator(
        self,
        validator: RuntimeValidatorInterface,
    ) -> None:
        self._runtime_registry.register_validator(
            validator,
        )

    def register_runtime_contract(
        self,
        contract: RuntimeContractInterface,
    ) -> None:
        self._runtime_registry.register_contract(
            contract,
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

    @property
    def runtime_validators(
        self,
    ) -> list[RuntimeValidatorInterface]:
        return self._runtime_registry.all_validators

    @property
    def runtime_registry(
        self,
    ) -> RuntimeRegistry:
        """
        The underlying per-`RuntimeType` registry (PRD §8) — used by
        `ValidationService` to build its `RuntimeValidationService`.
        `runtime_validators` above is the flattened view PRD §10 asks
        for on `ValidationRegistry` itself.
        """

        return self._runtime_registry
