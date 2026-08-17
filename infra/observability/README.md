# ResearchMind Observability (Prometheus + Grafana)

Implements `prds/prometheus_grafana_observability_prd.md`: a private
`/metrics` endpoint on the API, Prometheus scraping it, and Grafana
dashboards/alerts on top. This adds aggregate operational monitoring
alongside the existing tools -- it does not replace LangSmith tracing,
structured logs, or the PostgreSQL usage ledger (PRD §6).

## Layout

```text
infra/observability/
├── prometheus/
│   ├── prometheus.yml   # scrape config (targets the host-run API and workers)
│   └── alerts.yml       # API/runtime plus memory lifecycle/drift alert rules
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/prometheus.yml
│   │   └── dashboards/dashboards.yml
│   └── dashboards/
│       ├── researchmind-overview.json
│       ├── generation-runtime.json
│       ├── research-tools.json
│       ├── memory-runtime.json
│       └── eval-scores.json
└── README.md
```

Application-side code lives at `apps/api/app/ai/observability/prometheus/`
(registry, recorder, `/metrics` endpoint, HTTP middleware) and extends
the existing `app/infrastructure/metrics/` recorder abstraction that
Guardrails, Generation, and Memory already depend on -- no business
service imports `prometheus_client` directly.

## Why Prometheus scrapes `host.docker.internal`

This repo's `docker-compose.yml` does not run the API in a container --
it's started locally via `uvicorn` (see the root `README.md`). Prometheus
*does* run in Compose, so `prometheus.yml` points at
`host.docker.internal:8000` (Docker Desktop's host gateway) rather than
a Compose service name. If the API is ever containerized as an `api`
service, switch the scrape target to `api:8000` and add
`depends_on: api: condition: service_healthy` to the `prometheus` service.

## Local setup

1. Add the Prometheus/Grafana block from `.env.example` to your `.env`
   (defaults are fine for local dev).
2. Start the API as usual (`uvicorn app.main:app --reload` from `apps/api`,
   or however you normally run it).
3. Start Prometheus + Grafana:

   ```bash
   docker compose up -d prometheus grafana
   ```

4. Verify:

   ```bash
   curl http://localhost:8000/metrics        # API's own exposition
   curl http://localhost:8011/metrics        # memory lifecycle/inventory worker
   curl http://localhost:9090/-/healthy      # Prometheus is up
   ```

   Local URLs:

   - ResearchMind API: http://localhost:8000
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3001 (default `admin` / `admin` locally)

## Verification checklist

**Application**

```text
GET /metrics -> 200, includes researchmind_http_requests_total and
                researchmind_generation_requests_total after any traffic
```

**Prometheus** (`http://localhost:9090`)

- Status -> Targets: `researchmind-api` is `UP`; when their workers are
  running, the research-runtime and memory-lifecycle worker targets are also `UP`
- Graph: `researchmind_http_requests_total` returns data after hitting
  any API endpoint

**Grafana** (`http://localhost:3001`)

- Connections -> Data sources: `Prometheus` is healthy
- Dashboards: a `ResearchMind` folder exists with 5 dashboards, and
  panels populate after a few real requests

**Runtime** -- perform one of each and confirm the corresponding metric
increases: a Chat request, a `/research` request, a web-search-enabled
research request, an MCP paper-search call, a memory-eligible chat turn,
and a memory-skipped turn.

## Rollback

Set `PROMETHEUS_ENABLED=false` and restart the API. Every metrics call
site already falls back to a no-op recorder (PRD §5.4), `/metrics` is
no longer mounted, and the HTTP metrics middleware is not registered --
the rest of the application is completely unaffected.

## Multiprocess note

The current implementation assumes **one API process, one Uvicorn
worker**. `PrometheusMetricRegistry` uses an in-process `CollectorRegistry`
with no multiprocess support. Before running multiple Uvicorn/Gunicorn
workers behind this app, implement `PROMETHEUS_MULTIPROC_DIR` +
`multiprocess.MultiProcessCollector` + worker-exit cleanup, or metrics
will silently undercount (each worker only sees its own requests).

## Security

- Keep `/metrics` and Prometheus/Grafana off the public internet in any
  non-local environment -- there is no built-in auth on `/metrics`.
- No prompts, queries, full URLs, or any identifier (user/owner/session/
  research/request/document/citation/artifact id) is ever recorded as a
  metric or label -- see `apps/api/app/ai/observability/prometheus/names.py`
  and its accompanying tests (`tests/unit/ai/observability/test_metric_labels.py`).
- Set a strong `GRAFANA_ADMIN_PASSWORD` and disable sign-up
  (`GF_USERS_ALLOW_SIGN_UP=false`, already set) outside local dev.
