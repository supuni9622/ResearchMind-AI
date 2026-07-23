# ADR-032 — LangGraph Checkpointing and Event Adaptation

**Status:** Accepted  
**Date:** 2026-07-19

## Decision

Phase 1 verifies LangGraph `1.2.9` with the in-memory checkpointer in unit
tests. Phase 2 adds and verifies `langgraph-checkpoint-postgres==3.1.0` using
the project's Postgres test database: a second saver connection resumes an
interrupted graph thread after explicit one-time provisioning.

Production checkpointing still requires deliberate application lifecycle
wiring, retention/deletion policy, and rollout authorization. Its setup path
is explicit and must never run from a request handler or implicitly on every
application start.

LangGraph updates are adapted into ResearchMind's existing canonical
`StreamEvent`. Raw graph state, node names, checkpoint payloads, prompts, and
evidence are never public event data.

## Consequences

- The application database will remain the system of record for public run
  lifecycle and authorization; a checkpointer only supports execution resume.
- API routing, cancellation, approval, and durable resume are deferred until
  the lifecycle model and production saver are both available.

## Status update (2026-07-23)

The lifecycle model (`research_runs`) and production `AsyncPostgresSaver`
saver are both now available, and API routing/approval have shipped: see
**ADR-034** for the accepted proposal → approval → dispatch → SSE-events →
report flow. Cancellation and resume-after-crash are still genuinely
deferred — ADR-034 lists them explicitly as open gaps rather than leaving
that unstated.
