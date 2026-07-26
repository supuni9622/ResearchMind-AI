# Debugging Guide

Points to the tooling actually wired into the app for diagnosing a live issue.
For environment/setup problems (migrations, Docker, env vars), see
`docs/runbooks/troubleshooting.md` instead — this doc is about debugging
*behavior*, not *setup*.

---

## Where to look, by question

| Question | Where |
|---|---|
| Why did *this specific request* fail? | Structured logs, correlated by `request_id` |
| What did the model actually see/say for *this* generation? | LangSmith trace (see `docs/monitoring/langsmith.md`) |
| What did *this* research run cost? | PostgreSQL usage ledger (`/usage`) |
| Is error rate trending up across the fleet? | Grafana (`docs/monitoring/grafana.md`) |
| Is a metric/route getting slower over time? | Grafana / Prometheus (`docs/monitoring/prometheus.md`) |
| Why was a response blocked or regenerated? | `GuardrailReport` artifact (see below) |
| Why did a Deep Research report get revised/gap-researched? | `ResearchReviewArtifact` (see `docs/evaluation/report-quality.md`) |

## Structured logging

- `app/core/logging.py` configures `structlog`: colored console output in dev, JSON in production.
- `app/middleware/request_logging.py` binds `request_id`, `method`, `path`, `client` to contextvars for the lifetime of every request, so every log line in that request shares the same `request_id` — grep logs for one `request_id` to reconstruct a full request's trace.
- Noisy stdlib loggers (`uvicorn.access`, `sqlalchemy.engine`, `httpx`, `httpcore`) are silenced to `WARNING`.

## LangSmith traces

- Every Generation runtime call (streaming and non-streaming) is traced when `LANGSMITH_API_KEY` and `LANGSMITH_TRACING=true` are both set.
- Shows the real prompt, output, token usage, and `provider`/`model`/`runtime` tags per call.
- Best-effort — a LangSmith outage never fails generation (falls back to `NoOpTracer`).
- Full detail: `docs/monitoring/langsmith.md`.

## Guardrail / Validation artifacts

- `GuardrailService` persists a `GuardrailReport` per generation stage (input → retrieval → generation → runtime) via `GuardrailArtifactWriter` — inspect it to see exactly which check fired, at what severity, and what action (`WARN`/`REGENERATE`/`BLOCK`/`ESCALATE`) was taken.
- Validation outcomes (`ValidatorOutcome`, e.g. from `HallucinationValidator`) are separate from guardrail issues — same signal, different question ("did it work?" vs. "should we regenerate?").

## Aggregate/trend debugging

- Prometheus + Grafana answer fleet-wide questions (error rate, latency percentiles, cost, cache hit ratio) — they deliberately carry no `request_id`/`user_id`/`session_id`, so they can't answer per-request questions by design.
- See `docs/monitoring/prometheus.md` and `docs/monitoring/grafana.md` for dashboards and alerts, or `docs/runbooks/prometheus-grafana-observability.md` for the full operational runbook.

## Metrics/observability fail open

Metrics recording (Prometheus) and tracing (LangSmith) are both best-effort everywhere — a broken recorder or tracer cannot break Chat, Research, Generation, Memory, Web Search, MCP, or Guardrails. If observability looks wrong, treat it as an observability bug, not an application incident.
