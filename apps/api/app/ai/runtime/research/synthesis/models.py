from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ResearchDraftSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=6_000)
    citation_ids: list[str] = Field(default_factory=list, max_length=20)


class ResearchDraft(BaseModel):
    """Standard research-report draft; every evidence-backed claim cites bundle IDs."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    title: str = Field(min_length=1, max_length=300)
    abstract: str = Field(min_length=1, max_length=2_000)
    methodology: str = Field(min_length=1, max_length=2_000)
    findings: list[ResearchDraftSection] = Field(min_length=1, max_length=8)
    discussion: str = Field(min_length=1, max_length=4_000)
    conclusion: str = Field(min_length=1, max_length=2_000)
    citation_ids: list[str] = Field(default_factory=list, max_length=40)
    limitations: list[str] = Field(default_factory=list, max_length=12)
