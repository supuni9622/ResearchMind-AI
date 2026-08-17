# Prometheus

**Status:** Implemented (2026-07-26).
**Full runbook:** `docs/runbooks/prometheus-grafana-observability.md`.

---

## Access

| | |
|---|---|
| Prometheus UI | http://localhost:9090 |
| Raw API exposition | http://localhost:8000/metrics |
| Research worker exposition | http://localhost:8010/metrics |
| Memory worker exposition | http://localhost:8011/metrics |
| Start | `docker compose up -d prometheus grafana` |
| Kill switch | `PROMETHEUS_ENABLED=false` — every metrics call site, the `/metrics` endpoint, and the HTTP metrics middleware all no-op |

## Scrape config — `infra/observability/prometheus/prometheus.yml`

- `scrape_interval` / `evaluation_interval`: 15s
- Targets: `host.docker.internal:8000` (API), `:8010` (Research Runtime
  worker), and `:8011` (memory lifecycle/inventory worker). These processes run
  on the host, so Prometheus reaches them through Docker Desktop's host gateway.

## Metric registry — `app/ai/observability/prometheus/names.py`

Single, bounded registry: every metric name/type/label schema `PrometheusMetricsRecorder` may emit is declared here. A call site passing an unregistered metric key is a silent no-op — prevents unbounded-cardinality series from being created at arbitrary call sites. Covers Generation, Cache, Guardrails, Memory, HTTP, Web Search, and MCP metrics.

Never appears as a metric value or label: prompts, queries, full URLs, `request_id`, `owner_id`/`user_id`, `session_id`/`research_id`, `document_id`/`citation_id`/`artifact_id`, raw exception messages, API keys.

## Alert rules — `infra/observability/prometheus/alerts.yml`

| Alert | Condition | Window |
|---|---|---|
| `ResearchMindHighApiErrorRate` | 5xx rate > 5% | 10m |
| `ResearchMindHighGenerationFailureRate` | Generation failure rate > 10% | 10m |
| `ResearchMindHighWebSearchFailureRate` | Web-search failure rate > 20% | 15m |
| `ResearchMindHighMcpFailureRate` | MCP tool failure rate > 15% | 15m |
| `ResearchMindUnexpectedMemoryExtractionRate` | Extraction-requested/evaluated ratio > 70% | 30m |
| `ResearchMindMemoryLifecycleStale` | Last successful lifecycle cycle is older than 30h or absent | 15m |
| `ResearchMindMemoryLifecycleFailures` | Any lifecycle row failure in the last hour | 5m |
| `ResearchMindMemoryVectorDrift` | PostgreSQL/Qdrant missing or orphan count is non-zero | 15m |
| `ResearchMindMemoryInventoryStale` | Last successful inventory is older than 30h or absent | 15m |
| `ResearchMindChatLatencyHigh` | Chat generation P95 > 15s | 10m |
| `ResearchMindLinearResearchLatencyHigh` | Linear Research turn P95 > 45s | 10m |
| `ResearchMindDeepResearchRunAbnormallySlow` | Deep Research end-to-end P95 > 2h | 30m |

These are local-development defaults, not tuned production SLOs. No notification channel (PagerDuty/Slack) is wired up — alerts are visible in the Prometheus UI only.

## Example queries

```promql
# Which provider is failing right now?
sum by (provider, failure_type) (rate(researchmind_generation_failures_total[10m]))

# Cache effectiveness by level, last hour
sum by (cache_level) (increase(researchmind_cache_hits_total[1h]))
/ clamp_min(sum by (cache_level) (increase(researchmind_cache_operations_total[1h])), 1)
```
