# Research Runtime Architecture

## Current state (2026-07-23)

The sections below ("Phase 1 foundation" through "State and event rules")
describe the original walking-skeleton milestone and are historical. The
runtime has since grown a real product flow. See **ADR-034** for the
accepted decision record; summary:

```text
POST /research, POST /research/stream         → always linear ResearchService,
                                                  never routed through LangGraph

POST /research/proposals                      → planner-only, no run created
POST /research/proposals/{id}/approve         → creates ResearchRun + outbox dispatch
  (dedicated worker: apps/worker/research_runtime_main.py)
    → compile_multi_wave_research_graph()      → Postgres-checkpointed LangGraph:
       planner → dependency-wave retrieval (Send fan-out) → evidence →
       synthesis → review → bounded repair (≤1 revision, ≤1 gap round) →
       final report + PDF

GET /research/runs/{id}                       → owner-scoped lifecycle status
GET /research/runs/{id}/events                 → SSE replay+follow of canonical
                                                  progress events (DB-polled)
GET /research/runs/{id}/report                 → short-lived presigned PDF URL
```

Known open gaps (see ADR-034 for detail, kept here in sync so this doc
doesn't go stale the way the "Phase 1 foundation" section below did): no
cancellation endpoint despite `cancellation_requested` existing on the model;
no resume path for a run that crashes mid-execution; the SSE events endpoint
shares chat/generation's 5-minute stream duration ceiling, which a long
research run can exceed with no client-side reconnect built yet; no frontend
integration exists for any of this.

## Phase 1 foundation (historical)

The Research Runtime is a LangGraph-backed execution layer that will replace
the linear implementation incrementally behind a feature flag. ResearchMind
continues to own product contracts and persistence; LangGraph is not a domain
model or system of record.

```text
Research API (unchanged) ──> linear ResearchService
                              ^
                              | feature flag remains disabled in Phase 1
ResearchRuntimeService ──> StateGraph ──> injected checkpointer
```

The compiled Phase 1 graph is deliberately deterministic:

```text
START → initialize → complete → END
```

It demonstrates compact state, interrupt/resume behavior in memory-backed
tests, and canonical event adaptation. It does not perform research work.

## Persistence decision

`langgraph.checkpoint.memory.InMemorySaver` is test/local-only.
`langgraph-checkpoint-postgres==3.1.0` is directly pinned and its
`AsyncPostgresSaver` has passed a two-connection interrupt/resume integration
test. Production runtime execution remains disabled by
`Settings.research_runtime_enabled = False` until lifecycle/API wiring,
retention, and rollout authorization are complete.

Before enabling it, add `research_runs` as the owner-scoped lifecycle record
and prove a compatible Postgres saver with one-time migration/provisioning,
retention, process-restart resume, and authorization tests.

## State and event rules

State holds IDs, statuses, bounded counters, and later artifact references. It
must be JSON serializable. Full documents, provider payloads, embeddings, and
large context never enter graph state.

`LangGraphResearchEventAdapter` emits the existing `StreamEvent` contract;
only a run ID, graph thread ID, and stable phase are exposed.
