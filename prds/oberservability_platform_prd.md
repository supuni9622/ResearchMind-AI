# AI Runtime Observability Platform PRD

**Document:** `ai_runtime_observability_prd.md`
**Phase:** 3.9
**Status:** Core Platform Implemented (Generation runtime wired end-to-end; Retrieval/Streaming/Research metrics scaffolded, not yet artifact-wired)
**Owner:** ResearchMind AI
**Last Updated:** 2026-07-18

---

# 1. Overview

The AI Runtime Observability Platform provides standardized visibility into
all AI runtime executions inside ResearchMind.

Unlike infrastructure observability systems (Prometheus, Grafana,
OpenTelemetry), this platform focuses specifically on:

- AI execution metrics
- AI costs
- Runtime statistics
- Runtime reports
- Evaluation instrumentation
- Benchmark instrumentation
- Artifact persistence

The platform serves as the engineering foundation for:

- Evaluation Platform
- Research Runtime
- Agent Platform
- MCP Platform
- Production Monitoring

---

# 2. Goals

The platform should answer questions such as:

### Runtime

- Which model answered the request?
- How long did it take?
- How many retries occurred?
- Was cache used?
- Was regeneration required?

### Cost

- How many tokens were consumed?
- What was the estimated cost?
- Which provider is most expensive?
- Which research session costs the most?

### Quality

- Are validation scores degrading?
- Are hallucinations increasing?
- Are guardrail failures increasing?

### Performance

- Which stage is slow?
- What is the TTFT?
- What is the average TPS?
- Which providers are unstable?

---

# 3. Architectural Philosophy

ResearchMind owns:

- metrics
- statistics
- cost tracking
- reports
- artifacts
- benchmark instrumentation
- evaluation instrumentation

LangSmith owns:

- tracing
- experiments
- datasets
- comparisons

Infrastructure platforms own:

- Prometheus
- Grafana
- OpenTelemetry
- Jaeger
- Alerting

Infrastructure observability is intentionally deferred until
Production Platform phases.

---

# 4. Non Goals

This phase does NOT implement:

- Prometheus
- Grafana
- Jaeger
- OpenTelemetry
- Kubernetes metrics
- Infrastructure dashboards
- Distributed tracing
- Alerting systems
- APM systems

These belong to future production phases.

---

# 5. Responsibilities

---

# 5.1 Runtime Metrics Platform

Provide standardized metrics for every AI runtime.

Metrics must be provider-independent.

---

## Request Metrics

Track:

```python
request_id
generation_id
runtime
provider
model
session_id
research_id
user_id
```

---

## Execution Metrics

Track:

```python
latency_ms
ttft_ms
tps
retries
regenerations
cache_hit
cache_level
success
error_type
```

---

## Token Metrics

Track:

```python
prompt_tokens
completion_tokens
total_tokens
cached_tokens
saved_tokens
```

---

## Cost Metrics

Track:

```python
estimated_cost_usd
provider_cost_usd
session_cost_usd
research_cost_usd
daily_cost_usd
```

---

## Validation Metrics

Track:

```python
validation_score
hallucination_score
runtime_score
citation_score
groundedness_score
```

---

## Guardrail Metrics

Track:

```python
risk_score
blocked
violations
policy_name
```

---

# 5.2 Retrieval Metrics Platform

Track retrieval runtime statistics.

---

Metrics:

```python
dense_latency_ms
sparse_latency_ms
rerank_latency_ms
context_build_latency_ms

retrieved_chunks
expanded_chunks
compressed_chunks
citations_count
```

---

Additional Metrics:

```python
retrieval_strategy
reranker_provider
compression_provider
guardrail_provider
```

---

# 5.3 Streaming Metrics Platform

Provide observability for streaming execution.

---

Metrics:

```python
ttft_ms
stream_duration_ms
tokens_per_second
events_sent
disconnects
cancelled
completed
```

---

## Event Timeline

Capture:

```python
request_started
provider_started
first_token
last_token
stream_completed
stream_cancelled
```

---

# 5.4 Research Metrics Platform

Future runtime metrics for deep research.

---

Metrics:

```python
planning_duration_ms
research_duration_ms
review_duration_ms

sub_questions
tool_calls
mcp_calls
iterations

total_cost
total_tokens
```

---

# 5.5 Agent Metrics Platform

Future platform.

---

Metrics:

```python
agent_steps
tool_calls
iterations
approval_cycles
loop_count
completion_rate
```

---

# 6. Statistics Platform

Provide aggregate runtime statistics.

---

# Percentiles

Track:

```python
p50
p90
p95
p99
```

---

# Aggregations

Track:

```python
average_latency
average_cost
average_tokens
average_ttft
average_tps
error_rate
cache_hit_rate
hallucination_rate
```

---

# Provider Statistics

Track:

```python
provider_rankings
model_rankings
cost_rankings
latency_rankings
```

---

# Time Windows

Support:

```python
hourly
daily
weekly
monthly
```

---

# 7. Runtime Reports Platform

Generate human-readable reports.

---

## Reports

### Generation Report

Contains:

- latency
- tokens
- costs
- validation
- guardrails

---

### Retrieval Report

Contains:

- retrieval metrics
- reranking metrics
- compression metrics

---

### Research Report

Future:

- planning metrics
- tool metrics
- MCP metrics
- review metrics

---

### System Report

Contains:

- provider statistics
- cost statistics
- cache statistics

---

# 8. Artifact Platform

Observability data must be persisted as artifacts.

---

## Structure

```text
observability/

    metrics/
    statistics/
    reports/
```

---

## Example

```text
observability/

    {execution_id}/

        metrics.json
        statistics.json
        report.md
```

---

# 9. Canonical Models

---

## RuntimeMetricsSnapshot

Canonical execution metrics.

---

## RetrievalMetricsSnapshot

Canonical retrieval metrics.

---

## StreamingMetricsSnapshot

Canonical streaming metrics.

---

## StatisticsSnapshot

Aggregated statistics.

---

## RuntimeReport

Human-readable report.

---

# 10. Folder Structure

```text
app/ai/observability/

    models.py
    enums.py
    interfaces.py
    service.py
    create.py

    metrics/
    statistics/
    reports/
    artifacts/

    providers/

        langsmith/
```

---

# 11. LangSmith Integration

LangSmith should be heavily leveraged.

ResearchMind should NOT rebuild tracing infrastructure.

---

# 11.1 Tracing

LangSmith owns:

```python
request traces
nested traces
run trees
span visualization
execution graphs
```

ResearchMind responsibilities:

```python
trace metadata
runtime metadata
custom tags
custom metrics
```

---

# Guidelines

Every runtime execution should create traces:

```python
generation
retrieval
research
agent
mcp
evaluation
```

---

Recommended tags:

```python
provider
model
runtime
strategy
cache_hit
validation_score
cost
```

---

# 11.2 Datasets

LangSmith owns:

```python
golden datasets
evaluation datasets
research datasets
```

ResearchMind owns:

```python
dataset contracts
dataset schemas
dataset loaders
dataset versioning metadata
```

---

# 11.3 Experiments

LangSmith should be used for:

```python
prompt comparisons
model comparisons
retrieval comparisons
reranker comparisons
planner comparisons
```

---

ResearchMind owns:

```python
benchmark runners
experiment orchestration
experiment reports
```

---

# 11.4 Comparisons

LangSmith should provide:

```python
run comparisons
experiment comparisons
dataset comparisons
```

ResearchMind should persist:

```python
comparison reports
metrics snapshots
regression artifacts
```

---

# 12. Metrics Recorder Abstraction

Current abstraction should remain.

```python
MetricsRecorder
```

Implementations:

```python
NoOpMetricsRecorder
LangSmithMetricsRecorder
FuturePrometheusRecorder
```

Prometheus support is intentionally deferred.

---

# 13. Engineering Guidelines

---

# Single Source of Truth

Metrics must never be recomputed.

Metrics should always be derived from:

```python
GenerationResult
RetrievalResult
ResearchResult
```

---

# Provider Independence

Metrics must not depend on:

- OpenAI APIs
- Anthropic APIs
- LangChain internals

All metrics should remain canonical.

---

# Backward Compatibility

Adding new metrics must never break existing artifacts.

Prefer:

```python
field: float | None = None
```

over required fields.

---

# Best Effort Recording

Observability failures must never fail runtime execution.

Example:

```python
try:
    metrics.record()
except Exception:
    logger.exception(...)
```

---

# Artifact Persistence

Artifact persistence must be:

```python
best effort
never blocking
never fatal
```

---

# 14. Integration Points

The Observability Platform integrates with:

---

### Knowledge Platform

- Processing
- Chunking
- Embedding
- Retrieval
- Reranking
- Context

---

### Runtime Platform

- Generation
- Streaming
- Validation
- Guardrails
- Routing
- Cache

---

### Future Platforms

- Research Runtime
- Agent Runtime
- MCP Runtime
- Evaluation Platform

---

# 15. Exit Criteria

The platform is considered complete when:

---

## Runtime Metrics

- [x] Generation metrics complete — `build_generation_metrics_snapshot` (pre-existing, reused), wired end-to-end via `ObservabilityService.record_generation`, reachable from `GenerationService.generate()`, `GenerationService.stream_generate()` (via `StreamingService._stream_live`), **and** every caller of either — confirmed both `/research`+`/research/stream` and `/chat/stream`+`/chat/ws` route through these two methods, so no separate chat-specific wiring was needed (see §17 "Chat + Document Processing Wiring Scope")
- [x] Processing (Knowledge pipeline) metrics complete — `PipelineRuntimeMetrics` (pre-existing `app/ai/observability/{models,runtime,report}.py`, previously log-only) now also persisted via `ObservabilityService.record_processing()` under `ArtifactRuntime.PROCESSING`. Not an LLM execution, so no LangSmith trace — see §17.
- [x] Retrieval metrics complete — `RetrievalMetricsSnapshot` + `build_retrieval_metrics_snapshot`; `dense_latency_ms`/`sparse_latency_ms`/`rerank_latency_ms`/`reranker_provider` now populated in `RetrievalService.search_hybrid()`. Not yet wired to artifact persistence (no `record_retrieval` call site).
- [x] Streaming metrics complete — `StreamingMetricsSnapshot` + `build_streaming_metrics_snapshot` exist as canonical models; live streams instead record through the same `GenerationMetricsService`/`ObservabilityService` Generation uses (see §17 "Streaming Wiring Fix"), since a completed stream is represented as a `GenerationResult` with `statistics.streamed=True`.

---

## Statistics

- [x] Aggregations implemented — `average`, `rate` in `statistics/aggregator.py`
- [x] Percentiles implemented — `percentile`/`compute_percentiles` (p50/p90/p95/p99)
- [x] Provider rankings implemented — `rank_by_count`/`rank_by_average`

---

## Reports

- [x] Metrics reports implemented — `GenerationReportBuilder`, `RetrievalReportBuilder`
- [x] Statistics reports implemented — `SystemReportBuilder`

---

## Artifacts

- [x] Observability artifacts implemented — `ObservabilityArtifact`/`ObservabilityArtifactBuilder`/Writer/Reader, `ArtifactCategory.OBSERVABILITY`, policy-gated (`CHAT` → `SESSION`), best-effort persistence via `ObservabilityService.record_generation`. Wired for both the non-streaming and streaming Generation paths (`/research` and `/research/stream`); Retrieval/Research have no call site yet.

---

## LangSmith

- [x] Tracing integrated — `LangSmithTracer` wraps the provider call in `GenerationService._execute_once()` **and** `StreamingService._stream_live()`; real `Client.create_run`/`update_run`, gated on **both** `LANGSMITH_API_KEY` and `LANGSMITH_TRACING=true` (see §17). Generation runtime only (streaming and non-streaming) — Retrieval/Research/Agent runtimes are not yet traced.
- [ ] Dataset support integrated
- [ ] Experiment support integrated
- [ ] Comparison support integrated

---

# 16. Future Enhancements

Deferred to Production Platform:

- Prometheus
- Grafana
- OpenTelemetry
- Jaeger
- Alerting
- Dashboards
- Distributed tracing
- Infrastructure metrics

---

# 17. Implementation Notes (2026-07-18)

This section records what was actually built against this PRD, and where it
diverges from or narrows the plan above. It is additive documentation, not a
redefinition of scope — Section 15 is the authoritative checklist.

---

## Folder Structure — as built

Matches §10 exactly, added alongside the pre-existing (and unrelated, despite
the name collision) `app/ai/observability/{models,runtime,report,timer}.py`
used by the Knowledge Processing pipeline. Those files were left untouched.

---

## Settings

`app/core/settings.py` gained:

```python
langsmith_tracing: bool = False
langsmith_endpoint: str | None = None
langsmith_api_key: str | None = None
langsmith_project: str | None = "ResearchMind"
```

`get_langsmith_client()` passes `api_url=settings.langsmith_endpoint` through
to `langsmith.Client(...)`.

---

## LangSmith Enablement Gate

`create_runtime_tracer()`/`create_langsmith_metrics_recorder()`
(`app/ai/observability/providers/langsmith/create.py`) require **both**
`langsmith_api_key` and `langsmith_tracing=true` before returning real
(non-NoOp) instances — an API key alone does not enable tracing. This lets
ops keep the key configured in the environment while switching tracing off
(e.g. locally) without unsetting it. `LangSmithTracer`'s project name comes
from `settings.langsmith_project`, not `settings.app_name`.

---

## Storage Backend Caveat

`create_artifact_storage()` resolves unconditionally to `S3StorageService` —
there is no local-filesystem fallback and no localstack/S3 emulator in
`docker-compose.yml`. Running the observability artifact path locally
requires either real AWS credentials or a self-run S3-compatible emulator
with `AWS_S3_ENDPOINT_URL` pointed at it. Observability writes remain
best-effort (§13), so a missing/misconfigured bucket degrades silently
rather than breaking generation.

---

## Wiring Scope

`GenerationService` is instrumented end-to-end for both of its entry
points — `generate()` (tracer wraps `_execute_once()`) and
`stream_generate()`'s caller, `StreamingService._stream_live()` (tracer
wraps the live provider stream; see "Streaming Wiring Fix" below). Retrieval
and Research have canonical metrics snapshots and report builders but no
live call site persisting them yet — follow
`ObservabilityService.record_generation`'s shape (snapshot → report →
`ObservabilityArtifactBuilder` → policy-gated best-effort write) to extend.

---

## Streaming Wiring Fix (2026-07-18, post-initial-implementation)

The first pass of this PRD only instrumented `GenerationService.generate()`
— but the frontend's actual research flow calls `POST /research/stream`,
which never reaches `generate()`. That route goes
`ResearchService.stream_research()` → `StreamingService.stream_generate()`
→ `GenerationService.stream_generate()`, which calls
`generation_provider.stream(request)` directly, bypassing `_execute_once()`
entirely. Verified live: LangSmith showed 0 traces and the S3 artifact
bucket had no `observability/` prefix after a real `/research/stream` call,
even with tracing correctly configured — the request succeeded and the
tracer/observability code simply wasn't on the code path being executed.

Fix: `GenerationService` gained three read-only properties —
`metrics_service`, `observability_service`, `tracer` — exposing the same
instances `generate()` uses (mirroring the pre-existing `registry`
property, added for the same reason). `StreamingService` gained matching
optional constructor params of the same names/defaults, wired in
`streaming/create.py::create_streaming_service()` from
`generation_service.{metrics_service,observability_service,tracer}` so
streamed and non-streamed generations trace and record through the
identical instances rather than composing separate ones.

In `StreamingService._stream_live()`: the live provider stream is now
wrapped in `self._tracer.trace(name="generation", tags={..., "streamed":
True})`. Token/cost statistics — previously only computed when a
`CachingService` was wired, purely to build a `GenerationResult` for
`CachingService.store()` — are now built unconditionally once a stream
completes successfully (`_build_stream_result()`), so
`GenerationMetricsService.record()` and
`ObservabilityService.record_generation()` always run, mirroring
`generate()`'s unconditional metrics recording. On a mid-stream
`GenerationError`, neither runs — consistent with `generate()`, which also
only records metrics on success.

---

## Chat + Document Processing Wiring Scope (2026-07-18)

Following a request to cover every path, not just research: scoped every
AI-driven route in `api/v1/*` to find what's covered versus what has zero
observability.

**Chat needed no new wiring.** Both `stream_chat` and `stream_chat_ws`
(`api/v1/chat.py`) call `StreamingService.stream_generate()` directly — the
exact method the Streaming Wiring Fix above instrumented. Chat gets tracing
and artifact persistence "for free" from that fix; there is no separate
chat-specific generation path.

**Document processing was a real, separate gap.** `ProcessingService`
(`ai/knowledge/processing/service.py`) is a fundamentally different
pipeline — parse → chunk → embed → index, no LLM call at all — so it was
never reachable through `GenerationService`/`StreamingService` and had no
equivalent of its own. It already computed a `PipelineRuntimeMetrics` via
the pre-existing `RuntimeMetricsCollector` (`ai/observability/runtime.py`,
an older module, see §17 "Folder Structure — as built"), but the result was
only ever passed to `RuntimeReportBuilder.build()` and logged
(`processing.runtime_metrics`) — never persisted, never traced.

Fix: `ObservabilityService` gained `record_processing(*, metrics:
PipelineRuntimeMetrics, document_id: UUID, owner_id: str | None = None)`,
mirroring `record_generation`'s shape exactly (best-effort, policy-gated,
builds a report via the pipeline's own pre-existing `RuntimeReportBuilder`
rather than a new one, persists via `ObservabilityArtifactBuilder`). A new
`ArtifactRuntime.PROCESSING` enum value and a `(PROCESSING, OBSERVABILITY)
-> SHORT_TERM` policy rule were added — `SHORT_TERM` was a judgment call
(processing metrics are operational/debugging data, not canonical business
content like Research, but also not session-scoped like Chat since
documents aren't tied to a session). `ProcessingService` gained an optional
`observability_service` constructor param (`None` skips entirely, same
opt-in shape as every other optional collaborator in this codebase), wired
in both composition roots that construct it — `bootstrap/worker.py` (the
real async queue worker) and `dependencies/upload.py` (FastAPI DI). No
`RuntimeTracer`/LangSmith involvement here — there's no LLM call to trace,
only pipeline stage timings, consistent with this PRD's own boundary that
LangSmith is reserved for generation-type executions.

Everything else scoped (`/research/citations`, `GET /research/{id}`,
`/retrieve*`, `GET /documents`) has no generation step and nothing to
instrument. `evaluation.py`/`reports.py`/`feedback.py`/`admin.py` are
empty, unregistered placeholder files — not live routes.

---

## Missing Policy Rule Fix (2026-07-18)

After the fixes above, live verification showed LangSmith traces appearing
correctly for `/research/stream` but **zero S3 observability artifacts** —
tracing and artifact persistence are gated independently, and only the
latter was broken. Root cause: `ResearchService` tags every
`GenerationRequest` with `artifact_runtime=ArtifactRuntime.RESEARCH`
(`research/service.py:99,192`), but `DEFAULT_ARTIFACT_POLICY_RULES`
(`artifacts/policies/models.py`) only had an `OBSERVABILITY` rule for
`CHAT` (and, after the Processing fix, `PROCESSING`) — not `RESEARCH`.
`ArtifactPolicyService.resolve_policy()` fails safe to `ArtifactPolicy.NEVER`
for any `(runtime, category)` pair with no explicit rule, so
`ObservabilityService.record_generation()` silently skipped every research
write (`logger.debug("artifacts.observability.skipped", ...)` — not even a
warning, so nothing surfaced in normal logs).

Fix: added `ArtifactPolicyRule(runtime=ArtifactRuntime.RESEARCH,
category=ArtifactCategory.OBSERVABILITY, policy=ArtifactPolicy.PERMANENT)`,
matching Research's own artifact policy (Category 1, canonical, always
permanent). Chat was never affected — `api/v1/chat.py` already tags
requests `ArtifactRuntime.CHAT`, which had an `OBSERVABILITY` rule from the
start. Added a regression test
(`test_research_observability_persists_permanently`) asserting the
resolved policy directly, since the bug was invisible at the unit level —
every existing `ObservabilityService`/`GenerationService` test mocked the
policy service (`should_persist.return_value = True`), so none of them
exercised the real default rule table with `ArtifactRuntime.RESEARCH`.

---

## Trace Input/Output/Token Fix (2026-07-18)

Once artifacts were landing in S3, the user checked the LangSmith trace
detail view directly and found: the Input panel only showed the
`provider`/`model`/`runtime`/`streamed` tags (not the actual prompt), the
Output panel said "No outputs", and the Monitoring dashboard's LLM Calls
tab only had a count — no latency percentiles, no cost, no token charts.

Root cause: `RuntimeTracer.trace()`'s original signature took only `tags`,
which `LangSmithTracer` passed straight through as `create_run(inputs=tags
or {}, ...)` — i.e. the metadata dict was masquerading as the actual input,
and `update_run()` never received an `outputs` argument at all. There was
no way for a caller to hand the tracer the real prompt, the real completion
content, or token counts, because the interface had no seam for it.

Fix: `RuntimeTracer.trace()` gained an `inputs: dict[str, Any] | None`
parameter (the real prompt) and now returns a context manager yielding a
`TraceHandle` (new ABC, `tracing.py`) with one method,
`set_output(*, content=None, prompt_tokens=None, completion_tokens=None,
total_tokens=None)`, which callers invoke once the result is known but
before the trace closes. `LangSmithTracer.trace()`:
- passes `inputs=inputs or {}` to `create_run()` (the real prompt now shows
  in the Input panel);
- moves the provider/model/runtime tags into `extra={"metadata": {...,
  "ls_provider": ..., "ls_model_name": ...}}` — `ls_provider`/`ls_model_name`
  are the specific keys LangSmith's own cost calculator looks for to price
  well-known models automatically (best-effort: this is LangSmith's
  documented convention, not something verified against a live LangSmith
  account in this environment — if Cost & Tokens still don't populate,
  the model name string needs to match one LangSmith recognizes);
- its `TraceHandle.set_output()` builds `outputs={"content": ...,
  "usage_metadata": {"input_tokens", "output_tokens", "total_tokens"}}` —
  the `usage_metadata` shape LangChain/LangSmith use for token accounting —
  passed to `update_run(outputs=...)`.

Both callers updated: `GenerationService._execute_once()` passes
`inputs={"prompt": request.user_prompt}` and calls `trace_handle.
set_output(content=result.content, prompt_tokens=..., completion_tokens=...,
total_tokens=...)` from `result.statistics` right after the provider call,
still inside the `with` block. `StreamingService._stream_live()` passes the
same `inputs` and calls `trace_handle.set_output(content="".join(
content_parts))` right after the stream loop finishes (still inside the
`with` block) — **content only, no token counts**: those come from
`_build_stream_result()`'s `count_tokens()` calls, which run *after* the
trace closes and deliberately stay outside the try/except that wraps the
trace block, so a token-counting failure surfaces exactly as it did before
this change rather than being swallowed into a synthetic stream ERROR
event after real content already reached the client.

`NoOpTracer` gained a matching `_NoOpTraceHandle` whose `set_output()` is a
no-op, so every caller works unchanged with tracing off. Existing tracer
tests were updated (`__enter__` now returns a handle, not `None`) and
new tests cover `inputs`/`extra.metadata`/`set_output` → `outputs` wiring
directly against the (mocked) LangSmith client.

---

## Streaming Validation/Guardrail Scoring (2026-07-18)

Once traces/artifacts were both landing correctly, inspecting a real
`metrics.json` for a streamed generation showed `validation_score`,
`hallucination_score`, `runtime_score`, and `guardrail_risk_score` all
`null`. Root cause: `GenerationService.stream_generate()` only runs
*input*-side guardrails before generation starts (see its own docstring —
no regeneration loop, no fallback); it never calls
`_enforce_generation_guardrails()` or `ValidationService.validate()`, both
of which are `_execute_once()`-only (the non-streaming path). So
`result.validation`/`result.guardrails` are structurally `None` for every
streamed response — `/research/stream` and `/chat/stream` alike — and the
snapshot builder was correctly reporting "no score computed," not lying.

This is a Generation/Streaming Platform gap, not an observability bug, but
closing it enough to at least *record* the scores (never block on them —
tokens already reached the client, there's nothing left to stop) was
in scope to fix:

- New `GenerationService.score_completed_stream(*, request, result) ->
  GenerationResult` — calls `guardrail_service.evaluate()` and
  `validation_service.validate()` (the same two calls `_execute_once()`
  makes) but **never raises**: a `blocked=True` guardrail verdict is
  recorded on `result.guardrails`, not turned into a
  `GuardrailViolationError`, and either call failing outright is
  logged+swallowed rather than propagated, since this runs after the
  client-facing work is already done.
- `StreamingService._stream_live()` calls it immediately after
  `_build_stream_result()`, before caching/artifact-persistence/metrics —
  so the cached result, the stream artifact, and the
  `GenerationMetricsSnapshot` all see the (possibly-populated)
  `validation`/`guardrails` fields.
- No new constructor params anywhere: `score_completed_stream()` reuses
  `GenerationService`'s own already-wired `guardrail_service`/
  `validation_service` (`StreamingService` never held its own copies of
  these — it already delegates everything generation-related to
  `GenerationService`).

**Operational caveat, verified (2026-07-18) — corrected from the initial,
overly-cautious version of this note**: since `guardrail_service`/
`validation_service` are unconditionally wired in production, every
completed stream now runs a full guardrail evaluation + validation pass in
the background after the last token already reached the client — real
extra CPU per streamed request. The initial write-up of this fix also
warned this "may" add extra provider API calls/cost if any registered
guardrail/validator makes its own LLM call (e.g. an LLM-based
hallucination check). That was checked directly against every guardrail
under `app/ai/guardrails/` and every validator under `app/ai/runtime/
generation/validation/`: **none of them call an LLM today.** Every check
is rule-based/regex/lexical-overlap, or an explicit permissive MVP stub
(`moderation.py`/`toxicity.py` are literally commented as deferred to a
future real classifier; `hallucination_validator.py`'s own docstring says
"Deterministic, no-LLM groundedness proxy... avoid expensive/LLM calls").
So today, `score_completed_stream()` costs CPU only — **zero additional
provider spend**.

**Forward-looking policy (per explicit direction): if an LLM-based
guardrail or validator is ever added, it must default to a Groq model —
never OpenAI, Claude, or Gemini** — specifically so this background,
non-blocking scoring pass (which runs unconditionally, after the response
already reached the client, on every single streamed request) can never
silently start costing real money on an expensive frontier model just
because someone wired the default provider. `GenerationProvider.GROQ`
(`enums.py:7`) with `catalog/models.py`'s `LLAMA_3_3_70B`
(`model_name="llama-3.3-70b-versatile"`, `cost_per_input_1m=0.59`, the
cheapest/fastest catalog entry) is the designated choice when that day
comes. No code changes needed now — there is nothing to wire yet — this is
a constraint for whoever adds the first LLM-based check to respect.

---

## Known Gaps

- `StatisticsSnapshot.error_rate` is always `None` for Generation stats —
  `GenerationMetricsService.record()` only runs on successful results, so a
  batch of snapshots can't carry failures to compute a rate from.
- `RetrievalMetricsSnapshot.expanded_chunks`/`compression_provider`/
  `guardrail_provider` are always `None` — `ContextBuilderService` doesn't
  track a before/after chunk-count delta or record which
  compression/guardrail strategy ran.
- `AgentMetricsSnapshot` has no builder — `app/ai/agents/` doesn't exist yet.
- No persistent metrics store/query API; Statistics Platform is pure
  aggregation over a caller-assembled list, matching this PRD's own
  deferral of Prometheus/Grafana-style infra to the Production Platform
  phase.

---

# Final Architectural Principle

ResearchMind owns:

```text
Metrics
Statistics
Costs
Reports
Artifacts
Evaluation Contracts
Benchmark Instrumentation
```

LangSmith owns:

```text
Tracing
Datasets
Experiments
Comparisons
```

Infrastructure platforms own:

```text
Prometheus
Grafana
OpenTelemetry
Jaeger
Alerting
```

This separation prevents ResearchMind from rebuilding mature observability systems while retaining ownership of all AI-specific engineering concerns.
