# Remaining Work

**Last updated:** 2026-07-24
**Scope:** Consolidated, standalone punch list of everything not yet built or verified, as of the completion of the end-to-end single-agent Deep Research workflow (backend + frontend) and a follow-up user-testing pass against that frontend (2026-07-24, six real gaps found and fixed — see below). This file exists so "what's left" doesn't have to be reconstructed by diffing `PROJECT_STATUS.md`, `AI_ENGINEERING_AUDIT.md`, `ROADMAP.md`, and `RESEARCH_RUNTIME_IMPLEMENTATION_TRACKER.md` against each other. Those documents remain the authoritative sources for *why* each item is the way it is; this file is the flat "next" list.

For the full loophole/flow inventory (including already-fixed items like D1's cache-leakage risk), see `PRODUCT_FLOWS_AND_GAPS.md`. For the fine-grained implementation checklist, see `RESEARCH_RUNTIME_IMPLEMENTATION_TRACKER.md`.

---

## High priority

1. ~~**No horizontal worker scaling for Deep Research (D2).**~~ — **Fixed 2026-07-24**: the Postgres outbox (`SELECT ... FOR UPDATE SKIP LOCKED`) was already safe for concurrent claimants; `apps/worker/research_runtime_main.py` now actually exploits that, running `settings.research_runtime_worker_concurrency` concurrent claim lanes in-process (each its own DB session, default `1`), and running more copies of the same process/container composes with it since claims are DB-coordinated. Load-shedding also landed: `ResearchRunDispatchRepository.count_active()` gates `POST /proposals/{id}/approve`, rejecting with `503` + `Retry-After` once `settings.deep_research_max_queued_runs` (default 20) PENDING/RUNNING dispatches are already queued, instead of an invisible unbounded queue. **Residual gap**: both concurrency and the queue cap are static config, not autoscaling — nothing watches queue depth and provisions more lanes/processes automatically; that remains a deploy-time/operator decision.

2. **No timeout on `AWAITING_APPROVAL` (D5).** A run paused for report approval can sit indefinitely if the user never returns to accept/reject the report. There's no expiry, reminder notification, or auto-resolution (e.g. auto-approve after N days, or auto-cancel). Affects: `apps/api/app/ai/runtime/research/lifecycle.py`, `run_service.py`.

3. **Rate limiting is per-owner, not global.** `ValkeyRateLimiter` bounds any single user's request rate across Chat/Linear Research/Deep Research. Combined with item 1's fix, aggregate demand is now bounded too (the `deep_research_max_queued_runs` load-shedding cap is global, not per-owner) — but it's a blunt total-queue-depth cap, not fair-share scheduling, so one owner's burst can still fill the queue and get other owners' approvals shed. Affects: `apps/api/app/infrastructure/rate_limiting.py`.

## Medium priority

4. **MCP / multi-agent orchestration remains out of scope.** The Research Runtime is a complete single-agent workflow; the broader multi-agent/MCP vision described in `ResearchMind-Roadmap-v2.md` (Phase 5) is intentionally deferred and not started.

5. **No dedicated run-history browser.** ~~Past Deep Research runs are queryable via `GET /research/{id}` but there's no UI surface for listing/browsing a user's run history~~ — **substantially addressed 2026-07-24**: `GET /research/conversations/{id}` now returns `deep_research_runs` alongside Linear turns, and the frontend's History sidebar (which already lists conversations, not individual questions) reconstructs the full Deep Research card — including a still-running or awaiting-approval run's live state — for any run that's part of a conversation thread. What's still missing: a dedicated cross-conversation view listing *every* run a user has ever started, independent of which conversation it's in (today's browsing path is "pick a conversation, see its runs," not "see all runs").

## Lower priority / disclosed, not blocking

6. **Frontend documentation coverage gap in `STRUCTURE.md`.** `apps/web/src/features/` (where all Research frontend logic actually lives — `use-deep-research.ts`, `deep-research-block.tsx`, `escalation-suggestion.tsx`, etc.) is not itemized in `STRUCTURE.md`'s tree, a pre-existing gap predating this session. `FILES.md` has the authoritative per-file breakdown instead.

7. **`app/dependencies/`, `app/api/v1/`, `app/schemas/` are not itemized in `FILES.md`.** Same category as item 6 — a pre-existing, consistent gap across the whole document, not specific to any recent work.

---

## Explicitly out of scope (decided against, will not be built)

- **Chat → Deep Research escalation.** Chat is intended to remain a standalone, fast conversational surface with no suggestion path into Deep Research. Do not confuse this with the Linear → Deep Research escalation *inside the Research interface* (`check_escalation()` + the frontend suggestion banner), which is a different surface and is built.

## Explicitly NOT remaining (recently closed, listed here to prevent re-litigating)

- D1 cache-leakage risk (cross-run cache pollution in review/synthesis) — fixed 2026-07-23, `cache_runtime=CacheRuntime.REVIEWER`.
- Report-approval human checkpoint — implemented 2026-07-23 (`AWAITING_APPROVAL` lifecycle state, `interrupt()`-based pause, `record_report_decision()`).
- Memory-aware planning (query rewriting from durable user/semantic/research memory) — implemented 2026-07-23.
- Live SSE event streaming in the Deep Research frontend (planning/checking-sources/etc. progress) — implemented 2026-07-23, replacing the earlier polling-only UI.
- Rate limiting across Chat, Linear Research, and Deep Research — implemented (per-owner; see item 3 above for the residual gap).
- **Browser click-through verification of the Deep Research golden path — done 2026-07-23.** Manually exercised end-to-end at `localhost:3000/research`: DEEP mode toggle, submitting a complex query, live SSE progress steps (planning → source search → evidence analysis → report draft → citation review → awaiting approval), the report-approval UI (Approve/Reject), and the completed state with a working PDF download. Two real bugs surfaced only through this manual pass and are now fixed: a long-lived worker session serving stale identity-mapped `ResearchRun` data across dispatches (aborted-transaction poisoning on failure, and a stale `report_decision` read after approval — see `apps/worker/research_runtime_worker.py`, `apps/api/app/ai/runtime/research/execution.py`). Not yet covered by this pass: the Linear → Deep Research escalation banner specifically (a different UI surface from the Deep Research tab tested here).
- **User-testing pass on the Deep Research frontend — six gaps found and fixed 2026-07-24** (see `PRODUCT_FLOWS_AND_GAPS.md` D8–D13 for full detail):
  - Progress-step log disappearing once a run left the `running` stage — now stays visible through `report_review`/`done`/`failed`.
  - PDF report citations showing raw document UUIDs instead of filenames — one-line fix in `reporting/pdf.py`.
  - Linear and Deep Research turns never sharing one conversation (History fragmenting one row per question was a symptom of this) — fixed by threading a learned `conversation_id` both ways between `use-research.ts` and `use-deep-research.ts`.
  - Deep Research state lost on page refresh — `GET /research/conversations/{id}` now also returns `deep_research_runs`; the frontend reconstructs and re-subscribes to any non-terminal run.
  - Report rejection discarding the synthesized draft as a terminal `FAILED` run — the graph now routes a rejection straight to `END` (skipping only the PDF-writing node), so the run still completes and still publishes the draft as a plain answer.
  - Report approval being blind (no way to see or edit the draft before deciding) — new `GET /research/runs/{id}/draft` (reading the paused run's LangGraph checkpoint) plus an optional, citation-safe `edited_draft` on the approval decision.
  - A seventh reported issue (Deep Research seemingly not caching) was investigated and found to already be D1's fix working as intended, not a bug — no change made.
  - User re-tested the full flow in the browser after these fixes and confirmed all six work correctly.
- **Plan-approval editing (D4) — implemented 2026-07-24.** A new `await_plan_approval` graph node (`interrupt()`, positioned between `aggregate` and `synthesize`) gives the plan-approval checkpoint the same view/edit/reject-with-reason treatment report approval already had, without discarding the retrieval work already done. New `AWAITING_PLAN_APPROVAL` lifecycle state, `GET /research/runs/{id}/plan` (reads the paused run's gathered evidence + goal straight out of the checkpoint, mirroring `ResearchDraftInspectionService`), `POST /research/runs/{id}/plan-decision` (approve — optionally with an edited `rewritten_goal`, the only plan field still safe to change once retrieval has already run — or reject-with-reason). Only reached once per run: the automatic `REVISE_SYNTHESIS`/`RESEARCH_GAPS` repair loops route straight back to `synthesize`, bypassing this checkpoint on retries. Rejecting ends the run `CANCELLED` (`terminal_reason="plan_rejected_by_user"`) without ever calling `synthesize` -- unlike a rejected *report*, there's no draft yet to publish as a plain answer. Frontend: a new `goal_review` stage between `running` and `report_review`, reusing the live SSE event stream (`research_awaiting_plan_approval`).
