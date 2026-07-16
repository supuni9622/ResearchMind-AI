from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class OutputFormat(StrEnum):
    JSON = "json"

    PYDANTIC = "pydantic"

    MARKDOWN = "markdown"

    XML = "xml"


class StructuredOutputRequest(
    BaseModel,
):
    content: str

    output_format: OutputFormat

    output_schema: type[BaseModel] | None = None

    repair_json: bool = True


class StructuredOutputResult(
    BaseModel,
):
    raw_content: str

    parsed_content: Any

    success: bool

    errors: list[str] = []
