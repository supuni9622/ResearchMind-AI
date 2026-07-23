"""Compact JSON-safe LangGraph state owned by ResearchMind."""

from __future__ import annotations

import json
from typing import TypedDict

RESEARCH_RUNTIME_STATE_SCHEMA_VERSION = 1


class ResearchRuntimeState(TypedDict, total=False):
    schema_version: int
    research_run_id: str
    graph_thread_id: str
    owner_id: str
    status: str
    pause_after_initialize: bool
    completed: bool


def validate_json_state(state: ResearchRuntimeState) -> None:
    """Fail early if a node attempts to place a non-checkpointable value in state."""

    json.dumps(state, sort_keys=True, separators=(",", ":"))
