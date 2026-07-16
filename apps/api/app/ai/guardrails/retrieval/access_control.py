from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.guardrails.interfaces import RetrievalGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.knowledge.context.models import ContextChunk


class AccessControlProvider(
    ABC,
):
    """
    Foundation only (PRD §9/§17) -- "implement interfaces now, complex
    logic later". Future providers will check tenant isolation, document
    ACLs, and workspace permissions; this seam exists so
    `AccessControlGuardrail` doesn't need to change when they land.
    """

    @abstractmethod
    async def check_access(
        self,
        *,
        owner_id: str,
        chunks: list[ContextChunk],
    ) -> list[GuardrailIssue]:
        pass


class PermissiveAccessControlProvider(
    AccessControlProvider,
):
    """Default provider -- allows everything. No tenant isolation /
    document ACL / workspace permission model exists in this codebase yet."""

    async def check_access(
        self,
        *,
        owner_id: str,
        chunks: list[ContextChunk],
    ) -> list[GuardrailIssue]:

        return []


class AccessControlGuardrail(
    RetrievalGuardrailInterface,
):
    def __init__(
        self,
        provider: AccessControlProvider,
        *,
        owner_id: str = "",
    ) -> None:
        self._provider = provider

        self._owner_id = owner_id

    @property
    def name(
        self,
    ) -> str:
        return "access_control"

    async def check(
        self,
        chunks: list[ContextChunk],
    ) -> list[GuardrailIssue]:

        return await self._provider.check_access(
            owner_id=self._owner_id,
            chunks=chunks,
        )
