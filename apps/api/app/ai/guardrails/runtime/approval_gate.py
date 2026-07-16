from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID, uuid4

from app.ai.guardrails.enums import GuardrailCategory
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class ApprovalRequest(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    request_id: UUID = Field(
        default_factory=uuid4,
    )

    reason: str

    category: GuardrailCategory

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class ApprovalResponse(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    request_id: UUID

    approved: bool

    responder: str | None = None

    notes: str | None = None


class ApprovalGateInterface(
    ABC,
):
    """
    Interfaces only (PRD §19) -- the future LangGraph-interrupt seam for
    human-in-the-loop approval on high-cost/destructive/external-tool
    actions. Deliberately has **no** concrete implementation and is
    **not** registered in `create.py`'s registry: no `GuardrailAction.
    ESCALATE` is triggerable end-to-end in this MVP, since there's
    nothing yet to actually pause execution and wait for a response
    (that requires LangGraph checkpoints/interrupts, which are a future
    milestone per PRD §19).
    """

    @abstractmethod
    async def request_approval(
        self,
        request: ApprovalRequest,
    ) -> ApprovalResponse:
        pass
