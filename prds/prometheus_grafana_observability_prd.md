# ResearchMind Prometheus and Grafana Observability PRD

**Document:** `prometheus_grafana_observability_prd.md`  
**Status:** Approved for Implementation  
**Priority:** High  
**Target Build Time:** 1–2 days  
**Primary Runtime Surfaces:** Chat, Research, Generation, Memory, Web Search, MCP Tools  
**Implementation Style:** Incremental, production-minded, backward-compatible, and intentionally limited in scope

---

# 1. Overview

ResearchMind already has meaningful runtime behavior across:

- Chat
- Research
- Generation
- Memory
- Web Search
- MCP tools
- model routing
- provider fallback
- validation
- guardrails
- caching
- artifact persistence
- structured logging
- LangSmith tracing
- generation cost accounting

The missing layer is aggregate operational monitoring.

LangSmith helps inspect individual AI traces. Structured logs help debug specific requests. PostgreSQL usage records help inspect owner-scoped cost history.

Prometheus and Grafana will add a different capability:

> Aggregate, time-series visibility into platform health, latency, failures, throughput, cost, cache behavior, tool behavior, and runtime trends.

The first implementation must remain small and practical.

The target architecture is:

```text
ResearchMind Runtime Platforms
        ↓
Metrics Recorder Interfaces
        ↓
Prometheus Metrics Recorder
        ↓
Private /metrics Endpoint
        ↓
Prometheus
        ↓
Grafana
        ↓
Dashboards and Alerts
```

This PRD does not redesign the current Observability Platform.

It activates a Prometheus-backed metrics sink and Grafana dashboards using the metrics that ResearchMind already emits or conceptually owns.

---

# 2. Problem

ResearchMind currently lacks one operational view that answers questions such as:

- Is the API healthy?
- Are requests becoming slower?
- Which generation provider is failing?
- Are fallback calls increasing?
- Is web search creating unexpected latency?
- Are MCP tool calls timing out?
- Is memory extraction running too often?
- Are cache hit rates decreasing?
- Are guardrails blocking more traffic than expected?
- Is a deployment causing an increase in errors?
- Is estimated generation cost increasing unexpectedly?
- Are research runs using too many external tools?

Current observability is distributed across:

- application logs
- LangSmith traces
- generation artifacts
- memory events
- database usage records
- provider-specific logs
- web-search metrics
- MCP metrics

These are useful for detailed debugging, but insufficient for aggregate platform monitoring and alerting.

---

# 3. Goals

Implement a production-ready but minimal Prometheus and Grafana integration that provides:

1. a private Prometheus-compatible `/metrics` endpoint;
2. application metrics exposed through existing recorder abstractions;
3. HTTP request metrics;
4. generation runtime metrics;
5. cache metrics;
6. memory metrics;
7. web-search and web-fetch metrics;
8. MCP tool metrics;
9. guardrail metrics;
10. Prometheus scraping through Docker Compose;
11. Grafana provisioning through source-controlled files;
12. four focused dashboards;
13. a small set of high-value alerts;
14. safe metric labels with bounded cardinality;
15. tests for recorder behavior and endpoint availability;
16. clear local setup and verification instructions.

---

# 4. Non-Goals

Do not implement the following in this milestone:

- OpenTelemetry platform-wide instrumentation
- Grafana Tempo
- Grafana Loki
- distributed tracing replacement
- replacement of LangSmith
- replacement of structured logging
- Kubernetes monitoring
- cloud-host metrics aggregation
- production PagerDuty or Opsgenie integration
- log shipping
- trace-to-log correlation
- full SRE platform
- multi-region monitoring
- automated SLO management
- advanced anomaly detection
- business analytics dashboards
- per-user Prometheus metrics
- per-request identifiers as metric labels
- automatic Grafana Cloud integration
- cAdvisor unless there is remaining time after the core milestone
- node-level host monitoring unless there is remaining time after the core milestone

---

# 5. Architectural Principles

## 5.1 Metrics remain platform-owned

ResearchMind platforms must record metrics through internal interfaces.

Business services must not directly import Prometheus collectors.

Correct:

```text
Generation Platform
        ↓
MetricsRecorder
        ↓
PrometheusMetricsRecorder
```

Avoid:

```text
GenerationService
        ↓
prometheus_client.Counter(...)
```

This preserves provider independence and allows future metric backends.

## 5.2 Prometheus is for aggregate telemetry

Prometheus stores:

- counters
- rates
- gauges
- latency distributions
- bounded dimensions
- aggregate operational health

Prometheus does not store:

- prompts
- user queries
- full URLs
- request IDs
- user IDs
- workspace IDs
- raw exception messages
- document IDs
- research IDs
- citation IDs
- tool arguments
- API keys
- access tokens

Those belong in:

- structured logs
- LangSmith
- artifacts
- PostgreSQL
- secure debugging records

## 5.3 Grafana configuration is source-controlled

Grafana data sources and dashboards must be provisioned through files.

Do not rely on manual dashboard creation as the canonical setup.

The repository must contain:

```text
infra/observability/grafana/
```

with:

- data-source provisioning
- dashboard provisioning
- dashboard JSON files

## 5.4 Metrics failures must not break user requests

Prometheus metric recording is best effort.

If a metric recorder fails:

- log the failure;
- do not fail Chat;
- do not fail Research;
- do not fail generation;
- do not fail web search;
- do not fail MCP execution;
- do not fail memory operations.

## 5.5 Start with a bounded metric set

Do not expose every runtime field as a metric label.

The first implementation must prioritize:

- health
- latency
- requests
- failures
- cost
- cache performance
- tool performance
- memory efficiency
- guardrail actions

---

# 6. Current Observability Responsibilities

ResearchMind should use each observability component for a distinct purpose.

| Component | Responsibility |
|---|---|
| LangSmith | AI trace inspection, prompts, model calls, tool sequences, individual research-run analysis |
| Structlog | detailed application events, errors, request context, correlation IDs |
| Prometheus | aggregate time-series counters, rates, histograms, gauges |
| Grafana | dashboards, trends, alerts |
| PostgreSQL usage ledger | owner-scoped generation and memory-extraction cost records |
| Artifacts | immutable runtime execution history and replay data |

The systems complement one another.

Prometheus and Grafana must not replace the existing tools.

---

# 7. Target Architecture

```text
Chat Runtime ───────────────────────┐
Research Runtime ───────────────────┤
Generation Platform ────────────────┤
Memory Platform ────────────────────┤
Web Search Platform ────────────────┤
MCP Tool Platform ──────────────────┤
Guardrails Platform ────────────────┤
Caching Platform ───────────────────┤
HTTP Middleware ────────────────────┤
                                   ▼
                         Metrics Recorder Layer
                                   │
                                   ▼
                      PrometheusMetricsRecorder
                                   │
                                   ▼
                         Private /metrics Route
                                   │
                                   ▼
                              Prometheus
                                   │
                                   ▼
                               Grafana
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
               Dashboards                       Alerts
```

---

# 8. Package Structure

Claude Code must inspect the repository before editing.

Use the current codebase conventions. The following is the target structure unless equivalent files already exist.

```text
apps/api/app/ai/observability/

├── metrics/
│   ├── __init__.py
│   ├── interfaces.py
│   ├── models.py
│   ├── names.py
│   ├── recorder.py
│   ├── registry.py
│   └── create.py
│
├── prometheus/
│   ├── __init__.py
│   ├── collectors.py
│   ├── recorder.py
│   ├── registry.py
│   ├── endpoint.py
│   └── middleware.py
│
└── create.py
```

Infrastructure:

```text
infra/observability/

├── prometheus/
│   ├── prometheus.yml
│   └── alerts.yml
│
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── prometheus.yml
│   │   └── dashboards/
│   │       └── dashboards.yml
│   │
│   └── dashboards/
│       ├── researchmind-overview.json
│       ├── generation-runtime.json
│       ├── research-tools.json
│       └── memory-runtime.json
│
└── README.md
```

Tests:

```text
tests/unit/ai/observability/
├── test_prometheus_recorder.py
├── test_metric_labels.py
├── test_metric_registry.py
└── test_metrics_endpoint.py

tests/integration/ai/
└── test_prometheus_metrics.py
```

---

# 9. Dependencies

Add:

```text
prometheus-client
```

Use the existing project package manager and dependency style.

Do not add:

- OpenTelemetry packages
- Grafana SDK packages
- Loki clients
- Tempo clients
- Prometheus Pushgateway clients

unless they are already required elsewhere.

---

# 10. Configuration

Add conservative settings.

Suggested environment variables:

```env
PROMETHEUS_ENABLED=true
PROMETHEUS_METRICS_PATH=/metrics
PROMETHEUS_INCLUDE_HTTP_METRICS=true
PROMETHEUS_INCLUDE_RUNTIME_METRICS=true
PROMETHEUS_INCLUDE_PROCESS_METRICS=true
PROMETHEUS_INCLUDE_PLATFORM_METRICS=true

GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
GRAFANA_PORT=3001

PROMETHEUS_PORT=9090
PROMETHEUS_SCRAPE_INTERVAL_SECONDS=15
PROMETHEUS_RETENTION_TIME=15d
```

Production note:

```text
GRAFANA_ADMIN_PASSWORD must not use the local default.
```

The settings model must validate:

- metrics path begins with `/`;
- ports are within valid range;
- scrape interval is positive;
- retention value is non-empty.

---

# 11. FastAPI Metrics Endpoint

Expose a Prometheus-compatible endpoint.

Target:

```text
GET /metrics
```

Requirements:

- mounted only when `PROMETHEUS_ENABLED=true`;
- no application authentication required inside the private network;
- must not be publicly exposed through production routing;
- returns Prometheus text exposition format;
- does not expose sensitive values;
- works with the application’s normal ASGI lifecycle.

Recommended approach:

```python
from prometheus_client import make_asgi_app

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

Integrate through the application composition root.

Do not scatter endpoint setup across unrelated modules.

---

# 12. Prometheus Registry

Use one canonical application registry.

Responsibilities:

- create collectors once;
- prevent duplicate registration;
- expose collectors to recorders;
- support test isolation;
- support future multiprocess configuration;
- avoid module-level registration side effects where possible.

Suggested contract:

```python
class PrometheusMetricRegistry:
    def get_counter(self, name: str, description: str, labels: tuple[str, ...]):
        ...

    def get_histogram(self, name: str, description: str, labels: tuple[str, ...]):
        ...

    def get_gauge(self, name: str, description: str, labels: tuple[str, ...]):
        ...
```

If the official Prometheus registry is used directly, wrap it through a small composition layer.

---

# 13. Metrics Recorder Interface

Preserve or extend current recorder abstractions.

Suggested interface:

```python
from typing import Protocol


class MetricsRecorder(Protocol):
    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        ...

    def observe(
        self,
        name: str,
        *,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        ...

    def set_gauge(
        self,
        name: str,
        *,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        ...
```

Provide:

```text
PrometheusMetricsRecorder
NoOpMetricsRecorder
```

Requirements:

- unknown metrics must not be created accidentally at arbitrary call sites;
- metric names should be registered centrally;
- unsupported labels must be rejected or filtered;
- recorder failures must fail open.

---

# 14. Metric Naming Convention

All application metrics must use this prefix:

```text
researchmind_
```

Prometheus conventions:

- counters end in `_total`;
- durations use `_seconds`;
- sizes use `_bytes`;
- monetary counters use `_usd_total`;
- ratios are calculated in PromQL, not stored as separate mutable metrics;
- use lowercase snake case.

Examples:

```text
researchmind_generation_requests_total
researchmind_generation_duration_seconds
researchmind_web_fetch_bytes_total
```

---

# 15. Label Policy

## Allowed labels

Only use bounded labels such as:

```text
runtime
provider
model_family
status
method
route
status_code
cache_level
operation
tool
server
transport
stage
category
action
failure_type
source_mode
policy_outcome
```

## Forbidden labels

Never use:

```text
owner_id
user_id
workspace_id
session_id
conversation_id
research_id
request_id
correlation_id
document_id
citation_id
artifact_id
query
prompt
URL
exception_message
email
access_token
API_key
```

## Route normalization

Use:

```text
/api/v1/research/{research_id}
```

Never:

```text
/api/v1/research/550e8400-e29b-41d4-a716-446655440000
```

## Provider and model labels

Provider is safe if bounded:

```text
groq
openai
anthropic
gemini
ollama
```

Prefer a bounded `model_family` value rather than arbitrary model strings:

```text
gpt
claude
gemini
llama
deepseek
unknown
```

---

# 16. Metric Types

| Metric behavior | Type |
|---|---|
| requests | Counter |
| failures | Counter |
| tokens | Counter |
| cost | Counter |
| tool calls | Counter |
| memory writes | Counter |
| active requests | Gauge |
| active research runs | Gauge |
| queue depth | Gauge |
| health state | Gauge |
| request duration | Histogram |
| provider duration | Histogram |
| tool duration | Histogram |
| memory duration | Histogram |

Prefer histograms over summaries because histograms can be aggregated across service instances.

Suggested latency buckets:

```python
(
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
```

Use shorter buckets for HTTP metrics and longer buckets for AI/tool operations where appropriate.

---

# 17. HTTP Metrics

Add ASGI/FastAPI middleware.

Metrics:

```text
researchmind_http_requests_total
researchmind_http_request_duration_seconds
researchmind_http_in_flight_requests
researchmind_http_errors_total
```

Labels:

```text
method
route
status_code
```

Behavior:

1. increment in-flight gauge;
2. record start time;
3. call downstream application;
4. record normalized route;
5. increment request counter;
6. observe duration;
7. increment error counter for unhandled failures;
8. decrement in-flight gauge in `finally`.

Exclude:

```text
/metrics
/health
```

from request-rate dashboards if they create noise. They may remain instrumented but should be filterable.

---

# 18. Generation Metrics

Metrics:

```text
researchmind_generation_requests_total
researchmind_generation_failures_total
researchmind_generation_duration_seconds
researchmind_generation_input_tokens_total
researchmind_generation_output_tokens_total
researchmind_generation_cost_usd_total
researchmind_generation_fallbacks_total
researchmind_generation_regenerations_total
researchmind_generation_validation_failures_total
researchmind_generation_guardrail_blocks_total
researchmind_generation_cache_hits_total
```

Labels:

```text
runtime
provider
model_family
status
cache_hit
```

Do not duplicate existing generation accounting logic.

Use values already available from:

- `GenerationResult`
- routing metadata
- cache metadata
- validation report
- guardrail report
- generation statistics

Record metrics once per completed generation attempt or final request according to the existing Generation Metrics Service semantics.

Avoid double-counting fallback attempts and final requests.

Recommended semantics:

- `generation_requests_total`: one per user-facing generation request;
- `generation_failures_total`: one per request that ultimately fails;
- `generation_fallbacks_total`: increment for each fallback provider used;
- `generation_duration_seconds`: total request generation duration;
- tokens and cost: actual final recorded usage including fallback calls if the current statistics include them.

---

# 19. Cache Metrics

Metrics:

```text
researchmind_cache_operations_total
researchmind_cache_hits_total
researchmind_cache_misses_total
researchmind_cache_operation_duration_seconds
researchmind_cache_tokens_saved_total
researchmind_cache_cost_saved_usd_total
```

Labels:

```text
cache_level
runtime
operation
status
```

Allowed cache levels:

```text
exact
semantic
session
```

Allowed operations:

```text
lookup
store
invalidate
```

---

# 20. Memory Metrics

Map current structured memory events into Prometheus.

Counters:

```text
researchmind_memory_context_requests_total
researchmind_memory_context_durable_available_total
researchmind_memory_context_durable_empty_total
researchmind_memory_context_retrieval_skipped_total

researchmind_memory_query_embedding_requests_total
researchmind_memory_query_embedding_cache_hits_total
researchmind_memory_query_embedding_cache_misses_total

researchmind_memory_semantic_search_total
researchmind_memory_research_search_total
researchmind_memory_parallel_search_total

researchmind_memory_extraction_evaluated_total
researchmind_memory_extraction_skipped_total
researchmind_memory_extraction_requested_total
researchmind_memory_extraction_succeeded_total
researchmind_memory_extraction_failed_total
researchmind_memory_extraction_empty_total

researchmind_memory_created_total
researchmind_memory_updated_total
researchmind_memory_duplicates_total
```

Histograms:

```text
researchmind_memory_context_duration_seconds
researchmind_memory_embedding_duration_seconds
researchmind_memory_durable_search_duration_seconds
researchmind_memory_extraction_duration_seconds
```

Labels:

```text
runtime
status
policy_action
memory_type
```

Do not use:

- owner IDs;
- topic text;
- session IDs;
- extracted content.

---

# 21. Web Search Metrics

Counters:

```text
researchmind_web_search_requests_total
researchmind_web_search_failures_total
researchmind_web_search_results_total
researchmind_web_search_selected_results_total
researchmind_web_search_cost_usd_total

researchmind_web_fetch_requests_total
researchmind_web_fetch_failures_total
researchmind_web_fetch_blocked_total
researchmind_web_fetch_bytes_total

researchmind_web_evidence_created_total
researchmind_web_evidence_rejected_total
researchmind_web_prompt_injection_detected_total
```

Histograms:

```text
researchmind_web_search_duration_seconds
researchmind_web_fetch_duration_seconds
```

Labels:

```text
provider
status
source_mode
policy_outcome
failure_type
```

Do not use full domains or URLs as labels in the first implementation.

If domain analysis is later required, use a separately bounded, allow-listed source category.

---

# 22. MCP Tool Metrics

Client-side ResearchMind MCP metrics:

```text
researchmind_mcp_tool_requests_total
researchmind_mcp_tool_failures_total
researchmind_mcp_tool_results_total
researchmind_mcp_tool_duration_seconds

researchmind_mcp_server_requests_total
researchmind_mcp_server_failures_total
researchmind_mcp_server_duration_seconds
researchmind_mcp_server_health
```

Labels:

```text
server
tool
status
error_type
transport
```

Rules:

- server and tool names must come from registered bounded values;
- arbitrary remote names must be normalized to `unknown`;
- tool arguments must never become labels;
- MCP response content must never become labels.

`researchmind_mcp_server_health` values:

```text
1 = healthy
0 = unhealthy
```

---

# 23. Guardrail Metrics

Metrics:

```text
researchmind_guardrail_checks_total
researchmind_guardrail_blocks_total
researchmind_guardrail_failures_total
researchmind_prompt_injection_attempts_total
researchmind_pii_detections_total
researchmind_policy_violations_total
```

Labels:

```text
stage
category
action
```

Allowed stages:

```text
input
retrieval
generation
runtime
```

Allowed actions:

```text
allow
warn
block
regenerate
```

---

# 24. Research Runtime Metrics

Add a small runtime-level metric set.

Counters:

```text
researchmind_research_runs_total
researchmind_research_runs_completed_total
researchmind_research_runs_failed_total
researchmind_research_runs_cancelled_total
researchmind_research_tool_calls_total
researchmind_research_repair_rounds_total
```

Gauges:

```text
researchmind_research_active_runs
```

Histograms:

```text
researchmind_research_duration_seconds
researchmind_research_evidence_count
researchmind_research_tool_calls_per_run
```

Labels:

```text
status
source_mode
```

Do not use `research_id` as a label.

If the current Research API is still linear, record only metrics that reflect current real behavior. Do not create fake planner, wave, or reviewer metrics until those nodes exist.

---

# 25. Prometheus Configuration

Create:

```text
infra/observability/prometheus/prometheus.yml
```

Suggested content:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - /etc/prometheus/alerts.yml

scrape_configs:
  - job_name: researchmind-api
    metrics_path: /metrics
    static_configs:
      - targets:
          - api:8000
```

Create:

```text
infra/observability/prometheus/alerts.yml
```

Prometheus must persist data through a named Docker volume.

Use a fixed Prometheus image version.

---

# 26. Grafana Provisioning

## Data source

Create:

```text
infra/observability/grafana/provisioning/datasources/prometheus.yml
```

Example:

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

## Dashboard provisioning

Create:

```text
infra/observability/grafana/provisioning/dashboards/dashboards.yml
```

Example:

```yaml
apiVersion: 1

providers:
  - name: ResearchMind
    orgId: 1
    folder: ResearchMind
    type: file
    disableDeletion: true
    editable: true
    options:
      path: /var/lib/grafana/dashboards
```

Use source-controlled dashboard JSON files.

---

# 27. Docker Compose

Add services to the existing Docker Compose file.

Use fixed versions rather than `latest`.

Target:

```yaml
prometheus:
  image: prom/prometheus:<fixed-version>
  command:
    - "--config.file=/etc/prometheus/prometheus.yml"
    - "--storage.tsdb.path=/prometheus"
    - "--storage.tsdb.retention.time=${PROMETHEUS_RETENTION_TIME:-15d}"
  volumes:
    - ./infra/observability/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    - ./infra/observability/prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro
    - prometheus_data:/prometheus
  ports:
    - "${PROMETHEUS_PORT:-9090}:9090"
  depends_on:
    api:
      condition: service_healthy

grafana:
  image: grafana/grafana:<fixed-version>
  environment:
    GF_SECURITY_ADMIN_USER: ${GRAFANA_ADMIN_USER:-admin}
    GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:-admin}
    GF_USERS_ALLOW_SIGN_UP: "false"
  volumes:
    - grafana_data:/var/lib/grafana
    - ./infra/observability/grafana/provisioning:/etc/grafana/provisioning:ro
    - ./infra/observability/grafana/dashboards:/var/lib/grafana/dashboards:ro
  ports:
    - "${GRAFANA_PORT:-3001}:3000"
  depends_on:
    - prometheus
```

Add:

```yaml
volumes:
  prometheus_data:
  grafana_data:
```

Do not expose Prometheus publicly in production without network controls.

For local development, port `9090` is acceptable.

---

# 28. Dashboard 1 — ResearchMind Overview

File:

```text
researchmind-overview.json
```

Panels:

1. API requests per minute
2. HTTP error rate
3. HTTP P50 latency
4. HTTP P95 latency
5. HTTP P99 latency
6. in-flight requests
7. generation requests per minute
8. research runs
9. Chat generation requests
10. estimated generation cost over selected range
11. cache hit ratio
12. web-search failure rate
13. MCP tool failure rate
14. guardrail block count
15. memory-extraction request ratio

Suggested PromQL:

```promql
sum(rate(researchmind_http_requests_total[5m]))
```

```promql
sum(rate(researchmind_http_requests_total{status_code=~"5.."}[5m]))
/
clamp_min(sum(rate(researchmind_http_requests_total[5m])), 1)
```

```promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(researchmind_http_request_duration_seconds_bucket[5m])
  )
)
```

```promql
sum(increase(researchmind_generation_cost_usd_total[$__range]))
```

---

# 29. Dashboard 2 — Generation Runtime

File:

```text
generation-runtime.json
```

Panels:

1. generation requests by provider
2. generation success rate
3. generation failure rate
4. provider P95 latency
5. input-token rate
6. output-token rate
7. cost by runtime
8. fallback rate
9. regeneration rate
10. validation failure count
11. generation guardrail blocks
12. cache hit ratio by cache level
13. tokens saved by cache
14. cost saved by cache

Examples:

```promql
sum by (provider) (
  rate(researchmind_generation_requests_total[5m])
)
```

```promql
sum by (provider) (
  rate(researchmind_generation_failures_total[10m])
)
/
clamp_min(
  sum by (provider) (
    rate(researchmind_generation_requests_total[10m])
  ),
  1
)
```

---

# 30. Dashboard 3 — Research Tools

File:

```text
research-tools.json
```

Panels:

1. web searches over time
2. web-search success/failure rate
3. web-search P95 latency
4. results returned per search
5. selected-result ratio
6. web-fetch request rate
7. blocked fetches
8. web-fetch P95 latency
9. web evidence accepted/rejected
10. prompt injection detections
11. MCP tool requests by tool
12. MCP tool failure rate
13. MCP tool P95 latency
14. MCP server health
15. research tool calls per run
16. research repair rounds

---

# 31. Dashboard 4 — Memory Runtime

File:

```text
memory-runtime.json
```

Panels:

1. memory-context request rate
2. durable retrieval skip rate
3. durable-memory available vs empty
4. embedding cache hit rate
5. semantic/research search rate
6. memory-context P95 latency
7. durable-search P95 latency
8. extraction evaluated vs skipped
9. extraction request ratio
10. extraction success/failure rate
11. empty extraction rate
12. memories created vs updated
13. duplicate-memory rate
14. extraction P95 latency
15. extraction cost, if available through the existing usage ledger adapter

---

# 32. Initial Alerts

Keep alerts limited and actionable.

## 32.1 API error rate

```yaml
- alert: ResearchMindHighApiErrorRate
  expr: |
    sum(rate(researchmind_http_requests_total{status_code=~"5.."}[5m]))
    /
    clamp_min(sum(rate(researchmind_http_requests_total[5m])), 1)
    > 0.05
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: ResearchMind API error rate is above 5%
```

## 32.2 Generation failure rate

```yaml
- alert: ResearchMindHighGenerationFailureRate
  expr: |
    sum(rate(researchmind_generation_failures_total[10m]))
    /
    clamp_min(sum(rate(researchmind_generation_requests_total[10m])), 1)
    > 0.10
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: Generation failure rate is above 10%
```

## 32.3 Web-search failure rate

```yaml
- alert: ResearchMindHighWebSearchFailureRate
  expr: |
    sum(rate(researchmind_web_search_failures_total[10m]))
    /
    clamp_min(sum(rate(researchmind_web_search_requests_total[10m])), 1)
    > 0.20
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: Web search failure rate is above 20%
```

## 32.4 MCP tool failure rate

```yaml
- alert: ResearchMindHighMcpFailureRate
  expr: |
    sum(rate(researchmind_mcp_tool_failures_total[10m]))
    /
    clamp_min(sum(rate(researchmind_mcp_tool_requests_total[10m])), 1)
    > 0.15
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: MCP tool failure rate is above 15%
```

## 32.5 Memory extraction growth

```yaml
- alert: ResearchMindUnexpectedMemoryExtractionRate
  expr: |
    sum(rate(researchmind_memory_extraction_requested_total[30m]))
    /
    clamp_min(
      sum(rate(researchmind_memory_extraction_evaluated_total[30m])),
      1
    )
    > 0.70
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: Memory extraction runs for more than 70% of evaluated turns
```

These thresholds are initial development defaults.

They are not production SLOs.

---

# 33. Multiprocess Deployment

The first implementation should assume:

```text
one API container
one Uvicorn worker
```

This avoids Prometheus multiprocess complexity.

Before increasing Python worker count, implement and verify:

```text
PROMETHEUS_MULTIPROC_DIR
multiprocess.MultiProcessCollector
worker-exit cleanup
shared collector registry
```

Add a code comment and architecture note explaining that multiple Uvicorn/Gunicorn workers require explicit Prometheus multiprocess support.

Do not silently enable multiple workers with single-process metrics.

---

# 34. Security

## Metrics endpoint

Production requirements:

- keep `/metrics` on the private application network;
- do not expose it through the public load balancer;
- do not include secrets;
- do not include user-level identifiers;
- do not include query or prompt contents.

## Grafana

Local defaults may use:

```text
admin / admin
```

Production must:

- set a strong password;
- disable sign-up;
- restrict network access;
- use HTTPS through the deployment proxy;
- avoid anonymous access unless explicitly approved.

## Prometheus

Production must:

- restrict network access;
- persist storage to an approved volume;
- set retention deliberately;
- avoid public exposure.

---

# 35. Failure Handling

Metrics operations must fail open.

Example:

```python
try:
    recorder.increment(...)
except Exception:
    logger.warning("prometheus.metric_record_failed", ...)
```

Do not wrap every individual service call manually if the recorder can handle its own failure boundary.

Prometheus being down must not affect:

- Chat
- Research
- Generation
- Memory
- Web Search
- MCP
- Guardrails
- Caching

Grafana being down must not affect Prometheus or the application.

---

# 36. Testing

## 36.1 Unit tests

Test:

- metric registration;
- duplicate registration safety;
- counter increments;
- histogram observations;
- gauge updates;
- label validation;
- forbidden-label rejection;
- unknown metric behavior;
- recorder failure handling;
- NoOp recorder behavior;
- route normalization;
- model-family normalization.

## 36.2 Endpoint tests

Verify:

```text
GET /metrics
```

returns:

- HTTP 200;
- Prometheus content type;
- known application metric names;
- no user identifiers;
- no prompt content.

## 36.3 Integration tests

Required scenarios:

1. health or test request increments HTTP counter;
2. completed generation increments generation counter;
3. failed generation increments generation failure counter;
4. cache hit increments cache-hit counter;
5. memory extraction skip increments skip counter;
6. web-search success increments search counter;
7. MCP tool failure increments failure counter;
8. guardrail block increments block counter;
9. metrics recorder failure does not fail application request.

## 36.4 Docker verification

Verify:

```text
Prometheus target = UP
Grafana data source = healthy
Dashboards load automatically
Metrics appear without manual configuration
Alerts file loads successfully
```

---

# 37. Acceptance Criteria

The milestone is complete when:

- [ ] `prometheus-client` is installed.
- [ ] `/metrics` is available when enabled.
- [ ] `/metrics` is absent or disabled when configured off.
- [ ] HTTP metrics are recorded.
- [ ] Generation metrics are recorded.
- [ ] Cache metrics are recorded.
- [ ] Memory metrics are recorded.
- [ ] Web-search metrics are recorded.
- [ ] MCP metrics are recorded.
- [ ] Guardrail metrics are recorded.
- [ ] Metric labels follow the cardinality policy.
- [ ] No user or request identifiers appear as labels.
- [ ] Prometheus runs through Docker Compose.
- [ ] Prometheus successfully scrapes the API.
- [ ] Grafana runs through Docker Compose.
- [ ] Grafana’s Prometheus data source is provisioned automatically.
- [ ] Four dashboards are provisioned automatically.
- [ ] Initial alert rules load successfully.
- [ ] Metrics failures do not affect user requests.
- [ ] Unit tests pass.
- [ ] integration tests pass.
- [ ] Ruff passes.
- [ ] mypy passes.
- [ ] Docker Compose config validates.
- [ ] documentation contains setup, run, and verification commands.

---

# 38. Implementation Milestones

## Milestone 1 — Prometheus Foundation

Build:

- dependency
- settings
- registry
- recorder
- NoOp recorder
- metrics endpoint
- unit tests

Exit condition:

```text
GET /metrics
```

returns a valid Prometheus payload.

## Milestone 2 — HTTP and Generation Metrics

Build:

- HTTP middleware
- normalized route labels
- generation recorder integration
- cache metrics
- tests

Exit condition:

A Chat or Research generation updates HTTP, generation, token, cost, and cache metrics.

## Milestone 3 — Platform Metrics

Wire:

- Memory
- Web Search
- MCP
- Guardrails
- Research runtime

Exit condition:

Each platform exposes at least its request, failure, and duration metrics.

## Milestone 4 — Prometheus Service

Build:

- `prometheus.yml`
- `alerts.yml`
- Docker Compose service
- persistent volume
- target verification

Exit condition:

Prometheus shows:

```text
researchmind-api = UP
```

## Milestone 5 — Grafana Service and Dashboards

Build:

- Grafana service
- provisioned data source
- provisioned dashboard provider
- four dashboard JSON files
- persistent volume

Exit condition:

Opening Grafana immediately shows the ResearchMind dashboards without manual setup.

## Milestone 6 — Alerts and Hardening

Build:

- five initial alerts
- security notes
- multiprocess warning
- runbook
- failure-mode verification

Exit condition:

Alert rules load and the implementation is documented for local and production deployment.

---

# 39. Claude Code Execution Rules

Claude Code must follow these rules.

1. Inspect the repository before creating files.
2. Reuse current metrics interfaces where they already exist.
3. Do not create duplicate observability platforms.
4. Do not add direct `prometheus_client` imports throughout business services.
5. Add one Prometheus adapter behind platform-owned recorder interfaces.
6. Preserve existing structured logs.
7. Preserve LangSmith tracing.
8. Preserve the generation usage ledger.
9. Do not expose sensitive values.
10. Do not add IDs as metric labels.
11. Use fixed Docker image versions.
12. Keep the API on one worker for this milestone.
13. Add complete tests.
14. Run format, lint, type-check, and test commands.
15. Return complete files, not partial snippets.
16. Update documentation and `.env.example`.
17. Do not add Loki, Tempo, or OpenTelemetry in this milestone.
18. Do not build dashboards manually without committing their JSON.
19. Do not fabricate metrics for runtime features that do not exist yet.
20. Keep all metrics recording best effort.

---

# 40. Required Developer Commands

Claude Code must adapt these commands to the repository’s actual tooling.

Suggested commands:

```bash
uv add prometheus-client
```

```bash
uv run ruff format apps/api/app tests
```

```bash
uv run ruff check apps/api/app tests
```

```bash
uv run mypy apps/api/app
```

```bash
uv run pytest tests/unit/ai/observability -q
```

```bash
uv run pytest tests/integration/ai/test_prometheus_metrics.py -q
```

```bash
docker compose config
```

```bash
docker compose up -d api prometheus grafana
```

```bash
curl http://localhost:8000/metrics
```

```bash
curl http://localhost:9090/-/healthy
```

Local URLs:

```text
ResearchMind API: http://localhost:8000
Prometheus:       http://localhost:9090
Grafana:          http://localhost:3001
```

---

# 41. Verification Checklist

## Application

```text
GET /metrics → 200
```

Confirm the response includes:

```text
researchmind_http_requests_total
researchmind_generation_requests_total
```

## Prometheus

Open:

```text
Status → Targets
```

Confirm:

```text
researchmind-api = UP
```

Run:

```promql
researchmind_http_requests_total
```

## Grafana

Confirm:

- Prometheus data source is healthy;
- ResearchMind folder exists;
- four dashboards exist;
- panels populate after test requests.

## Runtime verification

Perform:

1. one Chat request;
2. one Research request;
3. one web-search-enabled Research request;
4. one MCP tool call;
5. one memory-eligible turn;
6. one memory-skipped turn.

Confirm relevant metrics increase.

---

# 42. Rollout Strategy

## Phase A — Local

Enable all metrics locally.

Validate:

- labels;
- dashboards;
- counters;
- histograms;
- no sensitive data;
- no duplicate registration.

## Phase B — Staging

Deploy with private `/metrics`.

Observe:

- scrape reliability;
- metric cardinality;
- dashboard behavior;
- latency overhead;
- memory footprint;
- alert noise.

## Phase C — Production

Enable:

- private Prometheus scrape;
- authenticated/restricted Grafana;
- deliberate retention;
- initial alerts.

Keep:

```text
PROMETHEUS_ENABLED
```

as a rollback flag.

---

# 43. Future Enhancements

Only after the current milestone is stable:

- OpenTelemetry traces
- Grafana Tempo
- Grafana Loki
- host metrics
- cAdvisor
- PostgreSQL exporter
- Redis/Valkey exporter
- Qdrant metrics scraping
- S3/cloud metrics
- alert routing to email or Telegram
- deployment annotations
- environment comparison dashboards
- SLO dashboards
- recording rules
- long-term remote metric storage
- Grafana Cloud
- trace-log-metric correlation
- async worker and queue metrics
- LangGraph node-level metrics after the Research Runtime exists

---

# 44. Final Architecture Decision

ResearchMind will use:

```text
LangSmith
    → detailed AI execution traces

Structlog
    → request and platform event logs

PostgreSQL usage ledger
    → owner-scoped cost accounting

Prometheus
    → aggregate time-series metrics

Grafana
    → dashboards and alerts
```

The initial implementation is intentionally limited to operational metrics.

It does not introduce a full distributed-observability stack.

The goal is:

> Make ResearchMind measurable and operable without overengineering the platform.
