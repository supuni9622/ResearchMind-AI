"""Paper-search execution policy -- budgets/limits, settings-driven.

`PaperSearchService` enforces this around every provider call so limits live
in one place rather than scattered across callers (mirrors
`app.ai.tools.web_search.policies`).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PaperSearchPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    max_results_per_call: int = 5
    timeout_seconds: float = 20.0
