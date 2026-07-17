from __future__ import annotations

from abc import abstractmethod

from app.ai.runtime.generation.models import (
    GenerationResult,
)
from app.ai.runtime.generation.validation.interfaces import (
    OutputValidatorInterface,
)
from app.ai.runtime.generation.validation.models import (
    ValidationIssue,
    ValidatorOutcome,
)
from app.ai.runtime.generation.validation.runtime.interfaces import (
    RuntimeContractInterface,
    RuntimeValidatorInterface,
)


class BaseRuntimeContract(
    RuntimeContractInterface,
    RuntimeValidatorInterface,
):
    """
    Shared plumbing for runtime contracts (PRD §15-§19): runs the
    generic runtime validators (PRD §14) a subclass composes via
    `checks`, and merges their outcomes into a single `ValidatorOutcome`
    tagged with `contract_name` — matching the PRD §21 report example,
    where every issue from the research contract carries
    `"validator": "research_contract"` regardless of which underlying
    check produced it (the originating check name is preserved in
    `ValidationIssue.details["check"]`).

    Implements both `RuntimeContractInterface` and
    `RuntimeValidatorInterface` — the same method signatures satisfy
    both, so a contract instance can be registered via
    `ValidationRegistry.register_runtime_contract()` (RuntimeType-keyed
    lookup) while still exposing `.name` for `RuntimeRegistry.all_validators`
    / crash logging.
    """

    @property
    @abstractmethod
    def contract_name(
        self,
    ) -> str:
        pass

    @property
    def name(
        self,
    ) -> str:
        return self.contract_name

    @property
    @abstractmethod
    def checks(
        self,
    ) -> list[OutputValidatorInterface]:
        """The generic runtime validators (PRD §14) this contract composes."""

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:

        issues: list[ValidationIssue] = []

        scores: list[float] = []

        for check in self.checks:
            outcome = await check.validate(
                result,
            )

            issues.extend(
                issue.model_copy(
                    update={
                        "validator": self.contract_name,
                        "details": {
                            **issue.details,
                            "check": check.name,
                        },
                    },
                )
                for issue in outcome.issues
            )

            if outcome.score is not None:
                scores.append(
                    outcome.score,
                )

        score = sum(scores) / len(scores) if scores else None

        return ValidatorOutcome(
            issues=issues,
            score=score,
        )
