"""LangGraph workflow compilation for bounded single-agent research stages."""

from app.ai.runtime.research.workflows.multi_wave_research import compile_multi_wave_research_graph
from app.ai.runtime.research.workflows.task_research import compile_task_research_graph

__all__ = ["compile_multi_wave_research_graph", "compile_task_research_graph"]
