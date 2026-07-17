from __future__ import annotations

from collections import defaultdict
from typing import cast

from app.ai.runtime.generation.validation.runtime.enums import (
    RuntimeType,
)
from app.ai.runtime.generation.validation.runtime.interfaces import (
    RuntimeContractInterface,
    RuntimeValidatorInterface,
)


class RuntimeRegistry:
    """
    Dynamic per-`RuntimeType` registration (PRD §8) for runtime-stage
    contracts and validators.

    Unlike `ValidationRegistry`'s flat per-stage lists, lookups here
    are keyed by `RuntimeType` — `RuntimeValidationService` only wants
    the contract/validators that apply to the runtime a given
    `GenerationRequest` declared.
    """

    def __init__(
        self,
    ) -> None:
        self._contracts: dict[RuntimeType, RuntimeContractInterface] = {}

        self._validators: dict[RuntimeType, list[RuntimeValidatorInterface]] = defaultdict(list)

    # ==========================================================
    # Registration
    # ==========================================================

    def register_contract(
        self,
        contract: RuntimeContractInterface,
    ) -> None:
        self._contracts[contract.runtime] = contract

    def register_validator(
        self,
        validator: RuntimeValidatorInterface,
    ) -> None:
        self._validators[validator.runtime].append(
            validator,
        )

    # ==========================================================
    # Lookup
    # ==========================================================

    def contract_for(
        self,
        runtime: RuntimeType,
    ) -> RuntimeContractInterface | None:
        return self._contracts.get(
            runtime,
        )

    def validators_for(
        self,
        runtime: RuntimeType,
    ) -> list[RuntimeValidatorInterface]:
        return list(
            self._validators.get(
                runtime,
                [],
            )
        )

    @property
    def all_validators(
        self,
    ) -> list[RuntimeValidatorInterface]:
        """
        Every registered contract and standalone validator, flattened
        across all runtimes — backs `ValidationRegistry.runtime_validators`
        (PRD §10). Every concrete contract also satisfies
        `RuntimeValidatorInterface` (see `BaseRuntimeContract`), hence
        the cast, so they're included alongside standalone validators.
        """

        return [
            *cast(
                "list[RuntimeValidatorInterface]",
                list(self._contracts.values()),
            ),
            *(validator for validators in self._validators.values() for validator in validators),
        ]
