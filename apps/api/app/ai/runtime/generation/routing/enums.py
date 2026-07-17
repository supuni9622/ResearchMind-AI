from __future__ import annotations

from enum import StrEnum


class RoutingStrategy(StrEnum):
    """
    Task-oriented routing objectives.

    Callers (agents, planners, runtime services) pick a strategy that
    describes what they need done, not which model to use — the
    scoring engine resolves the strategy into an actual model. See
    `routing/scoring/weights.py` for the weight profile each of these
    maps to.
    """

    AUTO = "auto"

    FAST = "fast"

    CHEAP = "cheap"

    QUALITY = "quality"

    REASONING = "reasoning"

    CODING = "coding"

    LONG_CONTEXT = "long_context"

    STRUCTURED_OUTPUT = "structured_output"

    SUMMARIZATION = "summarization"

    CLASSIFICATION = "classification"

    EXTRACTION = "extraction"

    VALIDATION = "validation"

    PLANNING = "planning"

    REVIEW = "review"

    LOCAL = "local"


class RequiredCapability(StrEnum):
    """
    Capability gates a caller can require of a routed model. Each value
    maps to a boolean field on `ProviderCapabilities` — see
    `routing/service.py::_CAPABILITY_FIELDS`.
    """

    STREAMING = "streaming"

    STRUCTURED_OUTPUT = "structured_output"

    TOOL_CALLING = "tool_calling"

    REASONING = "reasoning"

    VISION = "vision"

    JSON_MODE = "json_mode"
