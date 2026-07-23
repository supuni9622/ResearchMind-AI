"""Versioned planner prompt; hidden reasoning is never persisted or streamed."""

from __future__ import annotations

from app.ai.runtime.research.planner.models import ResearchPlan

PLANNER_PROMPT_VERSION = "research-planner-v1"


def planner_system_prompt() -> str:
    return """You are the ResearchMind research planner. Produce only the requested JSON.
Create a bounded plan for grounded document research. Do not answer the question, invent
sources, cite documents, or include hidden reasoning. Prefer one focused task unless the
request clearly needs comparison, chronology, or multiple independent aspects. Every task
ID must be lowercase, stable, and dependency-safe.

Also set `rewritten_goal`: a self-contained restatement of the request that resolves
pronouns, implicit references, or shorthand (e.g. "compare it with X") using any background
memory supplied below, so the goal reads correctly without that memory attached. If no
background memory is supplied or none of it is relevant, set `rewritten_goal` to the
request verbatim."""


def planner_user_prompt(*, query: str, memory_context: str | None = None) -> str:
    memory_block = f"\n\n{memory_context}\n" if memory_context else ""
    return (
        "Plan this research request. Keep it within the supplied schema and no more than "
        "five tasks."
        f"{memory_block}"
        f"\n\nRequest: {query}"
    )


def planner_schema() -> dict:
    return ResearchPlan.model_json_schema()
