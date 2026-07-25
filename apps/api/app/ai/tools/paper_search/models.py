"""Canonical, provider-independent paper-search models.

Providers translate their SDK/MCP responses into these types and never leak
raw MCP tool-result payloads past their own adapter module (mirrors
`app.ai.tools.web_search.models`).
"""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class PaperSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=3, max_length=500)
    max_results: int = Field(default=5, ge=1, le=20)


class PaperSearchResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_id: UUID = Field(default_factory=uuid4)
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    url: str | None = None
    doi: str | None = None
    abstract: str | None = None
    # The MCP server's own paper identifier -- kept for a future `get_paper`/
    # `get_related_papers` follow-up call; unused by search_papers callers today.
    external_id: str | None = None


class PaperSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    items: list[PaperSearchResultItem]
    provider: str
    duration_ms: float
