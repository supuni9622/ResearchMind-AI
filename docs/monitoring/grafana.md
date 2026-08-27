# Grafana

**Status:** Implemented (2026-07-26).
**Full runbook:** `docs/runbooks/prometheus-grafana-observability.md` (setup, troubleshooting, PromQL examples, rollback).

---

## Access

| | |
|---|---|
| URL | http://localhost:3001 |
| Credentials (local) | `admin` / `admin` (`GRAFANA_ADMIN_USER`/`GRAFANA_ADMIN_PASSWORD`) |
| Datasources | Prometheus (`.../datasources/prometheus.yml`) + Postgres (`.../datasources/postgres.yml`, for the Eval Scores dashboard below), both auto-provisioned |
| Start | `docker compose up -d postgres prometheus grafana` |

Dashboards, datasources, and alert rules are all provisioned from files under `infra/observability/` — not clicked together by hand.

## Dashboards (`infra/observability/grafana/dashboards/*.json`)

### ResearchMind Overview — "is anything on fire"

- API requests per minute / HTTP error rate / P50, P95, P99 latency / in-flight requests
- Generation requests per minute / research runs / chat generation requests
- Estimated generation cost (selected range) / cache hit ratio
- Web-search failure rate / MCP tool failure rate / guardrail block count / memory-extraction request ratio

### Generation Runtime

- Requests & success/failure rate by provider / provider P95 latency
- Input & output token rate / cost by runtime
- Retry (fallback) rate / regeneration rate / validation failure count / guardrail blocks
- Cache hit ratio, tokens saved, cost saved — by cache level

### Research Tools

- Web searches over time / success-failure rate / P95 latency / results returned per search / selected-result ratio / failures by type
- MCP tool requests by tool / failure rate / P95 latency / server health
- Research runs by outcome / P95 duration
- Deep Research review decisions (`ResearchReview.decision` — pass/finalize_with_limitations/research_gaps/revise_synthesis/fail — one series per decision, per review cycle)

### Memory Runtime

- Memory-context request rate / durable-retrieval skip rate / durable memory available vs. empty
- Semantic/research search rate / context & durable-search P95 latency
- Extraction evaluated vs. skipped / request ratio / success-failure rate / empty extraction rate
- Memories created, updated, and superseded / duplicate-memory rate / extraction P95 latency
- Absolute PostgreSQL rows by type/scope and table/index/total bytes
- Qdrant point count, missing/orphan drift, oldest-row age, and bounded owner/project p50/p95/max distributions
- Lifecycle and inventory freshness / examined, deleted, and failed outcomes
- Selected/dropped context tokens, omitted items, mutation throttles, consolidation outcomes, and utility/feedback trends

Storage inventory and lifecycle series are emitted by the separately running
`apps.worker.memory_lifecycle_main` process on port `8011`. Prometheus labels
contain only bounded aggregate dimensions; owner and project IDs are never labels.

### Eval Scores (E17)

The one dashboard querying Postgres directly instead of PromQL — `eval_scores` (E5/E6/E9) has no Prometheus representation.

- Online avg score by metric, 1h buckets (`source = online_sampled`)
- Online pass rate by metric, 1h buckets
- Offline (golden-set) avg score by metric — one point per roughly-one-benchmark-run, not continuous traffic
- Score-row volume by source (`online_sampled`/`offline_benchmark`/`human_feedback`), 1d buckets — a coverage check, not a quality metric

## What Grafana is not for

No request/user/session/research IDs ever appear as metric labels (by design — see `names.py`). For "why did *this* request fail," use structured logs or a LangSmith trace instead (`docs/guides/debugging.md`).
