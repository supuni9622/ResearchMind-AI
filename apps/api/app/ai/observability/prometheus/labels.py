"""
Shared bounded-label normalization helpers (Prometheus Grafana
Observability PRD §15 "Provider and model labels"). Kept out of
`names.py` (a pure data registry) and out of business services (which
must not decide Prometheus-facing label vocabularies themselves).
"""

from __future__ import annotations

_MODEL_FAMILY_PREFIXES: tuple[tuple[str, str], ...] = (
    ("gpt", "gpt"),
    ("o1", "gpt"),
    ("o3", "gpt"),
    ("claude", "claude"),
    ("gemini", "gemini"),
    ("llama", "llama"),
    ("deepseek", "deepseek"),
    ("qwen", "llama"),
)


def normalize_model_family(model: str | None) -> str:
    """Maps an arbitrary model string to one of a small, fixed set of
    families so the `model_family` label can never carry raw,
    unbounded model identifiers as Prometheus label values."""

    if not model:
        return "unknown"

    lowered = model.lower()

    for prefix, family in _MODEL_FAMILY_PREFIXES:
        if prefix in lowered:
            return family

    return "unknown"
