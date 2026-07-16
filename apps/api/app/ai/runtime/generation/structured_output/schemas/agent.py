from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AgentActionType(StrEnum):
    THINK = "think"

    PLAN = "plan"

    TOOL_CALL = "tool_call"

    RETRIEVE = "retrieve"

    GENERATE = "generate"

    REVIEW = "review"

    FINAL = "final"


class ToolCall(
    BaseModel,
):
    tool_name: str

    arguments: dict[
        str,
        Any,
    ] = Field(
        default_factory=dict,
    )


class AgentStep(
    BaseModel,
):
    step_number: int

    title: str

    reasoning: str | None = None

    action: AgentActionType

    tool_call: ToolCall | None = None

    expected_output: str | None = None


class AgentPlan(
    BaseModel,
):
    objective: str

    assumptions: list[str] = Field(
        default_factory=list,
    )

    steps: list[AgentStep] = Field(
        default_factory=list,
    )


class AgentReview(
    BaseModel,
):
    confidence: float = Field(
        ge=0,
        le=1,
    )

    issues: list[str] = Field(
        default_factory=list,
    )

    missing_information: list[str] = Field(
        default_factory=list,
    )

    requires_replanning: bool = False


class AgentResponse(
    BaseModel,
):
    objective: str

    reasoning_summary: str

    final_answer: str

    confidence: float = Field(
        ge=0,
        le=1,
    )

    citations: list[str] = Field(
        default_factory=list,
    )

    metadata: dict[
        str,
        Any,
    ] = Field(
        default_factory=dict,
    )


class AgentExecutionResult(
    BaseModel,
):
    plan: AgentPlan | None = None

    review: AgentReview | None = None

    response: AgentResponse
