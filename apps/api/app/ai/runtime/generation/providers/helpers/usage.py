from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Usage:
    prompt_tokens: int = 0

    completion_tokens: int = 0

    reasoning_tokens: int = 0

    cached_tokens: int = 0

    total_tokens: int = 0
