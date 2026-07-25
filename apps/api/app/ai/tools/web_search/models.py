"""Canonical, provider-independent Web Search models (web_search_tool_platform_prd.md §9).

Providers translate their SDK/HTTP responses into these types and never leak
SDK response objects past their own adapter module.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.ai.tools.web_search.enums import WebSearchDepth


class WebSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=3, max_length=500)
    max_results: int = Field(default=8, ge=1, le=20)
    search_depth: WebSearchDepth = WebSearchDepth.BASIC
    include_domains: list[str] = Field(default_factory=list, max_length=20)
    exclude_domains: list[str] = Field(default_factory=list, max_length=20)
    published_after: date | None = None
    published_before: date | None = None
    include_raw_content: bool = False


class WebSearchResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_id: UUID = Field(default_factory=uuid4)
    title: str
    url: str
    snippet: str
    provider: str
    domain: str
    provider_score: float | None = None
    published_at: datetime | None = None
    author: str | None = None
    raw_content: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class WebSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    items: list[WebSearchResultItem]
    provider: str
    duration_ms: float
    estimated_cost_usd: float | None = None
    request_id: str | None = None
