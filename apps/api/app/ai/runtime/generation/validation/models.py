from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class ValidationSeverity(StrEnum):
    ERROR = "error"

    WARNING = "warning"


class ValidationIssue(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    validator: str

    severity: ValidationSeverity

    message: str

    details: dict[str, Any] = Field(
        default_factory=dict,
    )


class ValidationResult(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    valid: bool

    issues: list[ValidationIssue] = Field(
        default_factory=list,
    )
