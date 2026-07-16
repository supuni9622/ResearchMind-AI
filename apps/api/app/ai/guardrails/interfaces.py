from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.guardrails.models import GuardrailIssue
from app.ai.guardrails.runtime.execution_limits import (
    BudgetPolicy,
    ExecutionState,
)
from app.ai.knowledge.context.models import ContextChunk
from app.ai.runtime.generation.models import (
    GenerationRequest,
    GenerationResult,
)


class InputGuardrailInterface(
    ABC,
):
    """
    A single input-stage guardrail check, run before retrieval/generation.

    Should not raise for a policy trigger — only for programming errors
    — and should return an empty list when nothing is triggered. Unlike
    Validation Platform's `ValidatorOutcome`, there is no separate score
    channel: every MVP guardrail check here is a discrete rule/threshold
    trigger, so `GuardrailService` derives each stage's risk score from
    the issues themselves (see `constants.SEVERITY_RISK_SCORES`).
    """

    @property
    @abstractmethod
    def name(
        self,
    ) -> str:
        pass

    @abstractmethod
    async def check(
        self,
        request: GenerationRequest,
    ) -> list[GuardrailIssue]:
        pass


class RetrievalGuardrailInterface(
    ABC,
):
    """A single retrieval-stage guardrail check, run over retrieved chunks."""

    @property
    @abstractmethod
    def name(
        self,
    ) -> str:
        pass

    @abstractmethod
    async def check(
        self,
        chunks: list[ContextChunk],
    ) -> list[GuardrailIssue]:
        pass


class GenerationGuardrailInterface(
    ABC,
):
    """A single generation-stage guardrail check, run over a completed result."""

    @property
    @abstractmethod
    def name(
        self,
    ) -> str:
        pass

    @abstractmethod
    async def check(
        self,
        result: GenerationResult,
    ) -> list[GuardrailIssue]:
        pass


class RuntimeGuardrailInterface(
    ABC,
):
    """A single runtime-stage guardrail check, run over execution state."""

    @property
    @abstractmethod
    def name(
        self,
    ) -> str:
        pass

    @abstractmethod
    async def check(
        self,
        state: ExecutionState,
        policy: BudgetPolicy,
    ) -> list[GuardrailIssue]:
        pass
