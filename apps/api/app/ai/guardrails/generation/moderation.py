from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.guardrails.interfaces import GenerationGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.runtime.generation.models import GenerationResult


class ModerationProvider(
    ABC,
):
    """
    Foundation only -- PRD §21 explicitly skips advanced moderation for
    MVP ("Not required for MVP"). Seam for a future classifier-backed
    provider.
    """

    @abstractmethod
    async def moderate(
        self,
        content: str,
    ) -> list[GuardrailIssue]:
        pass


class AlwaysAllowModerationProvider(
    ModerationProvider,
):
    async def moderate(
        self,
        content: str,
    ) -> list[GuardrailIssue]:

        return []


class ModerationGuardrail(
    GenerationGuardrailInterface,
):
    def __init__(
        self,
        provider: ModerationProvider,
    ) -> None:
        self._provider = provider

    @property
    def name(
        self,
    ) -> str:
        return "moderation"

    async def check(
        self,
        result: GenerationResult,
    ) -> list[GuardrailIssue]:

        return await self._provider.moderate(
            result.content,
        )
