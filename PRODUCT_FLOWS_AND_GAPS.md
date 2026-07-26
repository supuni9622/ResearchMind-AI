# Product Flows and Gaps — Chat, Linear Research, Deep Research

**Purpose:** a single, code-verified reference for how each of the three user-facing
paths actually works today, end to end, and what's weak about each — performance,
cost, correctness. Everything below was verified against the current code (not
against PRDs or trackers) as of 2026-07-23. Where a claim is about behavior rather
than a file, the file(s) it was checked against are named so it can be re-verified
after future changes.

**2026-07-25/26 update (paper search MCP client, markdown rendering, session-state fix):**
ResearchMind became an MCP **client** for the first time — a narrow,
single-tool "Research Intelligence MCP" paper-search platform
(`app/ai/tools/paper_search/`, ADR-037) reachable from Chat (toggle-gated
subsection below) and Deep Research (a non-blocking post-report suggestion
node, not a 4th approval checkpoint). This is scoped strictly to one
external server/one tool/two call sites — it does **not** start the
general-purpose Phase 6/7 Agentic/MCP Ecosystem work, which remains
deferred per ADR-033; see each path's new subsection below. Separately, a
real production bug in the Memory Platform was fixed the same session: a
Deep Research/Chat follow-up using a pronoun ("so how is magma related to
it?") had no durable session-level "what is this about" state to resolve
against — a new `SessionStateUpdaterService` now maintains one evolving,
upserted-in-place summary per session after every turn. And (uncommitted
as of 2026-07-26): Chat, Linear Research, and Deep Research answers now
render as real Markdown instead of raw `whitespace-pre-wrap` text — see
each path's Frontend note.

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

**2026-07-24 update (plan-approval editing):** Loophole D4 (no mid-run plan
editing, no plan-approval interrupt) is fixed — a new `await_plan_approval`
graph interrupt, positioned after evidence-aggregation but before the
synthesis call, gives plan approval the same view/edit/reject-with-reason
treatment report approval (D13) already had. See D4's entry and the new
Flow/Frontend diagrams below.

**2026-07-24 update (user-testing pass on the Deep Research frontend):** the
user hand-tested the flow verified end-to-end the day before and reported
seven issues from actually using it. Six were real, root-caused gaps and are
now fixed — D8 (event log disappearing after `running`), D9 (PDF citations
showing raw document UUIDs instead of filenames), D10 (Linear and Deep
Research never sharing one conversation, and History showing one row per
question as a symptom of the same root cause), D11 (Deep Research state lost
on refresh), D12 (report rejection was a terminal `FAILED` that discarded the
already-synthesized draft), and D13 (report approval was blind — no way to
see or edit the draft first). The seventh (perceived lack of caching in Deep
Research) turned out to already be D1's fix working as intended, not a new
bug — see D1's entry and the Cost section below.

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

### Optional tool augmentation (Web Search + Paper Search, both 2026-07-25/26)

Two independent, opt-in tool platforms can now add context to a Chat turn.
Neither is retrieval (Loophole C1 above still stands — a user's own
documents are never consulted in Chat) — both reach *external* sources
instead:

- **Web Search** (ADR-036) — `ChatStreamRequest.web_search_enabled`
  (default off). Reuses the same `WebSearchService`/
  `WebSearchNecessityService`/evidence-normalizer Deep Research uses.
  `run_chat_web_search()` (`app/ai/runtime/chat/web_search.py`).
- **Paper Search** (ADR-037) — `ChatStreamRequest.paper_search_enabled`
  (default off), reaching a Research Intelligence MCP server (ResearchMind's
  first MCP **client** integration — one external server, one tool,
  `search_papers`; not the general Phase 6/7 MCP Ecosystem). Deliberately
  **no** necessity-decision call, unlike Web Search — enabling the toggle
  always searches, using a query distilled from the user's prompt via
  `PaperQueryExtractionService`. `run_chat_paper_search()`
  (`app/ai/runtime/chat/paper_search.py`).

Both: toggle *is* the approval (Chat has no interrupt/resume mechanism to
pause on), both degrade silently to a no-op on any failure or when
unconfigured (never fail the turn), and both surface a status chip +
source pills in `message-bubble.tsx` once results land. A user can enable
both at once — the two run independently and both contexts get folded into
the same generation call.

### Frontend rendering (2026-07-26, uncommitted)

Chat answers now render through a shared `Markdown` component
(`apps/web/src/components/ui/markdown.tsx`, `react-markdown` +
`remark-gfm` + `remark-breaks`) instead of raw `whitespace-pre-wrap` text —
lists, headings, bold, tables, and code blocks in a model's answer now
format correctly instead of showing literal markdown syntax.

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
| ~~C1~~ | ~~No rate limiting on chat turns~~ — **Fixed 2026-07-23**: `ValkeyRateLimiter`, wired into both `/chat/stream` and `/chat/ws` ahead of any conversation/generation work. Default 20 req/60s per owner (`chat_rate_limit_requests`/`chat_rate_limit_window_seconds`). No test coverage yet on the `/chat/ws` close-path specifically (only the shared check function + the HTTP 429 path are tested) — see note below. | Resolved |
| C2 | Semantic cache (`AUTO`) could theoretically surface a stale/wrong answer for a near-duplicate question from a *different* conversation if cache keys aren't tightly owner+context scoped — not verified false-positive-tested in this pass | Low/Unverified |

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
`POST /research/runs/{id}/cancel`, `GET /research/runs/{id}/draft` (new
2026-07-24 — read the pending draft before deciding),
`POST /research/runs/{id}/report-decision` (as of 2026-07-24, optionally
carries an edited draft), `GET /research/runs/{id}/report` (PDF download).
Also: `GET /research/conversations/{id}` (as of 2026-07-24, replays Deep
Research turns in a conversation thread too, not just Linear ones — see D11).

Implementation: `apps/api/app/ai/runtime/research/` (proposal_service.py,
execution.py, workflows/multi_wave_research.py, planner/, retrieval/, synthesis/,
review.py) + `apps/worker/research_runtime_worker.py` +
`apps/worker/research_runtime_main.py`. Frontend:
`apps/web/src/features/research/` (`use-deep-research.ts`,
`components/deep-research-block.tsx`, `components/escalation-suggestion.tsx`) +
`apps/web/src/app/(app)/research/page.tsx` — see the new Frontend subsection below.

### Flow (current, as of the plan-approval-interrupt work, 2026-07-24)

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
             -> await_plan_approval: interrupt() -- GRAPH PAUSES HERE (NEW
                  2026-07-24; reached once per run -- REVISE_SYNTHESIS/
                  RESEARCH_GAPS retries below route straight back to
                  synthesize, bypassing this checkpoint)
             -> synthesize (Generation Runtime call, evidence-grounded)
             -> review (deterministic + optional model-based review)
             -> route on ReviewDecision:
                  PASS                     -> await_report_approval
                  REVISE_SYNTHESIS         -> retry synthesis (bounded)
                  RESEARCH_GAPS            -> one targeted gap-retrieval round
                  FINALIZE_WITH_LIMITATIONS -> await_report_approval
                  FAIL                     -> terminal failure
             -> await_report_approval: interrupt() -- GRAPH PAUSES HERE
        -> if paused at await_plan_approval: run.status =
           AWAITING_PLAN_APPROVAL, publish RESEARCH_AWAITING_PLAN_APPROVAL
        -> if paused at await_report_approval: run.status =
           AWAITING_APPROVAL, publish RESEARCH_AWAITING_APPROVAL
        -> either way, return (worker marks THIS dispatch attempt complete
           -- the run itself is not done)

3.3 [new 2026-07-24] GET /research/runs/{id}/plan
     ResearchPlanInspectionService.get_pending_plan()
       -> reads the paused run's LangGraph checkpoint directly
          (channel_values["plan"]/["evidence_bundle"]) -- evidence exists
          at this point but no draft does yet (synthesize hasn't run)
       -> returns goal/rewritten_goal/complexity/tasks, the evidence
          summary (completed/failed task counts, warning count), and
          citations resolved to filenames
       409s if the run isn't AWAITING_PLAN_APPROVAL, or the checkpoint has
       no evidence yet

     POST /research/runs/{id}/plan-decision
       {"approved": true|false, "reason": ..., "edited_plan": {"rewritten_goal": ...} | null}
       ResearchRunService.record_plan_decision()
         -> persist decision into run.budget_usage.plan_decision
         -> reopen the (1:1) dispatch row back to PENDING
       Approving resumes straight into synthesize (with the edited goal
       substituted onto state["plan"] if one was given); tasks/complexity
       aren't editable here since retrieval for the original tasks has
       already run. Rejecting routes straight to END without ever calling
       synthesize -- there's no draft yet to publish as a plain answer
       (unlike a rejected *report*, see step 5 below), so the run ends
       CANCELLED (terminal_reason="plan_rejected_by_user") rather than
       COMPLETED_WITH_LIMITATIONS. The gathered evidence isn't discarded,
       it's just never turned into a report.

3.5 GET /research/runs/{id}/draft
     ResearchDraftInspectionService.get_pending_draft()
       -> reads the paused run's LangGraph checkpoint directly
          (channel_values["draft"]/["evidence_bundle"]/["review"]) -- the
          only place this content exists before persist_final_report runs
       -> returns title/abstract/methodology/findings/discussion/conclusion,
          citations resolved to filenames (not raw document UUIDs -- see D9),
          and the review's scores/decision/limitations
       409s if the run isn't AWAITING_APPROVAL, or the checkpoint has no
       draft yet

4. POST /research/runs/{id}/report-decision
     {"approved": true|false, "reason": ..., "edited_draft": {...} | null}
     ResearchRunService.record_report_decision()
       -> persist decision into run.budget_usage.report_decision
       -> if approved with edited_draft: merge the edited free-text fields
          onto the original checkpointed draft (citation_ids/schema_version/
          limitations carried over unchanged -- an edit can never introduce
          an unsupported citation, so no re-validation against the evidence
          bundle is needed) and store the merged, fully-valid draft too
       -> reopen the (1:1) dispatch row back to PENDING
       One transaction; nothing runs synchronously in this request either.

5. [async, next worker poll] execute_approved_run() again
     run.status == AWAITING_APPROVAL -> resume branch
       -> transition AWAITING_APPROVAL -> RESEARCHING
       -> graph.ainvoke(Command(resume=decision), ...)
       -> approved (optionally with an edited draft -- see D13): await_report_
          approval overwrites state["draft"] with the merged edit, then
          persist_final_report (writer.write -> report JSON + PDF artifact
          refs) -> ResearchService.publish_runtime_report() (persists
          ResearchSession, triggers memory extraction)
          -> run.status = COMPLETED / COMPLETED_WITH_LIMITATIONS
       -> rejected (fixed 2026-07-24, see D12): route_after_report_approval
          routes straight to END, SKIPPING persist_final_report only --
          draft/evidence_bundle/review are already-set, unreduced state
          channels that survive regardless of which node the graph
          terminates at, so publish_runtime_report still runs and the
          synthesized draft still gets published as a plain answer, just
          without a PDF -> run.status = COMPLETED_WITH_LIMITATIONS,
          terminal_reason="report_rejected_returned_as_answer" (previously:
          ResearchReportRejectedError -> run.status = FAILED,
          terminal_reason="report_rejected_by_user", discarding the draft)

6. GET /research/runs/{id}/report -> 5-minute presigned S3 URL for the PDF
```

Cancellation (`POST /research/runs/{id}/cancel`) is cooperative: it flags
`cancellation_requested` and is checked at bounded checkpoints (before a new
wave, before a new synthesis attempt, and — as of this session — before resuming
from the report-approval pause). It is not a synchronous abort.

### Two optional tool augmentations added after this flow diagram was written (2026-07-25/26)

The numbered flow above predates both; noted here rather than renumbering
every step:

- **Web Search (ADR-036, 2026-07-25)** — a **third** `interrupt()`
  checkpoint (`await_web_search_approval`), reused inside the existing
  bounded gap-research loop between `aggregate`/`await_plan_approval` and
  `synthesize`. `web_search_mode` (disabled/auto/required) +
  `web_search_auto_approve` on `ResearchProposalRequest`. `AUTO` asks
  unless pre-authorized; `REQUIRED` never asks; a decline falls back to the
  pre-existing doc-only gap-research node. See `PROJECT_STATUS.md`'s
  "2026-07-25 Web Search Tool Platform" section for full detail (this file
  was not updated with a dedicated flow diagram change at the time).
- **Paper Search (ADR-037, 2026-07-25/26)** — **not** a 4th approval
  checkpoint. `ResearchProposalRequest.paper_suggestions_enabled` (default
  off) adds one new node, `suggest_related_papers`, sequential between
  step 5's `persist_final_report` and `END` — after the report is already
  durably persisted, so there's nothing left to gate. A Research
  Intelligence MCP server (ResearchMind's first MCP **client**
  integration — one server, one tool, not the general Phase 6/7 MCP
  Ecosystem) is queried for papers related to the run's goal (query
  distilled via `PaperQueryExtractionService`, since the raw
  `rewritten_goal` sentence returns zero results from the paper-search
  backend). Wrapped in a broad `try/except` + `asyncio.wait_for` timeout:
  any failure emits `RESEARCH_RELATED_PAPERS_SKIPPED` and the run reaches
  `END` exactly as it would have without the feature; success emits
  `RESEARCH_RELATED_PAPERS_COMPLETED` with up to 5 papers
  (title/authors/year/url) in the event metadata, rendered as a read-only
  card (no approve/reject) after the report completes.

### Frontend (2026-07-23 — new; previously this path had no UI at all)

`apps/web/src/app/(app)/research/page.tsx` now has a Linear/Deep mode toggle
(default Linear) in the composer. The Deep Research destination is a real,
working state machine (`use-deep-research.ts`), not a stub:

```
plan_review  (goal, tasks, complexity badge, Approve/Dismiss -- pre-run,
    |          before any retrieval has happened)
    |  approve
    v
running      (LIVE event feed via GET /research/runs/{id}/events SSE --
    |          one connection per run, from approve() through both
    |          approval pauses to a terminal event; see below. As of
    |          2026-07-24, this step log stays visible in every later
    |          stage too -- see D8 -- instead of disappearing once
    |          `running` ends.)
    v
goal_review  (graph paused at await_plan_approval -- new 2026-07-24, see
    |          D4 -- shows the goal and the evidence already gathered for
    |          it via GET /research/runs/{id}/plan, with the goal editable
    |          in place before Continue to report / Reject+reason. Reached
    |          once per run, not on automatic repair-loop retries.)
    |  approve
    v
running      (resumes into synthesis/review)
    v
report_review (graph paused at await_report_approval -- as of 2026-07-24,
    |          shows the actual draft (title/abstract/findings/citations/
    |          review scores) via GET /research/runs/{id}/draft, editable
    |          in place -- see D13 -- before Approve report / Reject+reason)
    |  (same SSE connection keeps running through both pauses -- the
    |   backend's replay loop doesn't close on `awaiting_plan_approval` or
    |   `awaiting_approval`)
    v
done / failed (final GET /research/runs/{id} fetch for the authoritative
               status, then GET /research/runs/{id}/report for the PDF link
               -- or, as of 2026-07-24, if the report was rejected, the
               synthesized answer rendered inline instead of a PDF link;
               see D12. Rejecting at `goal_review` instead lands here with
               no answer at all (see D4) -- there's no draft yet to fall
               back to. `failed` is now reserved for genuine failures, not
               user rejection.)
```

The `running`/`report_review` stages consume the **already-existing** (built
earlier, previously with zero frontend consumers) canonical progress events —
"Planning research", "Searching selected sources", "Analyzing evidence",
"Reviewing citations and coverage", "Generating report", "Preparing PDF" —
live, not polled. The stream reconnects (resuming from the last event cursor)
up to 5 times on a dropped connection before surfacing an error. This resolves
Loophole D6.

**Frontend rendering (2026-07-26, uncommitted):** the linear-answer/rejected-
report answer path (`renderAnswer()` in `research-block.tsx`, shared with
`deep-research-block.tsx`) now renders through the same shared `Markdown`
component Chat uses, replacing a hand-rolled string-splitting regex for
citation badges with a remark plugin operating on the parsed markdown tree.
This also fixed a real bug: the old regex only matched `S\d+`, so a web
citation marker (`[W1-1]`) embedded in a rejected report's fallback answer
rendered as plain unstyled text instead of a citation chip.

**Known, disclosed scope trims** (not regressions, never built):
- The citations/sources side panel stays Linear-Research-only — a focused Deep
  Research turn shows its empty state there, not the final report's evidence
  (the report-review card does show its own resolved citations inline as of
  2026-07-24 — see D13 — but the separate side panel doesn't pick them up).
- **Resolved 2026-07-24 (see D11):** conversation-history replay
  (`GET /research/conversations/{id}`) now does reconstruct the Deep Research
  card treatment — including a still-running or awaiting-approval run's live
  state, not just completed-and-flattened answer turns — via a new
  `deep_research_runs` field on the response and the frontend's
  `hydrateFromConversation`.
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

#### LLM call count per run (derived from the graph, not a separate budget)

Retrieval (`retrieval/service.py::_execute_task`) and decomposition
(`decomposition/scheduler.py::dependency_waves`) never call an LLM — hybrid
search + context building, and a deterministic topological sort,
respectively — regardless of task count. Only three nodes do: the planner
(once, and only when a run has no pre-approved plan already persisted — the
normal approved-run path reuses the proposal's plan and skips it), synthesis
(once per pass through `synthesize`, `multi_wave_research.py`), and review
(0 or 1 call per pass — `review_draft()`'s deterministic check runs first
and only escalates to the model in `_model_review` if that doesn't already
resolve the decision, `review.py`). The `max_review_iterations` column above
is what caps repeat synthesize+review passes from the repair loop
(`route_after_review`, `multi_wave_research.py`):

| Complexity | Base calls | Worst case (repair loop maxed) |
|---|---|---|
| SIMPLE | 2–3 | same — `max_review_iterations=0`, no repair loop possible |
| MODERATE | 2–3 | up to 5 (one repair pass adds +synthesize+review) |
| COMPLEX | 2–3 | up to 7–9 (2 repair iterations, plus up to 1 inline synthesis-schema retry per pass) |

Separately, the escalation-check suggestion (`POST /research/escalation-check`,
D7) runs its own uncached planner call *before* any of the above, since it
classifies the query independently of whether the user accepts the
suggestion.

### Performance

- **Concurrent worker lanes, fixed 2026-07-24 (D2).** `research_runtime_main.py`
  now opens `settings.research_runtime_worker_concurrency` DB sessions and runs
  that many `ResearchRuntimeWorker.run()` loops concurrently (default `1`,
  unchanged out of the box). The claim query (`SELECT ... FOR UPDATE SKIP LOCKED`)
  was already safe for multiple worker *processes*, so operators can also just
  run more copies of the process/container -- both knobs compose. Global
  load-shedding (`deep_research_max_queued_runs`, `503` on `/proposals/{id}/approve`
  once saturated) bounds how deep the queue is allowed to grow either way.
  **Still true at the default config**: with concurrency left at `1`, Deep
  Research runs are processed one at a time, 1-second poll interval between
  claims -- raising throughput is now a config change, not a code change.
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
  `test_review.py`). **Re-confirmed 2026-07-24**: the user asked why Deep
  Research "doesn't seem to cache" — this is that fix working as intended,
  not a bug. `CachePolicy.NEVER` means Deep Research's synthesis/review calls
  never hit the cache at all (by design, to prevent a semantic-cache hit from
  substituting a *different* run's prose into this run's report); only
  Linear Research's answer generation is cache-eligible. No code change.
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
| ~~D2~~ | ~~Single serial worker process — no horizontal scaling configured by default~~ — **Fixed 2026-07-24**: `apps/worker/research_runtime_main.py` now runs `settings.research_runtime_worker_concurrency` concurrent claim lanes in-process (each its own DB session), and running more copies of the process/container composes with that since the Postgres outbox (`SELECT ... FOR UPDATE SKIP LOCKED`) already made concurrent claims safe. Also added global load-shedding: `POST /proposals/{id}/approve` now checks `ResearchRunDispatchRepository.count_active()` against `settings.deep_research_max_queued_runs` (default 20) and returns `503` + `Retry-After` instead of queuing invisibly once saturated. Both are static config, not autoscaling — no automatic provisioning based on observed queue depth. The frontend-visible symptom (live event stream showing "Starting…" indefinitely while queued, indistinguishable from "about to start") is unchanged; a still-open cosmetic gap, not reopened here. | Resolved (residual: static config, not autoscaling) |
| ~~D3~~ | ~~No rate limiting on proposal creation~~ — **Fixed 2026-07-23**: `POST /research/proposals` is capped at `deep_research_proposal_rate_limit_requests` (default 5/60s) per owner, checked before the planner runs. `POST /research/proposals/{id}/approve` — the more expensive action — has its own, stricter cap: `deep_research_approval_rate_limit_requests` (default 5 per `deep_research_approval_rate_limit_window_seconds`=600s) per owner, checked before run creation/dispatch. Both return `429` with `Retry-After` and never touch `ResearchProposalService` when limited. | Resolved |
| ~~D4~~ | ~~No mid-run *plan* editing / no plan-approval interrupt~~ — **Fixed 2026-07-24**: a new `await_plan_approval` graph node (`interrupt()`, positioned between `aggregate` and `synthesize`) gives the plan-approval checkpoint the same view/edit/reject-with-reason treatment report approval (D13) already had. `GET /research/runs/{id}/plan` exposes the gathered evidence and goal from the paused run's checkpoint; `POST /research/runs/{id}/plan-decision` approves (optionally with an edited `rewritten_goal` — the only plan field still safe to change once retrieval has already run for the original tasks) or rejects with a reason. Reached once per run — the automatic `REVISE_SYNTHESIS`/`RESEARCH_GAPS` repair loops bypass it on retries. New `AWAITING_PLAN_APPROVAL` lifecycle state; a new `goal_review` frontend stage between `running` and `report_review`. | Resolved |
| D5 | Report-approval decision has no timeout: a run can sit in `AWAITING_APPROVAL` forever if the user never responds — no expiry, no reminder event, no auto-reject after N hours/days. The run just occupies a `research_runs` row indefinitely. | Low-Medium |
| ~~D6~~ | ~~`report-decision` endpoint has no frontend consumer yet~~ — **Fixed 2026-07-23**: full frontend built (plan review, live-streaming run status, report-approval, PDF download). See the new Frontend subsection above for what's covered and the disclosed scope trims (citations panel, history replay). | Resolved |
| D7 | The Research UI's default (Linear-mode) submission path now `await`s a full escalation-check planner call *before* running Linear Research — a deliberate, explicitly-requested design (blocking, not parallel, so a rejected suggestion cleanly "continues" rather than racing an already-started answer). Net effect: the UI's fast path is no longer as fast as the raw `POST /research` API — every default submission pays for one extra uncached LLM call (~1-3s) it wouldn't otherwise need. Not a bug; a known, disclosed tradeoff. **Possible follow-up**: run the check in parallel with Linear Research instead of gating it, showing the suggestion banner alongside/after the answer rather than before it. | Known tradeoff |
| ~~D8~~ | ~~`DeepResearchBlock` only rendered the progress-step log while `stage === 'running'`~~ — **Fixed 2026-07-24**: the log now also renders (as a completed, non-pulsing list) in `report_review`, `done`, and `failed`. Frontend-only, `deep-research-block.tsx`. Found via user testing. | Resolved |
| ~~D9~~ | ~~PDF report References section printed `item.document_id` (a raw UUID) instead of `item.filename`~~ — **Fixed 2026-07-24**: one-line fix in `reporting/pdf.py::_append_references`, matching the two sibling call sites (synthesis/review prompts) that already used `.filename`. Regression-tested — the old test's evidence bundle had no `evidence` items, so it couldn't have caught this. Found via user testing. | Resolved |
| ~~D10~~ | ~~Linear and Deep Research never shared one conversation; History showed one row per question instead of per thread~~ — **Fixed 2026-07-24**: root cause was `activeConversationId` living only in `use-research.ts`, never learned from or contributed to by Deep Research calls, so every Deep Research proposal/run started a *new* `ResearchConversation` even though the schema (`ResearchRun`/`ResearchProposal`/`ResearchSession` all FK to `research_conversations`) already fully supported mixing both turn types. Fixed frontend-only via a new `onConversationLearned` callback threading the id both ways. No backend change needed. Found via user testing. | Resolved |
| ~~D11~~ | ~~Deep Research state was lost on page refresh~~ — **Fixed 2026-07-24**: `GET /research/conversations/{id}` now also returns `deep_research_runs` (new `ResearchRunRepository.list_for_conversation` + a proposal lookup per run); the frontend's new `hydrateFromConversation` reconstructs every turn and re-subscribes non-terminal runs to the live event stream from cursor 0 (replaying full history, not just the live tail). The active conversation is also now synced into the page URL so a plain refresh finds its way back, not just an explicit `?conversation=` link. Found via user testing. | Resolved |
| ~~D12~~ | ~~Rejecting a report raised `ResearchReportRejectedError`, which the execution service caught and marked the whole run `FAILED` — discarding a draft that had already passed review~~ — **Fixed 2026-07-24**: `await_report_approval` no longer raises on rejection; a new `route_after_report_approval` conditional edge routes straight to `END`, skipping only `persist_final_report` (the PDF-writing node). `draft`/`evidence_bundle`/`review` are plain, unreduced state channels already set by earlier nodes, so they survive regardless of which node the graph terminates at — the run still completes (`COMPLETED_WITH_LIMITATIONS`, `terminal_reason="report_rejected_returned_as_answer"`) and `publish_runtime_report` still runs, publishing the draft as a plain answer. The frontend renders that answer inline instead of a "failed" card. Found via user testing. | Resolved |
| ~~D13~~ | ~~Report approval was blind — no way to see or edit the draft before deciding~~ — **Fixed 2026-07-24**: new `ResearchDraftInspectionService` reads a paused run's LangGraph checkpoint directly (`channel_values["draft"]`/`["evidence_bundle"]`/`["review"]`) and a new `GET /research/runs/{id}/draft` endpoint exposes it (citations resolved to filenames, same as D9's fix; 409 if not `AWAITING_APPROVAL`). `ResearchReportDecisionRequest` gained an optional `edited_draft` (free-text fields only — citation ids/schema version/limitations are always carried over from the original, so an edit can never break citation integrity and needs no re-validation). On approval, the edit overwrites `state["draft"]` before both `persist_final_report` and `publish_runtime_report` read it, applying uniformly to the PDF and the plain-answer path. Found via user testing. | Resolved |

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
approvals. D2's fix (2026-07-24) added a genuinely global backstop
(`deep_research_max_queued_runs`, checked in `ResearchProposalService.approve()`),
so aggregate demand exceeding worker throughput now gets an explicit `503`
instead of an unbounded queue -- but it's a blunt total-depth cap, not
per-owner fair-share, so one owner's burst can still consume the whole
queue and get other owners' approvals shed.

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

### X5 — Session-state pronoun resolution (fixed 2026-07-25/26, all paths)

A real production bug, found live: a Deep Research follow-up using a
pronoun ("so how is magma related to it?") had nothing to resolve "it"
against, since nothing about the session's actual topic had ever been
persisted anywhere retrievable — the old `state_from_user_turn` only fired
on a narrow set of trigger phrases, not ordinary topic drift. Fixed with a
new `SessionStateUpdaterService`
(`app/ai/memory/session/state_updater.py`) that, after every Chat/Deep
Research turn, asks a cheap model to maintain one evolving, ≤300-character
SESSION memory sentence describing what the session is currently about,
upserted in place (`MemoryService.get_latest_session_state()`, a tag
lookup by `metadata["kind"]`) rather than appended as a growing pile of
snapshots. This benefits all three paths that read session memory context,
not just Deep Research, since it's the same `MemoryService.get_context()`
call each already makes.

---

## 5. Consolidated priority list

| Priority | ID | Fix |
|---|---|---|
| ~~✓~~ | X1 | **Done (2026-07-23)** — per-owner `ValkeyRateLimiter` now covers Chat, Linear Research, and Deep Research proposals/approvals/escalation-checks. Remaining: it's per-owner, not global — doesn't bound aggregate demand across many accounts against the single Deep Research worker (see D2). |
| ~~✓~~ | D6 | **Done (2026-07-23)** — Deep Research got a full working frontend (plan review, live SSE progress, report-approval, PDF download) plus the escalation-check suggestion flow. |
| ~~✓~~ | D1 | **Done (2026-07-23)** — synthesis/review generation calls moved off `CacheRuntime.RESEARCH` onto `CacheRuntime.REVIEWER` (`CachePolicy.NEVER`), eliminating the cross-run report-content leakage risk. Regression-tested. |
| ~~✓~~ | D8–D13 | **Done (2026-07-24)** — six gaps found via user testing of the Deep Research frontend: progress-step log disappearing after `running`, PDF citations showing raw UUIDs, Linear/Deep Research not sharing a conversation (and History fragmenting per-question as a symptom), Deep Research state lost on refresh, report rejection destroying the synthesized draft as a terminal failure, and report approval being blind with no preview/edit. All fixed and regression-tested; see each ID's row above for detail. |
| ~~✓~~ | D4 | **Done (2026-07-24)** — plan-approval got the same view/edit/reject-with-reason treatment report approval already had, via a new `await_plan_approval` graph interrupt positioned between `aggregate` and `synthesize`. See D4's row above for detail. |
| ~~✓~~ | D2 | **Done (2026-07-24)** — in-process worker concurrency (`research_runtime_worker_concurrency`, multiple claim lanes/DB sessions per process) plus global load-shedding on approval (`deep_research_max_queued_runs`, `503` + `Retry-After`). Still a manual/static config knob, not autoscaling. |
| 2 | D5 | Add an expiry/auto-reject path for runs stuck in `AWAITING_APPROVAL` (now also covers `AWAITING_PLAN_APPROVAL` — the same unwired `expire_stale_awaiting_approval` sweep handles both, still just missing a cron trigger) |
| 3 | D7 | Consider parallelizing the escalation-check with Linear Research instead of gating it, so the UI's default path isn't paying a mandatory extra LLM call in serial |
| 4 | L1 | Consider short-circuiting retrieval on an exact-cache hit for Linear Research (would need the cache lookup moved ahead of `_retrieve_and_build_context()`, a real flow change, not a config flip) |
| 5 | C1 | Product decision, not a bug: whether/when Chat should get retrieval grounding (already tracked elsewhere as a known gap) |
