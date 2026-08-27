# Implementation Gap Cross-Check — 2026-08-12

**Method:** four independent read-only passes, each re-verifying claims against
actual source (not against the documents' own line-number citations), covering:
(1) Wave 0 + Wave 1 items E1–E12 of `PRIORITIZED_ROADMAP.md` /
`EVALUATION_IMPLEMENTATION_TRACKER.md`, (2) Wave 1 items E13–E23 (the freshest,
mostly same-day 2026-08-12 work), (3) Wave 2–7 + the Guardrails table + the
parallel Deployment track (all "not started" future work — checked for silent
partial progress or stale premises), (4) cross-document consistency across
every other planning/status doc in the repo, plus a repo-wide grep for
undocumented stubs.

**Headline result:** every "✅ Done" claim in Wave 0 and Wave 1 (E1 through
E23) checked out exactly against live code — no regressions, no partial
wiring, no stale claims. `PRIORITIZED_ROADMAP.md` and
`EVALUATION_IMPLEMENTATION_TRACKER.md` are accurate as of this date. The real
gaps found are not in that shipped work — they're (a) other docs in the repo
that never caught up to it, (b) already-known issues that were written down
somewhere but never got a line item in the master roadmap sequence, (c) one
code-level stub whose justifying comment is now factually false, and (d) one
incorrect premise inside the roadmap's own Wave 3 entry.

---

## Table A — Stale / contradictory docs (say something the code now disproves)

**Status: all five fixed 2026-08-12**, same day as this audit.

| Doc | Claim | Reality | Fix applied |
|---|---|---|---|
| [`docs/evaluation/strategy.md`](evaluation/strategy.md) | "Current Status: Not Implemented... there is no evaluation logic in this codebase yet" | Flatly false — golden set (115 examples), Ragas scoring, CI wiring, dashboard, online scoring, LLM-judge (E1–E23) are all shipped and verified live | ✅ Header changed to "Superseded", points to `PRIORITIZED_ROADMAP.md`/`EVALUATION_IMPLEMENTATION_TRACKER.md` as canonical, rest of doc kept as historical record |
| [`docs/platforms/retrieval-platform.md`](platforms/retrieval-platform.md) | `**Status:** Planned` | Hybrid retrieval, RRF, reranking, metadata filtering are long-shipped (`PROJECT_STATUS.md` Milestone 2.7, `✅ Complete`) | ✅ Status header updated to `✅ Complete`, points to `PROJECT_STATUS.md` Milestone 2.7 |
| [`docs/platforms/indexing-platform.md`](platforms/indexing-platform.md) | `**Status:** Planned` | Same — Milestone 2.6, `✅ Complete` | ✅ Status header updated to `✅ Complete`, points to `PROJECT_STATUS.md` Milestone 2.6 |
| [`docs/PROJECT_STATUS.md`](PROJECT_STATUS.md) | Last updated 2026-07-26; "Evaluation Platform Expansion" section still frames eval purely as `benchmarks/` NDCG/Groundedness metrics | Predates essentially all of Wave 0/Wave 1 (owner_id fix, citation validator, online scoring, dashboard, E1–E23) | ✅ Header timestamp bumped to 2026-08-12 with a summary of what shipped; inline "Superseded — see `PRIORITIZED_ROADMAP.md`" note added to the stale "Evaluation Platform Expansion" entry, matching this doc's existing convention for superseded entries elsewhere in the file |
| [`docs/AI_ENGINEERING_AUDIT.md`](AI_ENGINEERING_AUDIT.md) §5 P4 item 24 | "No proposal rejection/expiry, and no plan-edit-before-approval... still fully open" | Half-stale: plan-approval editing (D4, `await_plan_approval`) shipped 2026-07-24, predating this claim. Only the proposal-level rejection/expiry-before-a-run-exists half is still genuinely open | ✅ Claim split — plan-edit-before-approval marked shipped (2026-07-24, D4) with strikethrough on the outdated half; the still-open proposal-rejection/expiry half stated explicitly, cross-referenced to Table B below |

## Table B — Real, already-documented-somewhere gaps with no `PRIORITIZED_ROADMAP.md` line item

**Status: all triaged into the roadmap 2026-08-12.**

None of these were new discoveries — each was written down in some other doc
(`REMAINING_WORK.md`, `PRODUCT_FLOWS_AND_GAPS.md`, `AI_ENGINEERING_AUDIT.md`,
or a standalone `docs/todo/*.md`) but never made it into the canonical
Wave 0–7 sequence. Each now has a home: either a scored Wave line item, or
an explicit placement in the new "Engineering hygiene backlog" /
Deployment-follow-on sections.

| Gap | Source doc | Where it landed |
|---|---|---|
| Deep Research rate limiting is per-owner + total-queue-depth, not per-owner fair-share | `REMAINING_WORK.md` item 3 | ✅ New Wave 2 line item ("per-owner fair-share") |
| No cross-conversation Deep Research run-history browser | `REMAINING_WORK.md` item 5 | ✅ New Wave 2 line item |
| Paper Search MCP client's production-hardening deferred (JWT service-token auth, retry-with-backoff, 9-category error taxonomy, request-ID propagation, other 5 MCP tools) | `REMAINING_WORK.md` item 8 (ADR-037) | ✅ Explicit follow-on note added under "Parallel track — Deployment" |
| Retrieval (embedding + Qdrant) runs on every `/research` call even when the eventual answer will be a cache hit | `PRODUCT_FLOWS_AND_GAPS.md` L1 | ✅ Added to "Engineering hygiene backlog" as not-yet-Wave-scored (its own todo doc says it needs investigation first) |
| Linear Research's default path blocks on an uncached escalation-check LLM call before running | `PRODUCT_FLOWS_AND_GAPS.md` D7 | ✅ New Wave 2 line item ("parallelize the escalation-check call") |
| No user- or admin-facing cost dashboard, no per-user monthly cap | `PRODUCT_FLOWS_AND_GAPS.md` X2 | ✅ New Wave 2 line item, explicitly cross-referenced to Wave 7's dormant `BudgetGuardrail` wiring to avoid two competing enforcement paths |
| Proposal-level rejection/expiry before a run even exists | `AI_ENGINEERING_AUDIT.md` §5 P4 #24 (still-open half, per Table A) | ✅ New Wave 2 line item |
| Query-rewriting/condensation before retrieval, `AppException` inheritance for AI exceptions, JSON-logging prod bug, Gemini/Ollama timeout plumbing, CI coverage gate, multi-message provider API, generic tool-execution loop over `request.tools`, per-user concurrent-stream cap, L3 Session Cache wiring, native provider prompt-caching, Artifact-replay API routes, `record_retrieval()`/`record_agent()` call sites | `AI_ENGINEERING_AUDIT.md` §5, P0–P3 items 2,3,4,6,11,13,15,17,18,19,20,21 | ✅ Each individually re-verified against live code (not just re-read from the doc), then placed in a new dedicated "Engineering hygiene backlog" section with per-item Value/Ease and 2026-08-12 status. **One item changed since the audit was written**: Gemini/Ollama timeout plumbing is now Gemini-only — Ollama was independently fixed. **One item confirmed still literally broken, not just undone**: the JSON-logging bug — production still picks `ExceptionRenderer()` where the code's own docstring says `JSONRenderer()`. Two more items with their own standalone `docs/todo/*.md` files (L1 retrieval cache short-circuit, vector-indexing idempotency) were folded into the same backlog section for the same reason — real, confirmed-open, no Wave |

## Table C — Undocumented code-level gap found by grep

**Status: fixed 2026-08-12.**

| File:Line | Issue | Fix applied |
|---|---|---|
| [`apps/api/app/ai/artifacts/replay/research.py`](../apps/api/app/ai/artifacts/replay/research.py) | `ResearchReplayService.replay()` unconditionally `raise NotImplementedError(...)`; its docstring justified this by claiming "no Research Runtime exists yet to have persisted a ResearchArtifact" — false today, both the Research API Platform (Linear) and the Deep Research Runtime persist real `ResearchArtifact` records | ✅ Implemented for real rather than just fixing the comment: `ResearchReplayService` now takes a `ResearchArtifactReader` (the reader already existed, unused) and its `replay()` reads through it, mirroring `GenerationReplayService`/`StreamReplayService`'s exact shape. Missing-artifact case now correctly raises `ArtifactNotFoundError` (from the shared base reader) instead of the old blanket `NotImplementedError`. Tests rewritten in `tests/unit/ai/artifacts/replay/test_research.py` (write→replay roundtrip, optional-evaluation field, not-found case) — 8/8 passing. Still not wired to an API route, matching its two siblings — that remains open, tracked in Table B |

Everything else the grep surfaced (`toxicity.py`, `generation/moderation.py`,
`retrieval/access_control.py`, `input/rate_limit.py` guardrail stubs;
`app/ai/quality/*` empty scaffold packages; `app/ai/artifacts/{session,agent,evaluation}/*`
scaffold-only builders) matches documentation already in
`PRIORITIZED_ROADMAP.md` Wave 7 or prior audit notes verbatim — no action
needed, listed here only to confirm the grep was run and came back clean
beyond the one row above. No `TODO`/`FIXME`/`XXX` markers exist anywhere in
`apps/api/app/ai/`, `apps/api/app/api/`, or `apps/web/src/`.

## Table D — Incorrect premise inside `PRIORITIZED_ROADMAP.md` itself

**Status: fixed 2026-08-12.**

| Roadmap claim | Reality | Fix applied |
|---|---|---|
| Wave 3 note: the typed research-object domain model "is built inside the already-scaffolded-but-unused `artifacts/research` category — zero blast radius on anything live today" | **False.** `apps/api/app/ai/artifacts/research/models.py` (`ResearchArtifact`) is live production code. `apps/api/app/ai/research/service.py:837` calls `ResearchArtifactBuilder().build(...)` on **every** Linear Research (`/research`) request as a best-effort, policy-gated S3 audit-trail write (`plan.json`/`queries.json`/`retrievals.json`/`citations.json`/`report.json`) | ✅ Both the Wave 3 master-sequence table row and the Wave 3 narrative section in `PRIORITIZED_ROADMAP.md` rewritten: state the live write path explicitly with file:line evidence, and instruct that the typed model must be designed to either extend/wrap the existing writes, live alongside them as a separate category, or migrate them — decided up front, not discovered mid-implementation |

**Minor footnote (not a gap, no action needed):** Wave 4's Vision item
assumes zero existing scaffolding. In fact `apps/api/app/ai/runtime/generation/config.py`
already declares per-model `vision`/`multimodal_input`/`multimodal_output`
capability flags in the model catalog — but they're hardcoded `False` for
every model and nothing reads them outside `config.py`/`interfaces.py`. Dead
metadata, functionally inert, doesn't change Wave 4's scope or cost.

---

## Verification ledger — what was re-confirmed with no gap found

For completeness, everything below was independently re-checked against live
code (not just re-read from the docs) and found accurate. Full file:line
evidence lives with the auditing agents' reports; this is the roll-up.

| Area | Verdict |
|---|---|
| Wave 0 (6 items: `owner_id` required, `chunk.score` in `Citation`, draft-review.tsx rendering, LangSmith `owner_id` tag, Docling `do_ocr`, `ResearchReview.decision` in dashboard) | All confirmed, file:line evidence for each |
| Wave 1 E1–E12 (golden set, CI wiring, `POST /feedback`, citation validator, online scoring, trace attachment, dashboard, config fingerprint, segment analysis, promotion review, comment classification, ingestion fidelity) | All confirmed |
| Wave 1 E13–E23 (LLM-judge, latency-SLO alerts ×3 surfaces, cost forecast, LangSmith dataset registration, CI live-service triggers + 3 absolute gates, frontend thumbs-up/down ×3 surfaces, LangSmith `create_feedback()` mirror, tool-invocation metric) | All confirmed, including the E23 Linear Research exclusion (verified by absence of any web-search code path, not just by doc assertion) |
| Wave 2 (user-profile memory read-side, Socratic Challenger, preference→memory write, reject-with-revise, live cost/token events, HITL on memory deletion + document-delete) | Confirmed still fully not-started, matching roadmap |
| Wave 3 (Project schema, workspace UI, "@document" mentioning) | Confirmed still fully not-started (domain-model container premise error is separately flagged in Table D) |
| Wave 4 (Vision — attachments, image-to-RAG, charts) | Confirmed still fully not-started (dead capability-flag footnote above, no scope impact) |
| Wave 5 (Graph RAG, Canvas) | Confirmed zero existing graph store/entity extraction/canvas code |
| Wave 6 (Voice) | Confirmed zero STT/TTS dependency anywhere |
| Wave 7 Guardrails table (toxicity, moderation, access control, approval gate, runtime-stage wiring, rate-limit stub, prompt-injection/PII) | Every row's claimed current state confirmed accurate, including that `evaluate_runtime()` is genuinely never called from either production call site |
| Parallel Deployment track (AWS ECS Fargate) | Confirmed zero Dockerfiles/Terraform anywhere in repo |
| `docs/todo/user-memory-profile-injection-gap.md` | Still open, confirmed |
| `docs/todo/vector-indexing-idempotency-gap.md` | Still open, confirmed (`uuid4()` random IDs, no deterministic UUIDv5 scheme) |
| `docs/todo/l1-retrieval-cache-short-circuit.md` | Still open, confirmed |
| `docs/todo/aws-ecs-fargate-production-deployment.md` | Still open, confirmed |

---

## Suggested next actions

1. ~~Fix the five stale docs in Table A (mostly status-header edits, cheap).~~ **Done 2026-08-12.**
2. ~~Correct `PRIORITIZED_ROADMAP.md`'s Wave 3 premise (Table D) before anyone
   starts the typed domain-model work.~~ **Done 2026-08-12.**
3. ~~Fix or remove the false docstring on `ResearchReplayService.replay()`
   (Table C).~~ **Done 2026-08-12** — implemented for real against
   `ResearchArtifactReader`, not just a comment fix; see Table C.
4. ~~Triage Table B's items into the Wave sequence (or explicitly mark
   out-of-scope).~~ **Done 2026-08-12** — 5 items became new Wave 2 line
   items, 1 became a Deployment-track follow-on note, 12 (+2 standalone
   todo docs) became a new "Engineering hygiene backlog" section in
   `PRIORITIZED_ROADMAP.md`, each individually re-verified against live
   code rather than trusted from the original audit text. See Table B.

All four suggested actions from this report are now closed. This document
stays as the dated record of what the 2026-08-12 audit found and fixed;
`PRIORITIZED_ROADMAP.md` is once again the single up-to-date source for
what's next.
