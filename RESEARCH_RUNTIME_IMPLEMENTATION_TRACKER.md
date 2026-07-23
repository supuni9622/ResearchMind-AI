# Research Runtime Implementation Tracker

**Owner:** ResearchMind AI  
**Started:** 2026-07-19  
**Source plan:** `researchmind_research_runtime_implementation_plan.md`

**2026-07-23 status:** Deep Research is now a complete, working, end-to-end
single-agent research workflow with a real frontend — proposal → approval →
async multi-wave graph → live-streamed progress → report-approval → PDF, all
clickable in the Research UI, not just the API. See `PROJECT_STATUS.md`'s
Phase 6 section and `PRODUCT_FLOWS_AND_GAPS.md` for the current, code-verified
state and remaining gaps (highest-priority: D2 single-worker scaling, D5
approval-decision timeout, D7 escalation-check latency — none are correctness
bugs). This file's checkboxes below are updated to match.

**2026-07-23 update, same day, later:** the golden path above was manually
click-through-verified in a real browser for the first time (previously only
test/lint/build-verified — see `REMAINING_WORK.md`'s now-closed item on this).
That pass surfaced and fixed two real correctness bugs in the dedicated
worker's session lifecycle (aborted-transaction poisoning across dispatches,
and a stale identity-mapped `report_decision` read after approval) — both
were invisible to this file's existing test coverage, which always constructs
a fresh session per test. Full detail: `PROJECT_STATUS.md` Phase 6's
"2026-07-23 verification pass" and `PRODUCT_FLOWS_AND_GAPS.md`. These were
found *within* the existing single-worker-process design (item 1's D2 gap
below), not a sign D2 itself needs to move up in priority.

## Phase 1 — Runtime foundation and compatibility spike

- [x] Verify installed LangGraph APIs: `StateGraph`, `Send`, `Command`,
  `interrupt`, and `InMemorySaver`.
- [x] Record direct LangGraph dependency ownership at locked version `1.2.9`.
- [x] Confirm the Postgres checkpointer package is not importable.
- [x] Add disabled `research_runtime_enabled` flag.
- [x] Add compact JSON-safe runtime request/state contracts.
- [x] Add deterministic idempotent reducers.
- [x] Add `START → initialize → complete → END` graph.
- [x] Prove in-memory interrupt/resume using a stable thread ID.
- [x] Adapt graph lifecycle updates to canonical ResearchMind events.
- [x] Document the architecture and checkpointing boundary in ADR-031/032.
- [x] Verify focused tests, lint, formatting, and Research API regressions.
- [x] Run the full repository test suite and type checking before merge.
  (Continuously re-verified through 2026-07-23; 1286 tests passing, mypy/ruff clean.)

## Explicitly deferred

- [x] Add the direct Postgres checkpointer dependency (`langgraph-checkpoint-postgres==3.1.0`).
- [x] Add `research_runs` lifecycle persistence, owner-scoped reads, and database idempotency constraint.
- [x] Run Postgres checkpoint provisioning and process-restart resume integration test.
- [x] Add `research_runs` migration, status-transition policy, and idempotency replay policy.
- [x] Add lifecycle persistence and idempotency handling for runtime-owned
  execution; it is not invoked by the linear public Research API.
- [x] Correct routing: `POST /research` and `POST /research/stream` always
  remain linear. Deep Research uses separate proposal/approval endpoints.
- [ ] Extend idempotent lifecycle routing to SSE only after the resume/replay
  event contract is designed; streaming remains on the established linear path.
- [x] Planner, rewriting, decomposition, retrieval fan-out, evidence, synthesis,
  review, approval, cancellation. (All live; memory-aware query rewriting and
  the report-approval interrupt landed 2026-07-23.) MCP integration is the one
  item in this bucket still not started.

## Phase 3 — Single-agent workflow (incremental)

- [x] Add a structured Planner contract, policy ceilings, schema validation, and
  a Generation Runtime-only planner service.
- [ ] Persist plan artifacts and add planner metrics/evaluation fixtures.
- [x] Add dependency-wave DAG validation and deterministic scheduling.
- [x] Add bounded owner-scoped task retrieval/context execution with compact
  evidence references and partial-failure results.
- [x] Wire a validated wave into LangGraph fan-out/fan-in and persist an
  idempotent compact evidence artifact.
- [x] Add deterministic chunk-identity evidence aggregation with explicit
  partial-failure warnings.
- [x] Coordinate successive DAG waves through LangGraph and persist one final
  aggregated evidence bundle.
- [x] Add bounded structured synthesis through the Generation Runtime with
  evidence-only citation validation.
- [x] Add a standard research-report draft shape and deterministic citation /
  partial-coverage review gate.
- [x] Persist idempotent final-report JSON and downloadable PDF artifacts;
  render only the bounded reviewed draft and compact evidence metadata.
- [x] Wire evidence aggregation through bounded synthesis, deterministic review,
  and final-report artifact persistence in the multi-wave LangGraph workflow.
- [x] Add an owner-scoped `GET /research/runs/{research_run_id}/report`
  contract that returns a five-minute presigned PDF download URL.
- [x] Add a separately gated V1 execution path: planner -> dependency waves ->
  retrieval -> evidence -> synthesis -> review -> final PDF -> persisted
  user-facing report. Memory extraction remains exclusively post-persistence.
- [x] Add one bounded synthesis-only revision route for citation omissions;
  evidence is reused and retrieval is never repeated for this repair.
- [x] Classify no-evidence runs as failed and partial retrieval as a controlled
  `completed_with_limitations` terminal outcome.
- [x] Add model-based review and one targeted evidence-gap research route,
  with bounded plan versioning and durable per-decision review artifacts.
- [x] Add evidence, synthesis, deterministic review, and decision-specific
  bounded repair routing before enabling graph-driven answers.

## Phase 6.9 — Resume, streaming, and approval (incremental)

- [x] Define stable, user-safe canonical runtime progress event types and labels.
- [x] Add an owner-scoped Research Run inspection response for durable lifecycle
  polling; checkpoint internals and artifact keys remain private.
- [x] Add durable event replay (`GET /research/runs/{id}/events`, DB-backed,
  owner-scoped, `after`-cursor) with its own SSE duration ceiling separate
  from chat/generation. Client-side reconnect-on-error still has no consumer
  (no frontend yet) -- `/research/stream` itself still never routes through
  the graph, unaffected by this.
- [x] Add protected cancellation (`POST /research/runs/{id}/cancel`,
  cooperative -- checked at bounded graph checkpoints, not synchronous) and
  resume after a crashed/interrupted run (`_begin(allow_resume_in_progress=True)`
  + LangGraph checkpoint resume via `aget_tuple`/`None` input). Plan-approval
  mid-run interrupts remain out of scope.

## Safety invariants

- The existing linear Research API remains the production path.
- Graph state must not store documents, provider responses, embeddings, or
  unbounded contexts.
- Memory extraction is allowed only after a final user-facing answer is
  persisted; Phase 1 invokes no memory services.

## Deep Research product flow — active implementation plan

These use cases now define the remaining implementation order. They extend the
runtime without changing the existing fast Chat or linear Research paths.

### 1. Linear Research versus Deep Research Runtime

- [x] Keep `POST /research` and `POST /research/stream` as the existing fast,
  linear Research APIs. Runtime feature flags must never silently route either
  endpoint into LangGraph.
- [x] A user asks in normal Research and gets offered **"this looks like it'd
  work better as a comprehensive research report"** when the query classifies
  as multi-step/evidence-backed. Built 2026-07-23 as `POST /research/
  escalation-check` + a Research UI suggestion banner (accept -> reviews and
  approves the already-persisted plan; reject -> continues Linear Research,
  unaffected). **Scoped to the Research interface, not Chat** — see item 3
  below, which is a separate, still-unbuilt surface.
- [x] Persist owner-scoped compact Deep Research proposals and validated plans;
  planning alone creates neither retrieval work nor a durable research run.
- [x] Only explicit user approval creates a durable `research_run`.
- [x] Wire a dedicated asynchronous LangGraph dispatcher for approved runs via
  a PostgreSQL transactional outbox and leased worker claims.
- [x] The approved runtime publishes canonical, user-safe progress events for
  the UI (via the event journal + SSE replay) and produces the final
  report/PDF artifact. **The Research UI now consumes these live** (2026-07-23
  — see item 5 below); this line originally said "no UI consumes these yet."
### 2. Approved asynchronous Deep Research

- [x] Build asynchronous dispatch for approved runs with a dedicated worker and
  PostgreSQL transactional outbox. It does not reuse the document-processing
  worker or FastAPI background tasks.
- [x] Add replayable event SSE and protected cancel/resume actions.

### 3. Chat-to-Research escalation

**Out of scope — will not be built.** This is a distinct surface from item 1's
Research-interface (Linear→Deep) escalation, which is built. Chat is intended
to remain a standalone fast conversational surface with no path into Deep
Research.

### 4. Plan proposal and approval lifecycle

- [x] Present a persisted owner-scoped proposal and plan before execution.
- [x] On approval, atomically create an owner-scoped `research_run` and link it
  to the proposal.
- [x] Dispatch the approved run through the durable transactional-outbox hand-off.
- [x] Show the proposed scope, tasks/waves, selected-source constraints, and
  bounded time/cost expectations. Built 2026-07-23: the Research UI's plan-
  review card renders goal, tasks, complexity badge, and an estimated cost/time
  budget before Approve/Dismiss.
- [x] Add the protected, idempotent approve action; only approval may create a
  runtime record.
- [x] Add cancel now that the worker/event contract is in place
  (`POST /research/runs/{id}/cancel`, cooperative).
- [ ] Later, support bounded plan edits (scope, priorities, and document/source
  constraints) before approval. Preserve the original proposal for audit.
- [x] **Beyond original scope**: a second, mid-run approval checkpoint — the
  graph now pauses at a real LangGraph `interrupt()` after review passes,
  before the report is persisted (`POST /research/runs/{id}/report-decision`,
  approve/reject-with-reason). Built 2026-07-23; see ADR (report-approval
  interrupt) and `PRODUCT_FLOWS_AND_GAPS.md`'s Deep Research flow. The Research
  UI has a working card for this step.

### 5. User-safe runtime progress

- [x] Define stable canonical event types and safe labels. The remaining work is
  durable publication, SSE replay, reconnect, and UI consumption.
- [x] Map internal runtime milestones to safe, non-chain-of-thought labels:
  Planning research; Searching selected sources; Analyzing evidence; Comparing
  findings; Reviewing citations; Generating report; Preparing PDF.
- [x] Update the Research UI from those canonical events. Do not expose raw
  prompts, provider responses, hidden reasoning, or internal graph state. Built
  2026-07-23: `use-deep-research.ts` consumes `GET /research/runs/{id}/events`
  live (fetch+SSE, cursor-based reconnect), rendering only the safe labels
  above — never raw graph state.

### 6. Later research lifecycle capabilities

- [x] Provide user-facing run history, terminal status, cancellation, and safe
  resume/replay behavior based on the checkpoint and event contract. Terminal
  status, cancellation, and event resume/replay are live in the Research UI as
  of 2026-07-23. **Partial**: this covers the *current session's* view of a
  run, not a dedicated history browser — completed Deep Research runs replay
  through `GET /research/conversations/{id}` as plain answer turns (same table
  Linear Research uses), not with the Deep Research card treatment.
- [ ] Support refining a completed report as a new version with explicit user
  intent, source/evidence lineage, and prior-report references.
- [x] Continue using the current owner-scoped model. Separate projects or
  workspaces are not required for this product stage.
