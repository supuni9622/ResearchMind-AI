from __future__ import annotations

from enum import StrEnum


class RuntimeType(StrEnum):
    """
    Which runtime is consuming a `GenerationResult` — resolved from
    `GenerationRequest.runtime` (PRD §13) to select which runtime
    contract/validators apply (PRD §7). Distinct from
    `caching.enums.CacheRuntime`, which drives cache policy rather than
    output-correctness requirements.
    """

    CHAT = "chat"

    RESEARCH = "research"

    PLANNER = "planner"

    REVIEWER = "reviewer"

    AGENT = "agent"

    MCP = "mcp"
