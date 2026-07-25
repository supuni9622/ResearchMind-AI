"""Research-Runtime-specific web search decision/enum contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class WebSearchMode(StrEnum):
    """Per-request web search control (PRD §6.1)."""

    DISABLED = "disabled"
    AUTO = "auto"
    REQUIRED = "required"


class WebSearchNecessityDecision(BaseModel):
    """Structured output of the cheap necessity-decision LLM call. Deliberately
    tiny: a fast/cheap model only needs to answer yes/no plus a short,
    human-readable justification and search query -- never full reasoning."""

    model_config = ConfigDict(extra="forbid")

    needs_web_search: bool
    query: str = Field(min_length=1, max_length=400)
    reason: str = Field(min_length=1, max_length=500)
