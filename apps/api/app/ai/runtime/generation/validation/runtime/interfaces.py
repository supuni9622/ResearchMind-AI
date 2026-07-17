from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.runtime.generation.models import (
    GenerationResult,
)
from app.ai.runtime.generation.validation.models import (
    ValidatorOutcome,
)
from app.ai.runtime.generation.validation.runtime.enums import (
    RuntimeType,
)


class RuntimeValidatorInterface(
    ABC,
):
    """
    A single, reusable runtime-stage check (PRD §9) — e.g. completeness,
    consistency, confidence range. Tied to one `RuntimeType` so
    `RuntimeValidationService` only runs it for matching requests.
    Should not raise for validation failures — only for programming
    errors — and should return an empty outcome when it has nothing to
    check.
    """

    @property
    @abstractmethod
    def name(
        self,
    ) -> str:
        pass

    @property
    @abstractmethod
    def runtime(
        self,
    ) -> RuntimeType:
        pass

    @abstractmethod
    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:
        pass


class RuntimeContractInterface(
    ABC,
):
    """
    Defines what constitutes a valid output for one `RuntimeType`
    (PRD §8) — e.g. the Research Runtime Contract requires sections,
    citations, evidence, and confidence. Aggregates its own checks
    (and may delegate to `RuntimeValidatorInterface`s) into a single
    `ValidatorOutcome` covering every requirement for that runtime.
    """

    @property
    @abstractmethod
    def runtime(
        self,
    ) -> RuntimeType:
        pass

    @abstractmethod
    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:
        pass
