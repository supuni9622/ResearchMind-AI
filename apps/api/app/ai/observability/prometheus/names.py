"""
Central, bounded metric registry (Prometheus Grafana Observability PRD
§13/§14/§15/§16). Every metric `PrometheusMetricsRecorder` is allowed to
create is declared here -- name, Prometheus type, description, and its
fixed label schema. A call site passing an unregistered `metric`/
`operation` key is a silent no-op (see `recorder.py`): this is what
keeps arbitrary business-service call sites from accidentally creating
unbounded-cardinality series, per PRD §13 "unknown metrics must not be
created accidentally at arbitrary call sites."

Logical keys (the left-hand side of each dict) are the exact strings
already passed as `metric=`/`operation=` throughout the codebase (see
`app/infrastructure/metrics/*.py` and `app/ai/memory/observability/
metrics.py`) -- this module only adds the Prometheus-facing name/type/
label mapping on top, it does not introduce a second naming scheme.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.ai.memory.observability.metrics import (
    CONTEXT_DURABLE_AVAILABLE,
    CONTEXT_DURABLE_EMPTY,
    CONTEXT_ITEMS_OMITTED,
    CONTEXT_LATENCY,
    CONTEXT_REQUESTS,
    CONTEXT_RETRIEVAL_SKIPPED,
    CONTEXT_TOKEN_SHARE,
    CONTEXT_TOKENS_DROPPED,
    CONTEXT_TOKENS_SELECTED,
    DURABLE_SEARCH_LATENCY,
    EMBEDDING_LATENCY,
    EXTRACTION_EMPTY,
    EXTRACTION_EVALUATED,
    EXTRACTION_FAILED,
    EXTRACTION_LATENCY,
    EXTRACTION_REQUESTED,
    EXTRACTION_SKIPPED,
    EXTRACTION_SUCCEEDED,
    LIFECYCLE_DELETED,
    LIFECYCLE_DURATION,
    LIFECYCLE_EXAMINED,
    LIFECYCLE_FAILED,
    LIFECYCLE_LAST_SUCCESS,
    LIFECYCLE_OLDEST_CANDIDATE_AGE,
    MEMORY_COUNT,
    MEMORY_CREATED,
    MEMORY_DUPLICATE,
    MEMORY_HITS,
    MEMORY_MISSES,
    MEMORY_UPDATED,
    PARALLEL_SEARCH,
    REMEMBER_LATENCY,
    RESEARCH_SEARCH,
    SEARCH_LATENCY,
    SEMANTIC_SEARCH,
    SESSION_DUPLICATES_REMOVED,
    SESSION_ITEMS_LOADED,
)
from app.infrastructure.metrics.cache import (
    CACHE_COST_SAVED_USD_TOTAL,
    CACHE_HITS_TOTAL,
    CACHE_MISSES_TOTAL,
    CACHE_OPERATION_DURATION,
    CACHE_OPERATIONS_TOTAL,
    CACHE_TOKENS_SAVED_TOTAL,
)
from app.infrastructure.metrics.generation import (
    GENERATION_CACHE_HITS_TOTAL,
    GENERATION_COST_USD_TOTAL,
    GENERATION_FAILURES_TOTAL,
    GENERATION_GUARDRAIL_BLOCKS_TOTAL,
    GENERATION_HALLUCINATION_FLAGS_TOTAL,
    GENERATION_INPUT_TOKENS_TOTAL,
    GENERATION_OUTPUT_TOKENS_TOTAL,
    GENERATION_REGENERATIONS_TOTAL,
    GENERATION_REQUESTS_TOTAL,
    GENERATION_RETRIES_TOTAL,
    GENERATION_RUNTIME_VALIDATION_FAILURES_TOTAL,
    GENERATION_VALIDATION_FAILURES_TOTAL,
)
from app.infrastructure.metrics.guardrails import (
    GUARDRAIL_BLOCKS_TOTAL,
    GUARDRAIL_CHECKS_TOTAL,
    GUARDRAIL_FAILURES_TOTAL,
    PII_DETECTIONS,
    POLICY_VIOLATIONS,
    PROMPT_INJECTION_ATTEMPTS,
)
from app.infrastructure.metrics.mcp import (
    MCP_SERVER_HEALTH,
    MCP_TOOL_DURATION,
    MCP_TOOL_FAILURES_TOTAL,
    MCP_TOOL_REQUESTS_TOTAL,
    MCP_TOOL_RESULTS_TOTAL,
)
from app.infrastructure.metrics.research import (
    RESEARCH_DURATION,
    RESEARCH_REVIEW_DECISIONS_TOTAL,
    RESEARCH_RUN_DURATION,
    RESEARCH_RUNS_COMPLETED_TOTAL,
    RESEARCH_RUNS_FAILED_TOTAL,
    RESEARCH_RUNS_TOTAL,
)
from app.infrastructure.metrics.web_search import (
    WEB_SEARCH_DURATION,
    WEB_SEARCH_FAILURES_TOTAL,
    WEB_SEARCH_REQUESTS_TOTAL,
    WEB_SEARCH_RESULTS_TOTAL,
    WEB_SEARCH_SELECTED_RESULTS_TOTAL,
)

MetricKind = Literal["counter", "histogram", "gauge"]

#: Short buckets for HTTP request latency (PRD §16).
HTTP_BUCKETS: tuple[float, ...] = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
)

#: Longer buckets for AI/tool-call latency (PRD §16).
RUNTIME_BUCKETS: tuple[float, ...] = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    30.0,
    60.0,
    120.0,
)

TOKEN_BUCKETS: tuple[float, ...] = (10, 25, 50, 100, 250, 500, 1_000, 2_000, 4_000)

#: Deep Research end-to-end run duration (E17 follow-up) -- minutes-to-hours
#: scale, since a run's wall-clock time legitimately includes
#: human-approval wait time at the plan/report/web-search checkpoints, not
#: just compute time. `RUNTIME_BUCKETS` above tops out at 120s, an order
#: of magnitude too small to say anything meaningful about this metric.
DEEP_RESEARCH_RUN_BUCKETS: tuple[float, ...] = (
    5.0,
    15.0,
    30.0,
    60.0,
    120.0,
    300.0,
    600.0,
    1800.0,
    3600.0,
    7200.0,
    14400.0,
)


@dataclass(frozen=True)
class MetricSpec:
    name: str
    description: str
    kind: MetricKind
    labels: tuple[str, ...] = field(default_factory=tuple)
    buckets: tuple[float, ...] | None = None


#: Populated by `increment()` calls.
COUNTER_METRICS: dict[str, MetricSpec] = {
    #
    # Generation (PRD §18)
    #
    GENERATION_REQUESTS_TOTAL: MetricSpec(
        "researchmind_generation_requests_total",
        "Total completed generation requests.",
        "counter",
        ("runtime", "provider", "model_family", "cache_hit"),
    ),
    GENERATION_FAILURES_TOTAL: MetricSpec(
        "researchmind_generation_failures_total",
        "Total generation requests that ultimately failed.",
        "counter",
        ("runtime", "failure_type"),
    ),
    GENERATION_RETRIES_TOTAL: MetricSpec(
        "researchmind_generation_retries_total",
        "Total generation provider retry/fallback attempts.",
        "counter",
        ("runtime", "provider"),
    ),
    GENERATION_REGENERATIONS_TOTAL: MetricSpec(
        "researchmind_generation_regenerations_total",
        "Total generation regeneration attempts.",
        "counter",
        ("runtime", "provider"),
    ),
    GENERATION_CACHE_HITS_TOTAL: MetricSpec(
        "researchmind_generation_cache_hits_total",
        "Total generation requests served from cache.",
        "counter",
        ("runtime",),
    ),
    GENERATION_VALIDATION_FAILURES_TOTAL: MetricSpec(
        "researchmind_generation_validation_failures_total",
        "Total generation results that failed output validation.",
        "counter",
        ("runtime",),
    ),
    GENERATION_HALLUCINATION_FLAGS_TOTAL: MetricSpec(
        "researchmind_generation_hallucination_flags_total",
        "Total generation results flagged for possible hallucination.",
        "counter",
        ("runtime",),
    ),
    GENERATION_RUNTIME_VALIDATION_FAILURES_TOTAL: MetricSpec(
        "researchmind_generation_runtime_validation_failures_total",
        "Total generation results that failed runtime validation.",
        "counter",
        ("runtime",),
    ),
    GENERATION_INPUT_TOKENS_TOTAL: MetricSpec(
        "researchmind_generation_input_tokens_total",
        "Total generation input (prompt) tokens.",
        "counter",
        ("runtime", "provider", "model_family"),
    ),
    GENERATION_OUTPUT_TOKENS_TOTAL: MetricSpec(
        "researchmind_generation_output_tokens_total",
        "Total generation output (completion) tokens.",
        "counter",
        ("runtime", "provider", "model_family"),
    ),
    GENERATION_COST_USD_TOTAL: MetricSpec(
        "researchmind_generation_cost_usd_total",
        "Total estimated generation cost in USD.",
        "counter",
        ("runtime", "provider", "model_family"),
    ),
    GENERATION_GUARDRAIL_BLOCKS_TOTAL: MetricSpec(
        "researchmind_generation_guardrail_blocks_total",
        "Total generation results blocked by guardrails.",
        "counter",
        ("runtime",),
    ),
    #
    # Guardrails (PRD §23)
    #
    GUARDRAIL_CHECKS_TOTAL: MetricSpec(
        "researchmind_guardrail_checks_total",
        "Total individual guardrail checks executed.",
        "counter",
        ("stage",),
    ),
    GUARDRAIL_BLOCKS_TOTAL: MetricSpec(
        "researchmind_guardrail_blocks_total",
        "Total requests blocked by guardrails.",
        "counter",
        ("action",),
    ),
    GUARDRAIL_FAILURES_TOTAL: MetricSpec(
        "researchmind_guardrail_failures_total",
        "Total guardrail checks that crashed.",
        "counter",
        ("stage",),
    ),
    PROMPT_INJECTION_ATTEMPTS: MetricSpec(
        "researchmind_prompt_injection_attempts_total",
        "Total detected prompt-injection/jailbreak issues.",
        "counter",
        ("stage", "category"),
    ),
    PII_DETECTIONS: MetricSpec(
        "researchmind_pii_detections_total",
        "Total detected PII issues.",
        "counter",
        ("stage", "category"),
    ),
    POLICY_VIOLATIONS: MetricSpec(
        "researchmind_policy_violations_total",
        "Total error/critical-severity guardrail issues.",
        "counter",
        ("stage", "category"),
    ),
    #
    # Cache (PRD §19)
    #
    CACHE_OPERATIONS_TOTAL: MetricSpec(
        "researchmind_cache_operations_total",
        "Total generation cache operations.",
        "counter",
        ("cache_level", "runtime", "operation", "status"),
    ),
    CACHE_HITS_TOTAL: MetricSpec(
        "researchmind_cache_hits_total",
        "Total generation cache hits.",
        "counter",
        ("cache_level", "runtime"),
    ),
    CACHE_MISSES_TOTAL: MetricSpec(
        "researchmind_cache_misses_total",
        "Total generation cache misses.",
        "counter",
        ("runtime",),
    ),
    CACHE_TOKENS_SAVED_TOTAL: MetricSpec(
        "researchmind_cache_tokens_saved_total",
        "Total tokens saved by a cache hit.",
        "counter",
        ("cache_level",),
    ),
    CACHE_COST_SAVED_USD_TOTAL: MetricSpec(
        "researchmind_cache_cost_saved_usd_total",
        "Total estimated USD cost saved by a cache hit.",
        "counter",
        ("cache_level",),
    ),
    #
    # Web search (PRD §21)
    #
    WEB_SEARCH_REQUESTS_TOTAL: MetricSpec(
        "researchmind_web_search_requests_total",
        "Total web-search requests.",
        "counter",
        ("provider", "status"),
    ),
    WEB_SEARCH_FAILURES_TOTAL: MetricSpec(
        "researchmind_web_search_failures_total",
        "Total failed web-search requests.",
        "counter",
        ("provider", "failure_type"),
    ),
    WEB_SEARCH_RESULTS_TOTAL: MetricSpec(
        "researchmind_web_search_results_total",
        "Total raw web-search results returned by a provider.",
        "counter",
        ("provider",),
    ),
    WEB_SEARCH_SELECTED_RESULTS_TOTAL: MetricSpec(
        "researchmind_web_search_selected_results_total",
        "Total web-search results kept after policy filtering.",
        "counter",
        ("provider",),
    ),
    #
    # MCP tools (PRD §22)
    #
    MCP_TOOL_REQUESTS_TOTAL: MetricSpec(
        "researchmind_mcp_tool_requests_total",
        "Total MCP tool call requests.",
        "counter",
        ("server", "tool", "status"),
    ),
    MCP_TOOL_FAILURES_TOTAL: MetricSpec(
        "researchmind_mcp_tool_failures_total",
        "Total failed MCP tool calls.",
        "counter",
        ("server", "tool", "error_type"),
    ),
    MCP_TOOL_RESULTS_TOTAL: MetricSpec(
        "researchmind_mcp_tool_results_total",
        "Total results returned by an MCP tool call.",
        "counter",
        ("server", "tool"),
    ),
    #
    # Research runtime (PRD §24, linear Research API only)
    #
    RESEARCH_RUNS_TOTAL: MetricSpec(
        "researchmind_research_runs_total",
        "Total research runs started.",
        "counter",
        ("source_mode",),
    ),
    RESEARCH_RUNS_COMPLETED_TOTAL: MetricSpec(
        "researchmind_research_runs_completed_total",
        "Total research runs completed successfully.",
        "counter",
        ("source_mode",),
    ),
    RESEARCH_RUNS_FAILED_TOTAL: MetricSpec(
        "researchmind_research_runs_failed_total",
        "Total research runs that failed.",
        "counter",
        ("source_mode", "failure_type"),
    ),
    #
    # Deep Research review (Research Runtime V1 graph's report-quality
    # checkpoint, distinct from run-level completed/failed above) -- fires
    # on every review cycle, including ones that loop back into revision,
    # not just the terminal one a run ends on.
    #
    RESEARCH_REVIEW_DECISIONS_TOTAL: MetricSpec(
        "researchmind_research_review_decisions_total",
        "Total Deep Research report reviews, by decision.",
        "counter",
        ("decision",),
    ),
    #
    # Memory (PRD §20) -- no labels at existing call sites today.
    #
    MEMORY_HITS: MetricSpec(
        "researchmind_memory_hits_total", "Total memory profile lookups with a hit.", "counter"
    ),
    MEMORY_MISSES: MetricSpec(
        "researchmind_memory_misses_total", "Total memory profile lookups with a miss.", "counter"
    ),
    MEMORY_COUNT: MetricSpec(
        "researchmind_memory_profile_writes_total", "Total memory profile writes.", "counter"
    ),
    CONTEXT_REQUESTS: MetricSpec(
        "researchmind_memory_context_requests_total",
        "Total memory-context build requests.",
        "counter",
    ),
    CONTEXT_DURABLE_AVAILABLE: MetricSpec(
        "researchmind_memory_context_durable_available_total",
        "Total memory-context requests where durable memory was available.",
        "counter",
    ),
    CONTEXT_DURABLE_EMPTY: MetricSpec(
        "researchmind_memory_context_durable_empty_total",
        "Total memory-context requests where durable memory was empty.",
        "counter",
    ),
    CONTEXT_RETRIEVAL_SKIPPED: MetricSpec(
        "researchmind_memory_context_retrieval_skipped_total",
        "Total memory-context requests that skipped durable retrieval.",
        "counter",
    ),
    SEMANTIC_SEARCH: MetricSpec(
        "researchmind_memory_semantic_search_total", "Total semantic-memory searches.", "counter"
    ),
    RESEARCH_SEARCH: MetricSpec(
        "researchmind_memory_research_search_total", "Total research-memory searches.", "counter"
    ),
    PARALLEL_SEARCH: MetricSpec(
        "researchmind_memory_parallel_search_total",
        "Total memory searches run in parallel.",
        "counter",
    ),
    SESSION_ITEMS_LOADED: MetricSpec(
        "researchmind_memory_session_items_loaded_total",
        "Total session-memory items loaded.",
        "counter",
    ),
    SESSION_DUPLICATES_REMOVED: MetricSpec(
        "researchmind_memory_session_duplicates_removed_total",
        "Total duplicate session-memory items removed.",
        "counter",
    ),
    EXTRACTION_EVALUATED: MetricSpec(
        "researchmind_memory_extraction_evaluated_total",
        "Total turns evaluated for memory extraction.",
        "counter",
    ),
    EXTRACTION_SKIPPED: MetricSpec(
        "researchmind_memory_extraction_skipped_total",
        "Total turns skipped for memory extraction.",
        "counter",
    ),
    EXTRACTION_REQUESTED: MetricSpec(
        "researchmind_memory_extraction_requested_total",
        "Total memory extraction LLM calls requested.",
        "counter",
    ),
    EXTRACTION_SUCCEEDED: MetricSpec(
        "researchmind_memory_extraction_succeeded_total",
        "Total memory extraction calls that succeeded.",
        "counter",
    ),
    EXTRACTION_FAILED: MetricSpec(
        "researchmind_memory_extraction_failed_total",
        "Total memory extraction calls that failed.",
        "counter",
    ),
    EXTRACTION_EMPTY: MetricSpec(
        "researchmind_memory_extraction_empty_total",
        "Total memory extraction calls that returned nothing.",
        "counter",
    ),
    MEMORY_CREATED: MetricSpec(
        "researchmind_memory_created_total", "Total new memories created.", "counter"
    ),
    MEMORY_UPDATED: MetricSpec(
        "researchmind_memory_updated_total", "Total existing memories updated.", "counter"
    ),
    MEMORY_DUPLICATE: MetricSpec(
        "researchmind_memory_duplicates_total", "Total duplicate memories detected.", "counter"
    ),
    LIFECYCLE_EXAMINED: MetricSpec(
        "researchmind_memory_lifecycle_examined_total",
        "Total durable-memory rows examined by lifecycle sweeps.",
        "counter",
    ),
    LIFECYCLE_DELETED: MetricSpec(
        "researchmind_memory_lifecycle_deleted_total",
        "Total durable-memory rows deleted by lifecycle sweeps.",
        "counter",
    ),
    LIFECYCLE_FAILED: MetricSpec(
        "researchmind_memory_lifecycle_failed_total",
        "Total durable-memory rows whose lifecycle deletion failed.",
        "counter",
    ),
    CONTEXT_ITEMS_OMITTED: MetricSpec(
        "researchmind_memory_context_items_omitted_total",
        "Total memory entries omitted by the coordinated token budget.",
        "counter",
        ("type",),
    ),
}

#: Populated by `record_duration()` calls (`operation=` is the lookup key).
DURATION_METRICS: dict[str, MetricSpec] = {
    "generation": MetricSpec(
        "researchmind_generation_duration_seconds",
        "Generation request duration.",
        "histogram",
        ("runtime", "provider"),
        RUNTIME_BUCKETS,
    ),
    CACHE_OPERATION_DURATION: MetricSpec(
        "researchmind_cache_operation_duration_seconds",
        "Generation cache operation duration.",
        "histogram",
        ("cache_level", "runtime", "operation"),
        RUNTIME_BUCKETS,
    ),
    WEB_SEARCH_DURATION: MetricSpec(
        "researchmind_web_search_duration_seconds",
        "Web-search call duration.",
        "histogram",
        ("provider",),
        RUNTIME_BUCKETS,
    ),
    MCP_TOOL_DURATION: MetricSpec(
        "researchmind_mcp_tool_duration_seconds",
        "MCP tool call duration.",
        "histogram",
        ("server", "tool"),
        RUNTIME_BUCKETS,
    ),
    RESEARCH_DURATION: MetricSpec(
        "researchmind_research_duration_seconds",
        "Research run duration.",
        "histogram",
        ("source_mode",),
        RUNTIME_BUCKETS,
    ),
    RESEARCH_RUN_DURATION: MetricSpec(
        "researchmind_deep_research_run_duration_seconds",
        "Deep Research end-to-end run duration, creation to terminal "
        "status -- includes human-approval wait time, minutes-to-hours "
        "scale, not directly comparable to researchmind_research_duration_seconds.",
        "histogram",
        (),
        DEEP_RESEARCH_RUN_BUCKETS,
    ),
    REMEMBER_LATENCY: MetricSpec(
        "researchmind_memory_remember_duration_seconds",
        "Memory write duration.",
        "histogram",
        (),
        RUNTIME_BUCKETS,
    ),
    SEARCH_LATENCY: MetricSpec(
        "researchmind_memory_search_duration_seconds",
        "Memory search duration.",
        "histogram",
        (),
        RUNTIME_BUCKETS,
    ),
    EMBEDDING_LATENCY: MetricSpec(
        "researchmind_memory_embedding_duration_seconds",
        "Memory query-embedding duration.",
        "histogram",
        (),
        RUNTIME_BUCKETS,
    ),
    CONTEXT_LATENCY: MetricSpec(
        "researchmind_memory_context_duration_seconds",
        "Memory-context build duration.",
        "histogram",
        (),
        RUNTIME_BUCKETS,
    ),
    DURABLE_SEARCH_LATENCY: MetricSpec(
        "researchmind_memory_durable_search_duration_seconds",
        "Durable-memory search duration.",
        "histogram",
        (),
        RUNTIME_BUCKETS,
    ),
    EXTRACTION_LATENCY: MetricSpec(
        "researchmind_memory_extraction_duration_seconds",
        "Memory extraction call duration.",
        "histogram",
        (),
        RUNTIME_BUCKETS,
    ),
    LIFECYCLE_DURATION: MetricSpec(
        "researchmind_memory_lifecycle_duration_seconds",
        "Memory lifecycle sweep duration.",
        "histogram",
        (),
        RUNTIME_BUCKETS,
    ),
}

#: Populated by `set_gauge()` calls.
GAUGE_METRICS: dict[str, MetricSpec] = {
    MCP_SERVER_HEALTH: MetricSpec(
        "researchmind_mcp_server_health",
        "MCP server health (1 = healthy, 0 = unhealthy).",
        "gauge",
        ("server",),
    ),
    LIFECYCLE_LAST_SUCCESS: MetricSpec(
        "researchmind_memory_lifecycle_last_success_timestamp_seconds",
        "Unix timestamp of the last successful lifecycle sweep.",
        "gauge",
    ),
    LIFECYCLE_OLDEST_CANDIDATE_AGE: MetricSpec(
        "researchmind_memory_lifecycle_oldest_candidate_age_seconds",
        "Age of the oldest lifecycle candidate in seconds.",
        "gauge",
    ),
}

#: Populated by `observe()` calls (non-duration histogram values). Empty
#: until a caller needs one -- PRD §39 rule 19: don't fabricate metrics
#: ahead of real behavior.
OBSERVE_METRICS: dict[str, MetricSpec] = {
    CONTEXT_TOKENS_SELECTED: MetricSpec(
        "researchmind_memory_context_tokens_selected",
        "Estimated tokens selected for a rendered memory block.",
        "histogram",
        (),
        TOKEN_BUCKETS,
    ),
    CONTEXT_TOKENS_DROPPED: MetricSpec(
        "researchmind_memory_context_tokens_dropped",
        "Estimated candidate tokens dropped from a memory block.",
        "histogram",
        (),
        TOKEN_BUCKETS,
    ),
    CONTEXT_TOKEN_SHARE: MetricSpec(
        "researchmind_memory_context_budget_utilization_ratio",
        "Fraction of the resolved memory token budget used.",
        "histogram",
        (),
        (0.1, 0.25, 0.5, 0.75, 0.9, 1.0),
    ),
}
