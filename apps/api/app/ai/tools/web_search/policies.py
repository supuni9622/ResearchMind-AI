"""Search execution policy (PRD §25) -- budgets, domain rules, approval defaults.

Settings-driven; `WebSearchService` enforces this before/around every
provider call so limits live in one place rather than scattered across
callers.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WebSearchPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    max_search_calls_per_run: int = 1
    max_results_per_call: int = 8
    max_page_characters: int = 4_000
    timeout_seconds: float = 20.0
    allowed_domains: list[str] = Field(default_factory=list)
    blocked_domains: list[str] = Field(default_factory=list)

    def domain_allowed(self, domain: str) -> bool:
        domain = domain.lower()
        if self.blocked_domains and any(
            domain == blocked or domain.endswith(f".{blocked}")
            for blocked in (d.lower() for d in self.blocked_domains)
        ):
            return False
        if self.allowed_domains:
            return any(
                domain == allowed or domain.endswith(f".{allowed}")
                for allowed in (d.lower() for d in self.allowed_domains)
            )
        return True
