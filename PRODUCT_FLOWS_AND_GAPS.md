# Product Flows and Gaps — Chat, Linear Research, Deep Research

**Purpose:** a single, code-verified reference for how each of the three user-facing
paths actually works today, end to end, and what's weak about each — performance,
cost, correctness. Everything below was verified against the current code (not
against PRDs or trackers) as of 2026-07-23. Where a claim is about behavior rather
than a file, the file(s) it was checked against are named so it can be re-verified
after future changes.

**2026-07-23 update (rate limiting):** shipped for all three paths — Loopholes C2,
L2, and D3 are resolved, and X1 (cross-cutting) is fully closed at the per-owner
level. See each path's Cost section and the updated X1 entry for what's covered
and what's deliberately still open (per-owner vs. global limiting).

**2026-07-23 update (Deep Research frontend + escalation):** Deep Research went
from backend-only to having a real frontend, and a new `POST /research/
escalation-check` endpoint now backs an explicit-consent "this looks like it
needs Deep Research" suggestion inside the Research UI. Loophole D6 (no frontend
consumer) is resolved. See Deep Research's Flow/Cost sections and the new D7
entry for a real cost/latency tradeoff this introduced.

**2026-07-23 update (cache leakage fix):** Loophole D1 (Deep Research synthesis/
review calls sharing a cache namespace with Linear Research answers) is fixed —
both now use `CacheRuntime.REVIEWER` (`CachePolicy.NEVER`). X3 is resolved as a
result. This was the highest-severity open item in the doc.

**2026-07-23 update (browser click-through + worker session-staleness fixes):**
The Deep Research golden path was manually exercised end to end at
`localhost:3000/research` for the first time — DEEP mode toggle, submitting a
complex query, live SSE progress through to `awaiting_approval`, the
report-approval UI, and a completed run with a working PDF download. This
surfaced two real bugs invisible to unit/integration tests, both stemming from
`research_runtime_main.py` holding one `AsyncSession` for the worker's entire
process lifetime with `expire_on_commit=False` (`db/session.py`): (1) any
dispatch failure that aborted the session's transaction before its first
commit silently poisoned every dispatch claimed afterward, requiring a manual
process restart -- fixed with an explicit `session.rollback()` in
`ResearchRuntimeWorker.run_once`'s failure path; (2) `execute_approved_run`'s
resume-after-approval branch read `report_decision` off a possibly stale
identity-mapped `run` object -- loaded earlier in the same run's lifecycle,
before a separate API-request session committed the decision -- causing
"awaiting a report decision that was never recorded" even after approving.
Fixed with `await self._session.refresh(run)` immediately after the worker
loads the run, before any branch reads its fields (`execution.py`). Neither
bug was reachable by the existing test suite, which always constructs a fresh
session per test. See the "Performance" subsection below for the related,
still-open single-worker-process limitation these fixes sit inside of.

The product has three deliberately separate paths. They share the Generation
Runtime, Memory Platform, and (for two of the three) the Retrieval/Context
platforms, but nothing about one path silently activates another.

```
Chat              -- fast, conversational, memory-aware, NOT document-grounded
Linear Research   -- fast, one-shot, document-grounded (RAG), cited
Deep Research     -- slow, multi-step, proposal -> approval -> async graph -> report
```

---

## 1. Chat

**Entry points:** `POST /chat/stream` (SSE), `WS /chat/ws` — `apps/api/app/api/v1/chat.py`

### Flow

```
User message
  |
  v
Get-or-create Conversation (ConversationService)
  |
  v
Compact history if over budget (conversation_compaction.py)
  |
  v
Load recent prompt history + memory context
  (MemoryService.get_context: session + semantic + research memories)
  |
  v
Build GenerationRequest
  PromptContext.context = memory block + transcript
  PromptContext.chunks  = [] (ALWAYS — see Loophole C1)
  |
  v
GenerationRuntime.execute() / StreamingService.stream_generate()
  routing -> provider call -> guardrails -> cache -> validation
  |
  v
Stream tokens to client (SSE or WebSocket)
  |
  v
On completion: persist turn, extract+store memory (best-effort)
```

### What's actually grounded

Chat has **no retrieval or document context of any kind**. `_build_request()` in
`chat.py` never imports or calls `RetrievalService` or `ContextBuilderService` —
`PromptContext.chunks` is hard-coded to `[]`. The only non-conversational context
injected is the Memory Platform's session/semantic/research memory block
(`format_memory_context()` / `with_memory_context()`).

This means: **Chat answers are never grounded in a user's uploaded documents.**
A user who uploaded a PDF and asks about it in Chat gets an answer purely from the
model's own knowledge plus whatever memory happens to be relevant — not from the
document. This is a known, previously-documented gap (not new to this doc), but it
belongs here because it's the single biggest functional difference between Chat and
the other two paths, and nothing in the product surface currently tells the user
that.

### Performance

- Streaming (SSE/WS) — first token latency dominated by routing + provider TTFB,
  not by this path's own overhead (no retrieval round-trip to skip or pay for).
- History compaction (`compact_history_if_needed`) keeps the prompt bounded as a
  conversation grows — real, working control.
- Memory retrieval is `await`ed inline before the generation call, not
  parallelized with anything, but it's the same pattern used by Linear Research
  and is itself internally best-effort/fail-open (a memory backend outage doesn't
  block the turn — see `memory.chat.retrieval_failed` in `chat.py`).

### Cost

- `CacheRuntime.CHAT` → `CachePolicy.AUTO` (`caching/create.py`) — chat responses
  participate in both exact and semantic caching, which is the right default for a
  conversational surface with lots of repeated/near-duplicate small talk.
- Every generation call is cost-recorded via `GenerationUsageService.record()`
  (`generation/service.py:342-343`) — real per-call cost accounting exists in the
  `generation_usage` table, keyed by `session_id`/`conversation_id`.
- **Fixed (2026-07-23):** a per-owner fixed-window rate limit now runs before any
  conversation/generation work on both `/chat/stream` and `/chat/ws` —
  `ValkeyRateLimiter` (`infrastructure/rate_limiting.py`), `chat_rate_limit_requests`
  / `chat_rate_limit_window_seconds` in `settings.py` (default 20 requests / 60s per
  owner). A limited HTTP request never reaches the provider — it returns `429` with
  a `Retry-After` header before `StreamingResponse` is even constructed, so it costs
  nothing. A limited WS connection is closed with `1013 Try Again Later` before the
  payload is even read. This closes Loophole C2 below; the equivalent gap still
  exists, unfixed, for Linear Research and Deep Research proposals/approvals — see
  Loophole X1.

### Loopholes

| ID | Issue | Severity |
|----|-------|----------|
| C1 | Zero RAG grounding — `chunks=[]` always, `RetrievalService` never called | High (product gap, not new) |
| ~~C2~~ | ~~No rate limiting on chat turns~~ — **Fixed 2026-07-23**: `ValkeyRateLimiter`, wired into both `/chat/stream` and `/chat/ws` ahead of any conversation/generation work. Default 20 req/60s per owner (`chat_rate_limit_requests`/`chat_rate_limit_window_seconds`). No test coverage yet on the `/chat/ws` close-path specifically (only the shared check function + the HTTP 429 path are tested) — see note below. | Resolved |
| C3 | Semantic cache (`AUTO`) could theoretically surface a stale/wrong answer for a near-duplicate question from a *different* conversation if cache keys aren't tightly owner+context scoped — not verified false-positive-tested in this pass | Low/Unverified |

---

## 2. Linear Research

**Entry points:** `POST /research`, `POST /research/stream`, `POST /research/citations`
— `apps/api/app/api/v1/research.py` → `apps/api/app/ai/research/service.py`
(`ResearchService.research()` / `.stream_research()`)

### Flow

```
Query
  |
  v
Get-or-create Conversation (research-specific), set title from first query
  |
  v
Load conversation history
  |
  v
Memory retrieval (session/semantic/research, best-effort)
  |
  v
Retrieve (RetrievalService) + build context (ContextBuilderService)
  -> chunks, citations, sources
  |
  v
GenerationRequest:
  prompt_context = memory block + retrieved chunks/citations
  session_id     = research_id (fresh UUID per call)
  cache_runtime  = CacheRuntime.RESEARCH (AUTO)
  |
  v
GenerationRuntime.execute() -- ONE generation call, not multi-step
  |
  v
Persist ResearchSession + artifact
  |
  v
Extract + store memory (best-effort)
  |
  v
Return ResearchOutcome (answer, citations, sources, duration_ms)
```

This is genuinely a **single generation call** per request — plan → retrieve →
generate → done. There is no planning step, no multi-wave decomposition, no
review loop. "Linear" is accurate.

### Performance

- One retrieval round-trip + one generation call — the fastest grounded path in
  the product **at the API level**, by design. `POST /research` itself is
  unchanged and has no escalation-check gate — direct API callers still get the
  original single-call latency.
- **But the built-in Research UI's default submission path is no longer that
  fast.** `apps/web/src/app/(app)/research/page.tsx`'s `handleSubmit()` now
  `await`s `POST /research/escalation-check` (a full, uncached planner LLM call)
  *before* calling `/research/stream` whenever Linear mode is selected (the
  default). This was a deliberate, explicitly-requested design choice (see
  Loophole D7) — not a bug — but it means the UI's "fast path" now has a
  mandatory ~1-3s classification round-trip in front of it that the backend API
  itself doesn't have.
- `session_id=research_id` is a **fresh UUID every call** (`service.py:129,160`),
  unlike Deep Research where `session_id=research_run_id` persists across an
  entire multi-step run. This is correct for linear (one call = one cost record)
  but means **cost visibility here is per-call, not per-conversation** — summing
  cost across a research conversation's turns requires joining on
  `conversation_id`, not a single `session_id`, if that's ever needed.

### Cost

- `CacheRuntime.RESEARCH` → `CachePolicy.AUTO`, TTL from
  `settings.exact_cache_research_ttl_seconds` — exact + semantic caching both on.
  The code comment in `caching/create.py` explicitly reasons that this is safe
  because the exact-cache key includes the fully rendered transcript *and*
  retrieval context, so a genuinely different document context won't collide.
- Retrieval itself (embedding + vector search) is **not skipped on a cache hit**.
  `ResearchService.research()` calls `_retrieve_and_build_context()` unconditionally
  and only builds the `GenerationRequest` (where caching applies) afterward —
  caching is entirely inside `GenerationRuntime.execute()`, which runs strictly
  after retrieval. So every `/research` call pays the retrieval cost (embedding +
  Qdrant query) even when the eventual answer would have been an exact-cache hit;
  caching only saves the generation-provider call, not the retrieval round-trip.
  See L1 below.

### Loopholes

| ID | Issue | Severity |
|----|-------|----------|
| L1 | Confirmed: retrieval (embedding + Qdrant query) runs on every `/research` call regardless of cache outcome — caching only saves the generation-provider call. A repeat/near-duplicate question still pays full retrieval cost every time. | Medium — real, recurring cost, not a one-time architecture note |
| ~~L2~~ | ~~No rate limiting~~ — **Fixed 2026-07-23**: `/research`, `/research/stream`, and `/research/citations` share one `ValkeyRateLimiter` bucket per owner (default 15 req/60s, `research_rate_limit_requests`/`research_rate_limit_window_seconds`), checked before retrieval/generation starts. | Resolved |
| L3 | No per-conversation cost rollup surfaced anywhere (cost is trackable via `generation_usage` but nothing queries it by `conversation_id` today) | Low |

---

## 3. Deep Research

**Entry points:** `POST /research/escalation-check` (optional, explicit-consent
suggestion — see below) → `POST /research/proposals` →
`POST /research/proposals/{id}/approve` → (async, worker-driven) →
`GET /research/runs/{id}`, `GET /research/runs/{id}/events` (SSE),
`POST /research/runs/{id}/cancel`, `POST /research/runs/{id}/report-decision`,
`GET /research/runs/{id}/report` (PDF download)

Implementation: `apps/api/app/ai/runtime/research/` (proposal_service.py,
execution.py, workflows/multi_wave_research.py, planner/, retrieval/, synthesis/,
review.py) + `apps/worker/research_runtime_worker.py` +
`apps/worker/research_runtime_main.py`. Frontend:
`apps/web/src/features/research/` (`use-deep-research.ts`,
`components/deep-research-block.tsx`, `components/escalation-suggestion.tsx`) +
`apps/web/src/app/(app)/research/page.tsx` — see the new Frontend subsection below.

### Flow (current, as of the report-approval-interrupt work earlier this session)

```
0. [optional] POST /research/escalation-check  (Research UI's Linear-mode default)
     ResearchProposalService.check_escalation()
       -> same memory-aware ResearchPlanner.plan() call as propose() below
       -> SIMPLE plan  -> persists NOTHING, returns {suggested: false}
                          (caller proceeds with Linear Research, unaffected)
       -> MODERATE/COMPLEX -> persists a real ResearchProposal (identical
                          shape to step 1's output) and returns
                          {suggested: true, proposal: {...}}
       -> UI shows an accept/reject suggestion banner; accepting approves
          this SAME proposal_id (no second planner call); rejecting just
          runs Linear Research and leaves the orphaned proposal inert.

1. POST /research/proposals
     ResearchProposalService.propose()
       -> best-effort memory retrieval (session/semantic/research)
       -> ResearchPlanner.plan() [memory-aware; produces `rewritten_goal`]
       -> persist ResearchProposal (status=awaiting_approval)
       NO run, NO retrieval, NO durable state beyond the proposal+plan.
       (Also reached directly when the user manually picks Deep Research
       mode in the UI, skipping step 0 entirely.)

2. POST /research/proposals/{id}/approve
     ResearchProposalService.approve()
       -> atomically: create ResearchRun (status=created)
                       + link proposal -> run
                       + create ResearchRunDispatch row (transactional outbox)
       Single DB transaction. API request returns immediately; no graph work
       runs in-process (deliberate architectural rule).

3. [async] ResearchRuntimeWorker.run_once()
     claim_next() -- SELECT ... FOR UPDATE SKIP LOCKED, lease_seconds=900
     -> execution.execute_approved_run(run_id)
        -> transition CREATED -> PLANNING
        -> compile_multi_wave_research_graph(), invoke with recursion_limit=20
        -> graph:
             prepare_wave -> Send() fan-out to retrieve_task (per task, bounded
               concurrency via ResearchTaskRetrievalService's semaphore)
             -> advance_wave (loop until all waves done)
             -> aggregate evidence -> persist evidence artifact (S3/storage)
             -> synthesize (Generation Runtime call, evidence-grounded)
             -> review (deterministic + optional model-based review)
             -> route on ReviewDecision:
                  PASS                     -> await_report_approval (NEW)
                  REVISE_SYNTHESIS         -> retry synthesis (bounded)
                  RESEARCH_GAPS            -> one targeted gap-retrieval round
                  FINALIZE_WITH_LIMITATIONS -> await_report_approval (NEW)
                  FAIL                     -> terminal failure
             -> await_report_approval: interrupt() -- GRAPH PAUSES HERE
        -> if paused: run.status = AWAITING_APPROVAL, publish
           RESEARCH_AWAITING_APPROVAL, return (worker marks THIS dispatch
           attempt complete -- the run itself is not done)

4. POST /research/runs/{id}/report-decision  {"approved": true|false, "reason"}
     ResearchRunService.record_report_decision()
       -> persist decision into run.budget_usage.report_decision
       -> reopen the (1:1) dispatch row back to PENDING
       One transaction; nothing runs synchronously in this request either.

5. [async, next worker poll] execute_approved_run() again
     run.status == AWAITING_APPROVAL -> resume branch
       -> transition AWAITING_APPROVAL -> RESEARCHING
       -> graph.ainvoke(Command(resume=decision), ...)
       -> approved: persist_final_report (writer.write -> report JSON + PDF
          artifact refs) -> ResearchService.publish_runtime_report()
          (persists ResearchSession, triggers memory extraction)
          -> run.status = COMPLETED / COMPLETED_WITH_LIMITATIONS
       -> rejected: ResearchReportRejectedError -> run.status = FAILED,
          terminal_reason="report_rejected_by_user"

6. GET /research/runs/{id}/report -> 5-minute presigned S3 URL for the PDF
```

Cancellation (`POST /research/runs/{id}/cancel`) is cooperative: it flags
`cancellation_requested` and is checked at bounded checkpoints (before a new
wave, before a new synthesis attempt, and — as of this session — before resuming
from the report-approval pause). It is not a synchronous abort.

### Frontend (2026-07-23 — new; previously this path had no UI at all)

`apps/web/src/app/(app)/research/page.tsx` now has a Linear/Deep mode toggle
(default Linear) in the composer. The Deep Research destination is a real,
working state machine (`use-deep-research.ts`), not a stub:

```
plan_review  (goal, tasks, complexity badge, Approve/Dismiss)
    |  approve
    v
running      (LIVE event feed via GET /research/runs/{id}/events SSE --
    |          one connection per run, from approve() through report
    |          approval to a terminal event; see below)
    v
report_review (graph paused at the interrupt -- Approve report / Reject+reason)
    |  (same SSE connection keeps running through this pause -- the
    |   backend's replay loop doesn't close on `awaiting_approval`)
    v
done / failed (final GET /research/runs/{id} fetch for the authoritative
               status, then GET /research/runs/{id}/report for the PDF link)
```

The `running`/`report_review` stages consume the **already-existing** (built
earlier, previously with zero frontend consumers) canonical progress events —
"Planning research", "Searching selected sources", "Analyzing evidence",
"Reviewing citations and coverage", "Generating report", "Preparing PDF" —
live, not polled. The stream reconnects (resuming from the last event cursor)
up to 5 times on a dropped connection before surfacing an error. This resolves
Loophole D6.

**Known, disclosed scope trims in this pass** (not regressions, never built):
- The citations/sources side panel stays Linear-Research-only — a focused Deep
  Research turn shows its empty state there, not the final report's evidence.
- Conversation-history replay (`GET /research/conversations/{id}`) doesn't
  reconstruct the Deep Research card treatment for old completed runs — they
  replay as plain answer turns (that's how `publish_runtime_report` persists
  them: a normal `ResearchSession` row, same table Linear Research uses).
- Manual browser click-through of the golden path was performed 2026-07-23
  (see the update note above) — the mode toggle, submission, live SSE
  progress, report-approval UI, and completed-report PDF download all work.
  The Linear → Deep Research escalation banner specifically (a different UI
  surface from the Deep Research tab exercised here) remains unverified by
  hand, still resting on `tsc --noEmit`/`next lint`/`next build`/HTTP smoke
  test coverage only.

### Budgets (enforced, real)

`ResearchPlanningPolicy` (`planner/policies.py`), keyed by plan complexity:

| Complexity | max_tasks | max_review_iterations | max_duration_seconds | max_estimated_cost_usd |
|---|---|---|---|---|
| SIMPLE | 1 | 0 | 120 | $0.50 |
| MODERATE | 3 | 1 | 300 | $2.00 |
| COMPLEX | 5 | 2 | 600 | $5.00 |

(`planner/policies.py` — hard ceilings, independent of what the planner LLM recommends.)

Enforcement is real, not aspirational: `_execute_v1_graph`/`_resume_v1_graph_after_report_approval`
wrap the graph invocation in `asyncio.wait_for(timeout=budget.max_duration_seconds)`,
and `route_after_review` checks `cost_lookup()` (live sum from `generation_usage`,
keyed by `session_id=research_run_id`) against `max_estimated_cost_usd` before
allowing another repair iteration.

### Performance

- **Single worker process, serial processing.** `research_runtime_main.py` opens
  exactly one DB session and runs one `ResearchRuntimeWorker.run()` loop. The
  claim query (`SELECT ... FOR UPDATE SKIP LOCKED`) is safe for multiple worker
  *processes*, so horizontal scaling is possible — but nothing today starts more
  than one. **In practice, Deep Research runs across the entire application are
  processed one at a time**, with a 1-second poll interval between claims. Under
  any real concurrent load (multiple users approving proposals around the same
  time), later runs queue behind earlier ones for their full duration (up to 600s
  for COMPLEX plans) before even starting.
- Retrieval fan-out within a wave is bounded by a semaphore
  (`ResearchTaskRetrievalService`), not unbounded — real backpressure control,
  good.
- The report-approval pause is **not a performance cost** in the traditional
  sense (the graph returns immediately on `interrupt()`, it doesn't block a
  thread waiting for the human), but it does mean a run's wall-clock "time to
  report" now includes however long a human takes to review — worth knowing if
  anyone builds a p95-latency SLA around "proposal to PDF."

### Cost

- Planner calls are `CacheRuntime.PLANNER` → `CachePolicy.NEVER` — correct,
  deliberate: every plan should reflect the current memory/context state.
- **Fixed (2026-07-23):** Synthesis and review calls now tag `CacheRuntime.
  REVIEWER` (→ `CachePolicy.NEVER`) instead of `CacheRuntime.RESEARCH`
  (`synthesis/service.py:71`, `review.py:213`) — they no longer share a cache
  namespace with Linear Research's one-shot answers. This closes Loophole D1's
  cross-run leakage risk; regression tests assert `cache_runtime !=
  CacheRuntime.RESEARCH` on both call sites (`test_synthesis.py`,
  `test_review.py`).
- Full cost accounting exists and is actually enforced mid-run (see Budgets
  above) — this is one of the more mature parts of the platform.
- Every generation call across planning/retrieval-adjacent/synthesis/review is
  billed to `session_id=research_run_id`, so `GET /research/runs/{id}` combined
  with the `generation_usage` table gives an accurate running total per run.
- The report-approval interrupt does **not** add generation cost by itself (no
  LLM call happens at that node) — cost exposure is unchanged by this session's
  work, only the *timing* of when the final report gets persisted changed.
- `POST /research/escalation-check` is exactly as expensive as `POST /research/
  proposals` (same planner call under the hood) and **shares its rate-limit
  bucket** (`deep_research_proposal:{owner_id}`, 5 req/60s) — a burst of
  escalation checks from the UI counts against the same budget as a burst of
  actual proposal creations. See D7 for the resulting UX/cost tradeoff.

### Loopholes

| ID | Issue | Severity |
|----|-------|----------|
| ~~D1~~ | ~~Synthesis and review generation calls share `CacheRuntime.RESEARCH`~~ — **Fixed 2026-07-23**: both now tag `CacheRuntime.REVIEWER` (`CachePolicy.NEVER`), eliminating the cross-run semantic-cache leakage risk. Regression-tested. | Resolved |
| D2 | Single serial worker process — no horizontal scaling configured by default; concurrent Deep Research demand queues behind whatever run is currently executing (up to 10 minutes for COMPLEX plans). Confirmed the new frontend degrades sensibly while queued: with zero events yet in the DB, the live event stream just shows "Starting…" indefinitely rather than erroring — correct behavior, but a user has no way to tell "queued behind another run" apart from "about to start" from the UI alone. | Medium-High (scales with adoption) |
| ~~D3~~ | ~~No rate limiting on proposal creation~~ — **Fixed 2026-07-23**: `POST /research/proposals` is capped at `deep_research_proposal_rate_limit_requests` (default 5/60s) per owner, checked before the planner runs. `POST /research/proposals/{id}/approve` — the more expensive action — has its own, stricter cap: `deep_research_approval_rate_limit_requests` (default 5 per `deep_research_approval_rate_limit_window_seconds`=600s) per owner, checked before run creation/dispatch. Both return `429` with `Retry-After` and never touch `ResearchProposalService` when limited. | Resolved |
| D4 | No mid-run plan editing / no plan-approval interrupt (documented separately, unchanged by this session's work) | Medium (product gap, known) |
| D5 | Report-approval decision has no timeout: a run can sit in `AWAITING_APPROVAL` forever if the user never responds — no expiry, no reminder event, no auto-reject after N hours/days. The run just occupies a `research_runs` row indefinitely. | Low-Medium |
| ~~D6~~ | ~~`report-decision` endpoint has no frontend consumer yet~~ — **Fixed 2026-07-23**: full frontend built (plan review, live-streaming run status, report-approval, PDF download). See the new Frontend subsection above for what's covered and the disclosed scope trims (citations panel, history replay). | Resolved |
| D7 | The Research UI's default (Linear-mode) submission path now `await`s a full escalation-check planner call *before* running Linear Research — a deliberate, explicitly-requested design (blocking, not parallel, so a rejected suggestion cleanly "continues" rather than racing an already-started answer). Net effect: the UI's fast path is no longer as fast as the raw `POST /research` API — every default submission pays for one extra uncached LLM call (~1-3s) it wouldn't otherwise need. Not a bug; a known, disclosed tradeoff. **Possible follow-up**: run the check in parallel with Linear Research instead of gating it, showing the suggestion banner alongside/after the answer rather than before it. | Known tradeoff |

---

## 4. Cross-cutting concerns (apply to all three paths)

### X1 — Rate limiting (RESOLVED 2026-07-23 across all three paths)

`app/ai/guardrails/input/rate_limit.py`'s `RateLimitGuardrail` is still a
**permanent no-op** — confirmed by reading the implementation, not inferred:

```python
class RateLimitGuardrail(InputGuardrailInterface):
    """Foundation only ... no request-counting state exists anywhere in this
    codebase yet ... this is a pure interface seam: it always allows."""
    async def check(self, request: GenerationRequest) -> list[GuardrailIssue]:
        return []
```

It remains unused and unfixed — but is no longer the app's only rate-limiting
seam. A real, Valkey-backed limiter (`ValkeyRateLimiter`,
`app/infrastructure/rate_limiting.py`; fixed-window `INCR`+`EXPIRE`, one shared
instance via `get_rate_limiter()`/`enforce_rate_limit()` in
`app/dependencies/rate_limiting.py`) now sits directly in front of every
cost-generating route across all three paths, checked before any DB write,
retrieval, or generation call:

| Path | Route(s) | Scope key | Default limit |
|---|---|---|---|
| Chat | `POST /chat/stream`, `WS /chat/ws` | `chat:{owner_id}` | 20 req / 60s |
| Linear Research | `POST /research`, `/research/stream`, `/research/citations` (shared bucket) | `research:{owner_id}` | 15 req / 60s |
| Deep Research | `POST /research/proposals`, `POST /research/escalation-check` (shared bucket) | `deep_research_proposal:{owner_id}` | 5 req / 60s |
| Deep Research | `POST /research/proposals/{id}/approve` | `deep_research_approval:{owner_id}` | 5 req / 600s |

All limits are settings-configurable (`chat_rate_limit_*`, `research_rate_limit_*`,
`deep_research_proposal_rate_limit_*`, `deep_research_approval_rate_limit_*` in
`settings.py`). A limited request gets a `429` with a `Retry-After` header
(HTTP) and never reaches the underlying service (`.propose`/`.approve`/
`.research` are asserted un-awaited in tests) — for chat's WebSocket transport,
the connection is closed with `1013 Try Again Later` before the payload is even
read.

**Deliberately not rate-limited:** `GET` routes (status polls, history,
downloads — read-only, not cost-generating), `POST /research/runs/{id}/cancel`
(a safety valve — throttling it would be counterproductive), and
`POST /research/runs/{id}/report-decision` (bounded to one meaningful effect
per run regardless of how many times it's called — see the code comment on
`ResearchRunDispatchRepository.reopen`).

**Remaining gap:** the approval limit (5/600s) is a per-owner cap, not a
global one — it doesn't prevent many different accounts from each queuing
approvals that pile up behind the single serial worker (D2). Per-owner rate
limiting bounds abuse by any one account; it does not by itself solve
aggregate demand exceeding one worker's throughput.

### X2 — Cost accounting exists and is wired everywhere, but is not surfaced

`GenerationUsageService.record()` is called unconditionally after every
generation call (`generation/service.py:342-343`) when `usage_service` is
injected, and it is injected in both real composition roots
(`generation/create.py`, `generation/streaming/create.py`). So the raw data for
"what did this user/run/conversation cost" exists for all three paths. Nothing
today queries or surfaces it except Deep Research's own internal budget
enforcement (`_cost_so_far` via `GenerationUsageRepository.sum_cost_for_session`).
There's no user-facing or admin-facing cost dashboard, no per-user monthly cap.

### X3 — Caching policy consistency between "one-shot" and "multi-step, evidence-grounded" generation (RESOLVED 2026-07-23)

The caching platform's own policy table (`caching/create.py`) distinguishes
`RESEARCH`, `PLANNER`, `REVIEWER`, `CRITIC`, `SUMMARIZER` as separate runtimes
with separate policies — the design already anticipated that different
generation call *kinds* need different caching treatment. Deep Research's
synthesis and review calls not using their own runtime (they were both tagged
`CacheRuntime.RESEARCH`) was an oversight relative to the caching platform's
own design intent, not a deliberate choice — now fixed (see D1): both route
through `CacheRuntime.REVIEWER` (`CachePolicy.NEVER`), matching how `PLANNER`
already gets its own never-cached runtime.

### X4 — Memory retrieval is consistently best-effort/fail-open, everywhere

This is **not** a loophole — it's a correctly-applied pattern worth confirming
holds across all three paths, since a memory outage should never be a reason a
user can't chat, research, or run Deep Research. Verified in `chat.py`
(`memory.chat.retrieval_failed`), `research/service.py`
(`memory.research.retrieval_failed`), and this session's own additions to
`proposal_service.py`/`execution.py` (`research_runtime.proposal.memory_retrieval_failed`,
`research_runtime.execution.memory_retrieval_failed`) — all three swallow
exceptions from `MemoryService.get_context()` and continue without memory
context rather than failing the request.

---

## 5. Consolidated priority list

| Priority | ID | Fix |
|---|---|---|
| ~~✓~~ | X1 | **Done (2026-07-23)** — per-owner `ValkeyRateLimiter` now covers Chat, Linear Research, and Deep Research proposals/approvals/escalation-checks. Remaining: it's per-owner, not global — doesn't bound aggregate demand across many accounts against the single Deep Research worker (see D2). |
| ~~✓~~ | D6 | **Done (2026-07-23)** — Deep Research got a full working frontend (plan review, live SSE progress, report-approval, PDF download) plus the escalation-check suggestion flow. |
| ~~✓~~ | D1 | **Done (2026-07-23)** — synthesis/review generation calls moved off `CacheRuntime.RESEARCH` onto `CacheRuntime.REVIEWER` (`CachePolicy.NEVER`), eliminating the cross-run report-content leakage risk. Regression-tested. |
| 1 | D2 | Decide whether Deep Research needs horizontal worker scaling now or can stay single-process at current adoption; if scaling is needed, it's already DB-safe (`SKIP LOCKED`) — just needs more worker processes deployed |
| 2 | D5 | Add an expiry/auto-reject path for runs stuck in `AWAITING_APPROVAL` |
| 3 | D7 | Consider parallelizing the escalation-check with Linear Research instead of gating it, so the UI's default path isn't paying a mandatory extra LLM call in serial |
| 4 | L1 | Consider short-circuiting retrieval on an exact-cache hit for Linear Research (would need the cache lookup moved ahead of `_retrieve_and_build_context()`, a real flow change, not a config flip) |
| 5 | C1 | Product decision, not a bug: whether/when Chat should get retrieval grounding (already tracked elsewhere as a known gap) |
