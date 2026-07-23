# Remaining Work

**Last updated:** 2026-07-23
**Scope:** Consolidated, standalone punch list of everything not yet built or verified, as of the completion of the end-to-end single-agent Deep Research workflow (backend + frontend). This file exists so "what's left" doesn't have to be reconstructed by diffing `PROJECT_STATUS.md`, `AI_ENGINEERING_AUDIT.md`, `ROADMAP.md`, and `RESEARCH_RUNTIME_IMPLEMENTATION_TRACKER.md` against each other. Those documents remain the authoritative sources for *why* each item is the way it is; this file is the flat "next" list.

For the full loophole/flow inventory (including already-fixed items like D1's cache-leakage risk), see `PRODUCT_FLOWS_AND_GAPS.md`. For the fine-grained implementation checklist, see `RESEARCH_RUNTIME_IMPLEMENTATION_TRACKER.md`.

---

## High priority

1. **No horizontal worker scaling for Deep Research (D2).** Runs are dispatched to a single serial worker process via the Postgres transactional outbox (`SELECT ... FOR UPDATE SKIP LOCKED`). Under concurrent load, runs simply queue behind each other — there's no autoscaling, multi-worker coordination, or load-shedding story yet. Affects: `apps/worker/research_runtime_worker.py`, `apps/api/app/repositories/research_run_dispatch.py`.

2. **No timeout on `AWAITING_APPROVAL` (D5).** A run paused for report approval can sit indefinitely if the user never returns to accept/reject the report. There's no expiry, reminder notification, or auto-resolution (e.g. auto-approve after N days, or auto-cancel). Affects: `apps/api/app/ai/runtime/research/lifecycle.py`, `run_service.py`.

3. **Rate limiting is per-owner, not global.** `ValkeyRateLimiter` bounds any single user's request rate across Chat/Linear Research/Deep Research, but nothing caps aggregate demand against the single shared Deep Research worker. Combined with item 1, a burst of distinct users can still starve the worker even though no individual user exceeds their limit. Affects: `apps/api/app/infrastructure/rate_limiting.py`.

## Medium priority

4. **No plan editing or rejection before approval.** Once a plan is proposed, the user can only approve it or implicitly abandon it (never call approve). There's no UI or API to edit scope/tasks, or to explicitly reject with a reason, before a run is created. Affects: `apps/api/app/ai/runtime/research/proposal_service.py`, `apps/web/src/features/research/`.

5. **MCP / multi-agent orchestration remains out of scope.** The Research Runtime is a complete single-agent workflow; the broader multi-agent/MCP vision described in `ResearchMind-Roadmap-v2.md` (Phase 5) is intentionally deferred and not started.

6. **No dedicated run-history browser.** Past Deep Research runs are queryable via `GET /research/{id}` but there's no UI surface for listing/browsing a user's run history — the tracker marks this "Partial," not done.

## Lower priority / disclosed, not blocking

7. **Frontend documentation coverage gap in `STRUCTURE.md`.** `apps/web/src/features/` (where all Research frontend logic actually lives — `use-deep-research.ts`, `deep-research-block.tsx`, `escalation-suggestion.tsx`, etc.) is not itemized in `STRUCTURE.md`'s tree, a pre-existing gap predating this session. `FILES.md` has the authoritative per-file breakdown instead.

8. **`app/dependencies/`, `app/api/v1/`, `app/schemas/` are not itemized in `FILES.md`.** Same category as item 7 — a pre-existing, consistent gap across the whole document, not specific to any recent work.

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
