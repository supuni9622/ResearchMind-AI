# Prometheus & Grafana Observability

> How to run the Prometheus/Grafana stack locally and how to read it once
> it's running.

## Status

✅ Implemented (2026-07-26) — `prds/prometheus_grafana_observability_prd.md`.

This is the operational counterpart to
[`infra/observability/README.md`](../../infra/observability/README.md),
which stays terse (commands only). This document explains *why* those
commands exist and how to actually use the result day to day.

---

## What this platform is (and isn't)

Prometheus/Grafana add one thing ResearchMind didn't have before:
**aggregate, time-series visibility** — request rates, error rates,
latency percentiles, cost trends, cache hit ratios, tool failure rates.

It does **not** replace anything already in place:

| Question | Where to look |
|---|---|
| "Why did *this* request fail?" | Structured logs (`structlog`), correlated by `request_id` |
| "What did the model actually see/say on *this* generation?" | LangSmith trace |
| "What did *this* research run cost?" | PostgreSQL usage ledger (`/usage`) |
| "Is error rate trending up across the fleet?" | **Grafana** |
| "Is generation P95 latency getting worse this week?" | **Grafana** |
| "Are we about to blow through a cost/error/failure threshold?" | **Prometheus alerts** |

If you're debugging one specific request, start with logs/LangSmith, not
Grafana — Prometheus deliberately carries no request/user/session/research
IDs (see "What never becomes a metric" below), so it can't answer
per-request questions by design.

---

## Setup

### Prerequisites

- The API running locally (`uvicorn`, as usual — it is **not** a Docker
  Compose service; see "Why `host.docker.internal`" below).
- Docker Desktop (for Prometheus + Grafana themselves).

### Steps

1. Copy the Prometheus/Grafana block from `.env.example` into your `.env`
   (the defaults work as-is for local dev — `PROMETHEUS_ENABLED=true` is
   already the default even without this block).
2. Start the API as usual.
3. Start Prometheus + Grafana:

   ```bash
   docker compose up -d prometheus grafana
   ```

4. Open:

   - Grafana — <http://localhost:3001> (`admin` / `admin` locally)
   - Prometheus — <http://localhost:9090>
   - Raw API exposition — <http://localhost:8000/metrics>
   - Raw `research_runtime_main` worker exposition — <http://localhost:8010/metrics>
     (`Settings.research_runtime_worker_metrics_port` -- only runs when
     that worker process is up, unlike the API's)
   - Raw `memory_lifecycle_main` worker exposition — <http://localhost:8011/metrics>
     (inventory and lifecycle gauges exist only while this worker is running)

That's it — dashboards, both datasources (Prometheus + Postgres, the
latter for the Eval Scores dashboard below), and alert rules are all
provisioned from files under `infra/observability/`, not clicked together
by hand. If Grafana's `ResearchMind` folder is empty, something is wrong
with the volume mounts, not with "someone forgot to import a dashboard."
The Postgres datasource needs the `postgres` service running too (`docker
compose up -d postgres prometheus grafana` if you haven't already started
it as part of the normal dev stack).

### Why `host.docker.internal`

This repo's `docker-compose.yml` never containerized the API — it runs
via `uvicorn` on the host. Prometheus *does* run in Compose, so
`infra/observability/prometheus/prometheus.yml` scrapes
`host.docker.internal:8000` (Docker Desktop's host gateway) instead of a
Compose service name. If the API is ever containerized as an `api`
service, switch that target to `api:8000` and add a
`depends_on: api: condition: service_healthy` to the `prometheus` service.

---

## Observing the platform

### Dashboards

All five live under the **ResearchMind** folder in Grafana.

**1. ResearchMind Overview** — start here. Request rate, HTTP error
rate, P50/P95/P99 latency, in-flight requests, generation volume,
research runs, estimated generation cost, cache hit ratio, web-search and
MCP failure rates, guardrail blocks, memory-extraction ratio. This is the
"is anything on fire" dashboard.

**2. Generation Runtime** — the Generation platform in detail: requests
and failures by provider, P95 latency by provider, token rates, cost by
runtime, fallback/retry rate, regeneration rate, validation/guardrail
counters, and cache effectiveness (hit ratio, tokens/cost saved) by
cache level.

**3. Research Tools** — Web Search and MCP paper search: request rates,
success/failure, P95 latency, result counts, selected-result ratio, MCP
server health, research-run outcomes/duration, and Deep Research review
decisions (`ResearchReview.decision`, one series per pass/
finalize_with_limitations/research_gaps/revise_synthesis/fail, per review
cycle). Useful when a research run feels slow, a research answer is thin
on evidence, or reports are routinely finalizing with limitations rather
than passing cleanly.

**4. Memory Runtime** — Memory platform internals: context-build and search,
created/updated/superseded writes, absolute PostgreSQL rows and bytes, Qdrant
points and drift, oldest-row age, bounded owner/project distributions,
lifecycle freshness/outcomes, context tokens and omissions, mutation
throttles, consolidation outcomes, and memory utility/feedback trends. The
scheduled inventory comes from `memory_lifecycle_main`; no owner or project ID
is exported as a metric label. Useful for "is memory extraction running too
often," "is cleanup healthy," or "why is
memory context empty for this user type" questions (in aggregate — not
per-user, see below).

**5. Eval Scores** (E17, EVALUATION_IMPLEMENTATION_TRACKER.md) — the one
dashboard that isn't Prometheus-backed: `eval_scores` (E5/E6/E9) lives in
Postgres, so this queries the dev database directly through a native
Grafana Postgres datasource (`researchmind-postgres`, provisioned
alongside the Prometheus one) rather than PromQL. Online avg
score/pass-rate by metric, offline (golden-set) avg score by metric per
run, and score-row volume by source (`online_sampled`/
`offline_benchmark`/`human_feedback`) — the quality-trend picture
Grafana's other four dashboards (all operational: latency/cost/error
rate) don't cover. Uses the same hardcoded dev credentials already
checked into `docker-compose.yml`'s `postgres` service — a dedicated
read-only reporting user is real future hardening before any production
deployment, not built here.

Every panel on dashboards 1-4 is backed by a PromQL query you can copy
into Prometheus's own "Graph" tab (<http://localhost:9090/graph>) to
inspect raw series or tweak ad hoc; dashboard 5's panels are raw SQL
against `eval_scores`, editable the same way directly in Grafana's panel
editor — neither hides anything.

### Alerts

Defined in `infra/observability/prometheus/alerts.yml`, visible under
Prometheus → Alerts:

| Alert | Fires when | Likely cause to check first |
|---|---|---|
| `ResearchMindHighApiErrorRate` | 5xx rate > 5% for 10m | A dependency (DB/Valkey/Qdrant) is down, or a recent deploy introduced a bug |
| `ResearchMindHighGenerationFailureRate` | Generation failure rate > 10% for 10m | A provider outage/rate-limit, or a bad routing/model config change |
| `ResearchMindHighWebSearchFailureRate` | Web-search failure rate > 20% for 15m | Tavily outage/rate-limit, or an expired/invalid API key |
| `ResearchMindHighMcpFailureRate` | MCP tool failure rate > 15% for 15m | The Research Intelligence MCP server is down or unreachable |
| `ResearchMindUnexpectedMemoryExtractionRate` | Extraction requested/evaluated ratio > 70% for 30m | The extraction policy/threshold changed (intentionally or not) and is now firing on most turns |
| `ResearchMindMemoryLifecycleStale` | No successful lifecycle cycle for 30h | The lifecycle worker is stopped, its lock/dependencies are unhealthy, or the cycle is failing |
| `ResearchMindMemoryLifecycleFailures` | Any row-level lifecycle failure in 1h | A canonical delete, vector cleanup, or per-row dependency failed |
| `ResearchMindMemoryVectorDrift` | Any canonical/vector ID mismatch for 15m | Qdrant indexing/deletion failed or an out-of-band change created an orphan |
| `ResearchMindMemoryInventoryStale` | No successful inventory collection for 30h | The lifecycle worker is stopped or aggregate PostgreSQL/Qdrant collection failed |
| `ResearchMindChatLatencyHigh` | Chat P95 generation latency > 15s for 10m | A provider is degraded/slow, or a routing change picked a slower model |
| `ResearchMindLinearResearchLatencyHigh` | Linear Research P95 turn latency > 45s for 10m | Retrieval/reranking or the generation provider is degraded |
| `ResearchMindDeepResearchRunAbnormallySlow` | Deep Research P95 end-to-end run duration > 2h (1h window, 30m for) | A genuinely different *kind* of alert from the two above, not just a bigger number: `researchmind_deep_research_run_duration_seconds` measures `completed_at - started_at`, which legitimately includes human-approval wait time at the plan/report/web-search checkpoints — this is a stuck-run/anomaly detector, not a performance SLO, since it can't distinguish "slow reviewer" from "actually orphaned" |

These thresholds are **local-development defaults**, not tuned production
SLOs (PRD §32) — expect to revisit them once there's real traffic to
calibrate against. Alerts have no notification channel wired up yet
(no PagerDuty/Opsgenie/Slack) — this milestone stops at "visible in the
Prometheus UI," per the PRD's explicit non-goals.

Deep Research's `researchmind_deep_research_run_duration_seconds` is a
separate metric from `researchmind_research_duration_seconds` above
(Chat/Linear Research's single-turn latency) — one Prometheus histogram
has one fixed bucket set shared across every label value, and Deep
Research's wall-clock duration is a fundamentally different scale
(minutes-to-hours) than Chat/Linear's seconds-scale buckets, so it needed
its own metric name and bucket set (`DEEP_RESEARCH_RUN_BUCKETS`,
`app/ai/observability/prometheus/names.py`) rather than reusing theirs.
Recorded at every terminal-transition path
(`ResearchRuntimeExecutionService._record_run_duration()`, called from
`_complete_run`/`_mark_terminal`/`_mark_failed`).

**A second, deeper gap, found only by watching a real Deep Research run
complete end-to-end (2026-08-12), same day:** the metric above is
recorded from inside `apps/worker/research_runtime_main.py`, which runs
as its own OS process with its own private Prometheus registry
(`get_prometheus_metric_registry()` is `@lru_cache`d *per process*) --
`prometheus.yml` only ever scraped the API's own `:8000/metrics`, so
every metric this worker records (Deep Research run duration, and also
planner/synthesis generation duration for that surface) was invisible to
Prometheus regardless of how correctly it was recorded. Fixed with a new
`start_worker_metrics_server()` (exposes the worker's own registry via
`prometheus_client.start_http_server()`, its standard mechanism for a
non-web-framework process) bound to `Settings.
research_runtime_worker_metrics_port` (default `8010`) and a second
scrape target, `researchmind-research-runtime-worker`, in
`prometheus.yml`. Verified live: `/api/v1/targets` reports both scrape
jobs `health: up`.

### Useful ad-hoc queries

Paste these into Prometheus's Graph tab (or a new Grafana panel):

```promql
# Which provider is failing right now?
sum by (provider, failure_type) (rate(researchmind_generation_failures_total[10m]))

# Is a specific route slow?
histogram_quantile(0.95, sum by (le, route) (rate(researchmind_http_request_duration_seconds_bucket[5m])))

# Cache effectiveness by level, last hour
sum by (cache_level) (increase(researchmind_cache_hits_total[1h]))
/ clamp_min(sum by (cache_level) (increase(researchmind_cache_operations_total[1h])), 1)

# Cost burn rate, last 24h
sum(increase(researchmind_generation_cost_usd_total[24h]))
```

### What never becomes a metric

By design, none of the following ever appear as a metric value or a
label: prompts, user queries, full URLs, `request_id`, `owner_id`/
`user_id`, `session_id`/`conversation_id`, `research_id`, `document_id`/
`citation_id`/`artifact_id`, raw exception messages, API keys/tokens.
Route labels are path *templates* (`/api/v1/research/{research_id}`),
never the raw path with a real ID in it. If you ever see one of these in
`/metrics` output, that's a bug — file it against
`apps/api/app/ai/observability/prometheus/names.py`, the single place
every metric's label schema is declared (see
`tests/unit/ai/observability/test_metric_labels.py` for the enforced
policy).

---

## Troubleshooting

**Prometheus target shows `DOWN`** (Status → Targets)

- Confirm the API is actually running and `curl http://localhost:8000/metrics`
  succeeds from the host.
- On Linux, `host.docker.internal` may not resolve without the
  `extra_hosts: host.docker.internal:host-gateway` entry already present
  in `docker-compose.yml` — confirm your Docker Desktop/Engine version
  supports it, or point `prometheus.yml` at your host's real IP instead.

**Grafana shows no dashboards / empty "ResearchMind" folder**

- Check the container actually mounted the volumes:
  `docker compose logs grafana` for provisioning errors.
- Confirm `infra/observability/grafana/dashboards/*.json` are valid JSON
  (they're generated, not hand-edited — regenerate rather than patch by
  hand if one gets corrupted).

**`/metrics` returns 404 or isn't mounted**

- Check `PROMETHEUS_ENABLED` — if `false`, this is expected: the
  endpoint, the HTTP middleware, and every recorder all degrade to
  no-ops (this is the intended kill switch, see Rollback below).

**A panel is empty even though the app is getting traffic**

- Confirm the underlying metric name in the panel's query actually
  matches one declared in `names.py` — a typo'd metric key at a call
  site is silently dropped (by design, to prevent unbounded-cardinality
  accidents), not an error, so it won't show up anywhere including logs
  at `info` level (only a `debug`-level `prometheus.metric.unregistered`
  log line).

**Metrics look wrong for the API but the app itself is fine**

- Metrics recording is best-effort everywhere (PRD §5.4) — a broken
  Prometheus recorder cannot break Chat, Research, Generation, Memory,
  Web Search, MCP, or Guardrails. If metrics look wrong, the application
  itself should be unaffected; treat it as an observability bug, not an
  incident.

---

## Rollback

Set `PROMETHEUS_ENABLED=false` and restart the API. Every metrics call
site already falls back to a no-op recorder, `/metrics` is no longer
mounted, and the HTTP metrics middleware is never registered. Prometheus
and Grafana containers can keep running (they'll just show a `DOWN`
target) or be stopped independently — neither affects the API.

---

## Related docs

- [`infra/observability/README.md`](../../infra/observability/README.md) — commands-only quick reference
- `prds/prometheus_grafana_observability_prd.md` — the full design/requirements this was built from
- [`docs/architecture/observability-platform.md`](../architecture/observability-platform.md) — the older, pre-existing runtime-metrics/artifact observability system this complements (not replaces)
