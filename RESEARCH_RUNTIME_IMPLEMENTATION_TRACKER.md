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

## Web Search Tool Platform (2026-07-25)

Third human-approval checkpoint, mirroring the plan-approval checkpoint's
`interrupt()`/`Command(resume=...)` pattern. See ADR-036 and
`prds/2. web_search_tool_platform_prd.md`.

- [x] Framework-independent Web Search platform (`app/ai/tools/web_search/`):
  canonical models, provider interface/registry, `WebSearchService`
  (policy/budget/dedupe), Tavily provider via raw `httpx`.
- [x] Research-Runtime glue (`app/ai/runtime/research/web_search/`):
  `WebSearchNecessityService` (cheap OpenAI `gpt-5-nano` / Claude
  `claude-haiku-4-5` structured decision, deterministic pre-rules for
  DISABLED/REQUIRED) and web-result evidence normalization (reuses the
  existing Context Guardrails Platform for prompt-injection scanning).
- [x] Three new graph nodes (`evaluate_web_search_need`,
  `await_web_search_approval`, `search_web_gap`) inserted into the existing
  bounded gap-research loop in `multi_wave_research.py` — not a parallel
  node family, so the existing iteration/cost/recursion budget applies
  unchanged and a decline falls back to the pre-existing
  `prepare_gap_research` doc-only path.
- [x] `AWAITING_WEB_SEARCH_APPROVAL` status, lifecycle transitions,
  `record_web_search_decision`, TTL-expiry sweep coverage, and an
  `execution.py` resume branch, mirroring the plan-approval checkpoint's
  five-file surface exactly.
- [x] `GET /research/runs/{id}/web-search` +
  `POST /research/runs/{id}/web-search-decision`; `web_search_mode` /
  `web_search_auto_approve` / `include_domains` / `exclude_domains` added to
  `ResearchProposalRequest` only (Linear Research and Chat contracts
  unchanged).
- [x] Research UI: mode toggle (Off/Auto/Required) + "skip approval" checkbox
  in the composer, and an approve/reject card for the new checkpoint in
  `deep-research-block.tsx`.
- [x] Unit tests (web_search platform, necessity decision, evidence
  normalization) and extended `multi_wave_research` graph tests (disabled,
  AUTO decline/approve, pre-approved toggle, REQUIRED forcing, budget
  exhaustion, malformed-payload-as-rejection). Full suite green
  (1397 tests), ruff/mypy clean on both apps/api and apps/web.
- [ ] Not built this pass (deferred, see ADR-036): the standalone
  SSRF-hardened Web Fetch Platform, multi-provider fallback (Exa/Brave/MCP),
  org-wide domain policy management, the full evaluation/benchmark harness.
- Default-off: `WEB_SEARCH_ENABLED=false` and `web_search_mode=disabled`
  both default off; no `TAVILY_API_KEY` degrades to inert rather than
  crashing a run.

### Bug fix + early evidence-relevance detour (2026-07-25, same day, later)

- [x] Fixed a real crash: `ResearchService._runtime_evidence_metadata`
  assumed every evidence item's `document_id`/`chunk_id` was a real UUID
  (true for documents, not for web evidence's URL/`web:<uuid>` strings) --
  raised `ValueError: badly formed hexadecimal UUID string` the first time
  a run with web evidence reached report publication. Now falls back to a
  deterministic `uuid5`-derived UUID. Also shortened web citation markers
  from `web:<uuid>` to `W{round}-{n}` (matches the app's `S1`/`S2` style and
  fixes a citation-card display truncation bug the long form caused).
- [x] `route_after_aggregate` now detours through
  `evaluate_web_search_need` unconditionally, right after evidence
  aggregation and before plan approval, whenever `auto`/`required` is set --
  catching a private corpus that's topically irrelevant to the goal (not
  just "thin") before a synthesis call is ever spent on it. Previously the
  web-search check only fired post-review (after a full synthesis pass) if
  the reviewer happened to flag a gap; a confidently off-topic corpus can
  pass citation-integrity review cleanly, so the mismatch surfaced only as
  a disclaimer buried in the synthesized report's abstract.
- [x] Considered and rejected a numeric relevance-score threshold at
  aggregation time: `ResearchEvidenceReference.score` is a Reciprocal Rank
  Fusion sum (rank-derived), not a semantic-similarity measure, so it
  can't reliably distinguish a confidently-wrong top hit from a genuinely
  relevant one. Reused the existing cheap necessity-decision model instead
  (prompt tuned to also judge topical relevance, not just recency).
  See ADR-036's addendum for the full reasoning, including the discarded
  Voyage `rerank-2` score as a deferred, more principled alternative.
- [x] `REQUIRED` mode's "at least one web source" guarantee moved from a
  post-review-PASS forced check to this same early, deterministic
  aggregate-time detour -- strictly earlier and cheaper.
  Full suite green (1401 tests), ruff/mypy clean.

### Two more fixes from the same live run (2026-07-25, same day, later still)

- [x] `search_web_gap` no longer charges the early (pre-plan-approval)
  detour against `gap_research_count` -- that's the same counter
  `route_after_review` checks against the review-repair budget
  (`max_review_iterations`, as low as 1 for MODERATE plans), and the early
  detour always runs before any synthesis attempt, so charging it there
  could leave zero budget for a legitimate post-synthesis citation fix.
- [x] Budget-exhausted `REVISE_SYNTHESIS` (citation-integrity fix needed,
  no repair rounds left) now finalizes with limitations
  (`completed_with_limitations`, matching the existing budget-exhausted
  `RESEARCH_GAPS` behavior) instead of routing to `fail()` and raising an
  unhandled `RuntimeError` -- explicit user decision, applies uniformly to
  both `REVISE_SYNTHESIS` triggers. See ADR-036's second addendum.
  Full suite green (1402 tests), ruff/mypy clean.

### AUTO model swap + Chat web search (2026-07-25, same day, latest)

- [x] `WebSearchNecessityService`'s default OpenAI model swapped
  `gpt-5-nano` → `gpt-5-mini`: production logs showed `gpt-5-nano`
  unreliably following the structured-output contract for this call
  (invalid/non-repairable JSON, not truncation), making AUTO mode silently
  fail closed to "no search needed" on every run. Paired with a
  JSON-only-output system prompt and higher `max_tokens`/
  `max_regeneration_attempts` (300→600, 1→2).
- [x] Chat gets web search (Linear Research explicitly excluded, per user
  decision). No approval checkpoint — a new `web_search_enabled: bool`
  toggle on `ChatStreamRequest` is itself the one-time-per-turn approval,
  since Chat has no interrupt/resume mechanism to pause on. Reuses the
  existing `WebSearchService`/`WebSearchNecessityService`/
  `normalize_web_search_result` unchanged.
  - New: `app/ai/runtime/chat/web_search.py::run_chat_web_search()`
    (best-effort — any failure degrades to no search for that turn, never
    fails the chat turn) and `ChatEventType`
    (`chat_web_search_started/completed/skipped`, `category=TOOL`).
  - `stream_chat` (SSE) and `stream_chat_ws` (WebSocket) both call
    `run_chat_web_search()` before generation and prepend a formatted
    web-context block to the prompt when results were found, via a
    `_chain_events()` wrapper generator that emits the search's status
    events ahead of the token stream.
  - Frontend: a Web Search toggle button in `chat-composer.tsx`,
    `use-chat.ts` handles the three new SSE event types (attaching
    `webSearch: { stage, query, sources }` to the streaming assistant
    message), and `message-bubble.tsx` renders a "Searching the
    web…"/"Searched the web" chip plus clickable source-domain pills.
  - [x] 8 new unit tests for `run_chat_web_search()` (toggle off, missing
    collaborators, unavailable service, necessity failure, no-search-needed,
    successful search, empty results, search failure) — all best-effort
    degradation paths covered.
  Full suite green (1410 tests), ruff/mypy clean across all 1159 backend +
  test source files, frontend `tsc --noEmit`/`eslint`/`next build` clean.
  Toggle defaults off; Linear Research's request/response schemas have no
  `web_search_enabled` field, so it's untouched by construction.
