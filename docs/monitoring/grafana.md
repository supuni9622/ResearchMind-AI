# Grafana

**Status:** Implemented (2026-07-26).
**Full runbook:** `docs/runbooks/prometheus-grafana-observability.md` (setup, troubleshooting, PromQL examples, rollback).

---

## Access

| | |
|---|---|
| URL | http://localhost:3001 |
| Credentials (local) | `admin` / `admin` (`GRAFANA_ADMIN_USER`/`GRAFANA_ADMIN_PASSWORD`) |
| Datasource | Prometheus, auto-provisioned (`infra/observability/grafana/provisioning/datasources/prometheus.yml`) |
| Start | `docker compose up -d prometheus grafana` |

Dashboards, datasource, and alert rules are all provisioned from files under `infra/observability/` — not clicked together by hand.

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
- Memories created vs. updated / duplicate-memory rate / extraction P95 latency

## What Grafana is not for

No request/user/session/research IDs ever appear as metric labels (by design — see `names.py`). For "why did *this* request fail," use structured logs or a LangSmith trace instead (`docs/guides/debugging.md`).
