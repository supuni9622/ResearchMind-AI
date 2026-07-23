# ADR-034 — Deep Research Product Routing: Proposal, Approval, and Asynchronous Runtime Dispatch

**Status:** Accepted
**Date:** 2026-07-23
**Related ADRs:** ADR-031 (Research Runtime Boundary), ADR-032 (LangGraph Checkpointing and
Event Adaptation), ADR-033 (Single-Agent vs Multi-Agent Decision Framework)

---

## Context

ADR-031 and ADR-032 (2026-07-19) recorded the Phase 1 decision to build the
Research Runtime as a disabled, deterministic walking skeleton that was "not
wired to the existing linear `/research` API," with "API routing,
cancellation, approval, and durable resume ... deferred."

Since then, `researchmind_research_runtime_implementation_plan.md` §0.1 and
`research_runtime_prd.md` §1.1 (both 2026-07-20) recorded a product-routing
decision in planning-doc form only: the linear Research APIs stay the default
experience, and Deep Research becomes an explicit, approval-gated additive
path. That routing decision has since been implemented
(`RESEARCH_RUNTIME_IMPLEMENTATION_TRACKER.md` tracks the detailed checklist),
but it was never captured as an ADR. ADR-031/032 as written now read as
current when they describe only the pre-implementation state, which is
misleading to anyone using them as the architecture reference. This ADR
records the routing decision itself and the state of its implementation as of
2026-07-23, and supersedes the "deferred" language in ADR-031/032 for the
items listed below.

## Decision

**The linear Research APIs remain the default, unconditional experience.**
`POST /research` and `POST /research/stream` always call the linear
`ResearchService` directly. No runtime feature flag, environment setting, or
request field switches these two routes onto LangGraph. (The
`get_research_runtime_execution_service` dependency in
`app/dependencies/research.py` constructs a `ResearchRuntimeExecutionService`
bridge behind `research_runtime_enabled` +
`research_runtime_postgres_checkpointing_enabled`, but no API route currently
depends on it — the only real caller of `ResearchRuntimeExecutionService` is
the dedicated worker described below. Treat that dependency function as
unused scaffolding, not a live routing path, until something injects it.)

**Deep Research is a separate, explicit, approval-gated flow:**

```text
POST /research/proposals
      ↓ (planner only — no retrieval, no run, no memory cost)
persisted ResearchProposal (status: awaiting_approval)
      ↓ user-initiated
POST /research/proposals/{proposal_id}/approve
      ↓ (idempotent — re-approving returns the same run)
persisted ResearchRun (status: created) + research_run_dispatches row (status: pending)
      ↓ dedicated worker (apps/worker/research_runtime_main.py), transactional
        outbox claim via SELECT ... FOR UPDATE SKIP LOCKED
ResearchRuntimeExecutionService.execute_approved_run()
      ↓ compile_multi_wave_research_graph() — Postgres-checkpointed LangGraph
planner → dependency-wave retrieval (Send fan-out) → evidence → synthesis →
review → bounded repair (≤1 synthesis revision, ≤1 gap-research round) →
final report + PDF artifacts
      ↓
GET /research/runs/{research_run_id}            — owner-scoped lifecycle status
GET /research/runs/{research_run_id}/events      — SSE replay+follow of canonical progress events
GET /research/runs/{research_run_id}/report      — short-lived presigned PDF URL
```

Only explicit approval creates a durable `research_run` and a dispatch
record; proposing a plan alone never retrieves evidence, never starts a
worker, and never creates memory-extraction cost.

**The worker is dedicated and never shares infrastructure with document
processing or FastAPI background tasks.** `ResearchRuntimeWorker` polls its
own `research_run_dispatches` outbox table; `apps/worker/research_runtime_main.py`
is a standalone process.

**Progress events are canonical and user-safe.** `LangGraphResearchEventAdapter.progress()`
maps internal phases to a fixed label set ("Planning research", "Searching
selected sources", "Analyzing evidence", ..., "Research report ready"). Raw
graph state, node names, checkpoint payloads, prompts, and evidence text
never cross the `ResearchRunEvent` boundary.

**Chat-to-Research escalation ("Research this") is out of scope and will not
be built.** This ADR originally recorded an intended shape (a user-facing
suggestion in Chat that creates a proposal on explicit user action, never
automatically) but that plan has been dropped. Chat is intended to remain a
standalone fast conversational surface with no path into Deep Research. The
distinct linear Research → Deep Research escalation (inside the Research
interface itself, not Chat) was built instead — see `check_escalation()` and
`PRODUCT_FLOWS_AND_GAPS.md`; do not conflate the two.

## What this explicitly does not yet cover (open gaps as of 2026-07-23)

Recording these here so this ADR doesn't repeat ADR-031/032's mistake of
going stale by omission:

- **No frontend integration exists.** Nothing in `apps/web/src` calls any of
  the proposal/run/events/report endpoints. This entire flow is reachable
  only via direct API calls today.
- **No proposal rejection/expiry endpoint.** Only `propose` and `approve`
  exist; there is no explicit way to decline or expire a proposal short of
  never approving it.
- **Resumed runs replay coarse phase events from the top.** `execute_approved_run`
  unconditionally republishes `RESEARCH_STARTED` / `PLANNER_COMPLETED` /
  `RETRIEVAL_STARTED` at the start of every attempt, including a resume of an
  interrupted run that's actually further along (e.g. already in review).
  Harmless to execution, but the SSE progress feed can show a stale-looking
  "Planning research" for a run that's really resuming near the end. Fixing
  this needs the event contract to carry resume-awareness, not just phase
  labels.

## Resolved since first written (2026-07-23 update)

The following were listed as open gaps in this ADR's original revision and
are now implemented:

- **Cancellation.** `POST /research/runs/{id}/cancel`
  (`ResearchRunService.request_cancellation`) flags a non-terminal run,
  owner-scoped and idempotent. It is cooperative, not synchronous: the graph
  observes it only at bounded checkpoints (before each dependency wave,
  before each synthesis attempt — see `compile_multi_wave_research_graph`'s
  `cancellation_check`), so cancelling a run already mid-retrieval or
  mid-synthesis call takes effect at the *next* checkpoint, not instantly.
- **Resume after a crashed run.** `_begin()` now allows re-entry from
  `PLANNING`/`RESEARCHING`/`REVIEWING`/`SYNTHESIZING`, gated by
  `allow_resume_in_progress=True` (only passed by the worker's
  `execute_approved_run`, not the direct `.execute()` path, since only the
  worker path is protected by the dispatch outbox's single-active-lease
  guarantee). `_execute_v1_graph` checks `checkpointer.aget_tuple()` and
  invokes with `None` input when a checkpoint already exists, so LangGraph
  resumes from its last completed step instead of restarting the planner and
  waves.
- **The SSE events endpoint no longer shares chat's 5-minute ceiling.**
  `sse_stream_response()` now takes an optional `max_duration_seconds`;
  `GET /research/runs/{id}/events` passes 1800s (30 min), comfortably above
  the runtime's own `max_duration_seconds` budget (≤600s for COMPLEX plans).
  The `after`-cursor reconnect primitive this relies on for anything longer
  still has no client implementing it, since no frontend exists yet.
- **Budget enforcement was mostly declared but not wired; it now is.**
  `ResearchPlanningBudget` gained `max_duration_seconds` and
  `max_estimated_cost_usd` per complexity tier. `max_review_iterations` is
  now actually read by `route_after_review` (previously hardcoded to `< 1`
  regardless of complexity, so a SIMPLE plan's "0 iterations" policy was
  never enforced). Cost is checked via a fresh `SUM(estimated_cost_usd)`
  read from the `generation_usage` ledger scoped to the run's `session_id` —
  real spend, not an estimate, but bounded by the same caveat as that
  ledger: `GenerationUsageService.record()` is fail-open, so a recording
  failure under-counts rather than blocking. Duration is enforced with
  `asyncio.wait_for()` around `graph.ainvoke()`, raising a classified
  `ResearchRunBudgetExceededError` → `FAILED` with `terminal_reason:
  "duration_budget_exceeded"`. `recursion_limit` is now passed explicitly
  (`Settings.research_runtime_graph_recursion_limit`, default 20) instead of
  relying on LangGraph's default.
- **The dead `execute_wave`/`max_concurrency` code is gone.** LangGraph's
  `Send()` fan-out was already calling `execute_task` directly per task, so
  the concurrency bound now lives on `ResearchTaskRetrievalService`'s own
  semaphore (acquired inside `execute_task`) rather than an unused batch
  wrapper.
- **A raw synthesis schema/citation failure no longer kills the whole run.**
  `synthesize()` catches `ResearchSynthesisError` and retries once inline
  with the failure reason as revision instructions, consuming the same
  `synthesis_revision_count` budget slot the review-triggered revision path
  uses (so total repair attempts stay bounded regardless of which path
  triggered them).

## Consequences

- ADR-031's "not wired to the existing linear `/research` API" and ADR-032's
  "API routing, cancellation, approval, and durable resume are deferred" are
  superseded for the proposal/approval/dispatch/events/report surface
  described above. Their walking-skeleton and Postgres-checkpointer-spike
  content otherwise still stands.
- Future work implementing cancel, crash-resume, SSE reconnect, or the Chat
  handoff should update this ADR's "open gaps" list rather than leaving those
  items undocumented, so this file doesn't drift the same way ADR-031/032
  did.
