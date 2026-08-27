# Memory Platform — Cross-Document Gap Analysis

**Status:** point-in-time audit, not a replacement for the living docs below.
**Date:** 2026-08-26
**Inputs reconciled:** [`PRIORITIZED_ROADMAP.md`](PRIORITIZED_ROADMAP.md),
[`MEMORY_MANAGEMENT_SUMMARY.md`](MEMORY_MANAGEMENT_SUMMARY.md),
[`MEMORY_PLATFORM_PRIORITIZED_TASKS.md`](MEMORY_PLATFORM_PRIORITIZED_TASKS.md),
[`PHASE_2_3_ROADMAP.md`](PHASE_2_3_ROADMAP.md), all last reconciled 2026-08-17
and re-checked against the source tree on 2026-08-26.

## 1. Are the four documents aligned?

**Yes.** There is a single, consistent chain of authority and no
contradictions found:

- `MEMORY_PLATFORM_PRIORITIZED_TASKS.md` is the source of truth for task IDs
  (M0–M16) and acceptance criteria.
- `MEMORY_MANAGEMENT_SUMMARY.md` mirrors that backlog's status in
  architecture/orientation form (tables, diagrams) — every status word
  ("Complete", "Implemented; rollout pending", "Partial") matches the backlog
  doc exactly, task for task.
- `PRIORITIZED_ROADMAP.md` places the memory backlog at Wave 2 (production
  hardening + Projects isolation) and explicitly defers to the backlog doc
  for status rather than re-deriving it ("Use the memory backlog rather than
  this section's older rationale to determine implementation status").
- `PHASE_2_3_ROADMAP.md` also defers status to the backlog doc and adds one
  scope guardrail not restated elsewhere: **do not expand USER memory into a
  separate `HumanInsight` domain model** — that belongs to Wave 3's typed
  research-object work, not to the memory platform.

No stale cross-references or conflicting completion claims were found across
the four documents as of 2026-08-17.

## 2. Spot-check against the source tree (2026-08-26)

To verify the docs' claims aren't aspirational, the following were confirmed
live in code rather than taken on faith:

| Claim | Verified |
|---|---|
| M3 recurring lifecycle worker exists | ✅ `apps/worker/memory_lifecycle_main.py`, `memory_lifecycle_worker.py` |
| M7 migration `f5a6b7c8d9e0` (memory feedback/correlation) | ✅ `alembic/versions/f5a6b7c8d9e0_add_m7_memory_feedback_and_correlation.py` |
| M14/M15 migration `c8d9e0f1a2b3` (governance jobs) | ✅ `alembic/versions/c8d9e0f1a2b3_add_memory_governance_jobs.py` — **exists in the repo but is not confirmed deployed to any environment**, matching the docs' "deploy migration" open item |
| M5 `Project`/`ProjectMembership` foundation, not a full Project product | ✅ `apps/api/app/models/project.py`, `apps/api/app/services/project_authorization.py` — minimal, matches "foundation only" framing |
| M5 scope threaded into storage | ✅ `project_id`/scope params present throughout `apps/api/app/ai/memory/storage/postgres_store.py` |
| M6 evaluation harness exists | ✅ `benchmarks/memory/{benchmark,dataset,runner,capture,metrics,results,answer_utility,persist_scores}.py` plus matching unit tests |
| M14 published backup-expiry policy | ❌ **Not found.** No standalone backup/retention policy document exists; only the three memory docs *mention* that one is still owed |
| M16 dependency-backed load/failure test suite | ❌ **Not found.** No `test_memory_*load*` / `*scale*` / cross-store failure-injection suite beyond the existing deterministic hardening tests |

Everything the docs claim as "Complete" or "Implemented" checked out. Every
item flagged as an open operational gate (deploy a migration, publish a
policy, run a staging drill, run a load test) is genuinely absent from the
repo, not just unlinked from these docs — i.e., the docs are not overstating
progress.

## 3. Task-by-task status (from the authoritative backlog)

| Task | Status | What's actually done | What's still missing |
|---|---|---|---|
| M0 | ✅ Complete | Feedback/memory transaction isolation, DB-failure test | — |
| M1 | ✅ Complete | SESSION newest-N-then-chronological fix | — |
| M2 | ✅ Complete | Write/delete rate limits, payload bounds, extraction circuit breaker | — |
| M3 | 🟡 Implemented, rollout pending | Worker, locking, batching, metrics, dry-run default | **Staging dry-run review + explicit production deletion enablement + monitored cadence** |
| M4 | ✅ Complete | Shared token budget across all 4 injection surfaces | — |
| M5 | ✅ Foundation complete | `scope_type`/`project_id` everywhere, membership authorization, backfill migration | **Full Project/workspace product (Wave 3) before project-scoped runtime traffic is activated** |
| M6 | 🟡 Implementation complete, calibration pending | Versioned dataset, Recall/Precision/MRR/nDCG, release gate logic, live-capture adapter | **Seed staging, capture first live baseline, human-calibrate judge vs. labels, turn live run into a deployment gate** |
| M7 | 🟡 Implemented, rollout pending | Memory-ID↔generation correlation, feedback signals, opt-in utility judge | **Deploy migration `f5a6b7c8d9e0`, verify feedback on staging, enable `MEMORY_ONLINE_UTILITY_JUDGE_ENABLED` after accepting cost** |
| M8 | 🟡 Implemented, gate pending | Bounded consolidation batch, typed judge decisions, reversible lineage, disabled+dry-run by default | **Reviewed sample of near-duplicate rates, gate rollout on M6 benchmark, enable in production** |
| M9 | 🟡 Implemented, calibration pending | Topic classification + complete-history candidate search, fail-open | **Staging sample proving dormant-preference recall without false positives; M6 v1.1 scenarios run for real** |
| M10 | 🟡 Implemented, calibration pending | Typed preference object, controlled namespace, deterministic supersession | **Calibrate controlled namespace + confidence threshold from real data** |
| M11 | ✅ Complete | Dashboard + alerts for size/growth/lifecycle/drift/budget/consolidation/utility | — |
| M12 | ✅ Complete | Scope-aware management API, two-user/two-project tests | — |
| M13 | 🟡 UI complete, product-integration gate pending | Full Personal/Project UI: filters, provenance, edit, move, export/erasure entry points, focus/keyboard behavior | **Verify a real Project-scoped request reflects a memory change once Wave 3 supplies authorized project context — this is a Wave 3 dependency, not unbuilt UI** |
| M14 | 🟡 Core shipped, operational acceptance pending | Export format, background erasure job, polling/retry UI, cross-store failure tests | **Deploy migration `c8d9e0f1a2b3`, publish + verify provider backup-expiry policy, run a real dependency-backed erasure drill, decide in-process-task vs. durable external queue at scale** |
| M15 | ✅ Complete | Server-authorized preview, hashed single-use 5-min confirmation token | — |
| M16 | 🟡 Deterministic hardening complete, scale evidence pending | Prompt-injection delimiting, quotas, provider failure-mode tests, 1,000-candidate budget test, cross-store retry regressions | **Dependency-backed load tests for large owner/project histories; staged failure injection against real Postgres/Qdrant/Valkey/artifact storage; environment-specific capacity thresholds** |

## 4. The real gaps, grouped by kind

### 4.1 Not missing code — missing operational evidence
This is the dominant category. M3, M6, M7, M8, M9, M10, M14, M16 are all
implemented in the sense that the logic, tests, and defaults exist — what's
missing is running them against staging/production and recording the
result:
- Deploy two outstanding migrations (`f5a6b7c8d9e0`, `c8d9e0f1a2b3`) to every
  environment that needs them.
- Run the M3 lifecycle worker in staging in dry-run, inspect real age/
  importance distributions, then flip on deletion deliberately.
- Seed the M6 dataset in staging and capture one real live-retrieval +
  paired-answer baseline; compare the judge against human labels.
- Turn on `MEMORY_ONLINE_UTILITY_JUDGE_ENABLED` after accepting the sampled
  OpenAI cost (M7).
- Review a real sample of M8 consolidation decisions before enabling
  mutation in production.
- Calibrate M9's topic-candidate recall and M10's confidence threshold from
  observed data, not defaults.
- Run a dependency-backed erasure drill (M14) and a load/failure-injection
  suite (M16) against real Postgres/Qdrant/Valkey — none of this exists yet
  in the test tree.
- Publish the M14 backup/retention-expiry policy as an actual document —
  today it's only referenced as "remaining" inside the three planning docs
  themselves, not written anywhere.

None of this is a code gap; it's a "someone needs to run this in a real
environment and sign off" gap, which is qualitatively different from an
unimplemented feature.

### 4.2 Genuinely blocked on other roadmap work (Wave 3)
M5's storage/authorization boundary is done, but two things stay dormant
until Wave 3 ships the real Project/workspace product:
- **M13's last acceptance line** — proving a Project-scoped memory change
  shows up in the next Project-scoped request — has no way to be exercised
  until Project creation, membership, and request-context resolution exist
  as a real runtime path (today's `Project`/`ProjectMembership` models are a
  minimal foundation, not the full product).
- Project-scoped memory writes from Chat/Research/Deep Research stay
  inactive; those surfaces still resolve personal scope only.

This is correctly sequenced in all four docs (Wave 3 is explicitly listed as
a dependency of, not a competitor to, M5) — it's a real gap, just not one the
memory team can close by itself.

### 4.3 Scope boundary — now restated in all four documents (fixed 2026-08-26)
`PHASE_2_3_ROADMAP.md` was the only one of the four documents stating a real
guardrail: USER memory must not be expanded into a separate `HumanInsight`
domain object — that belongs to Wave 3's typed research-object model
(`Knowledge`/`Evidence`/`HumanInsight`/`Hypothesis`). The concrete case it
protects is Wave 2's already-shipped Socratic Challenger node, which
currently writes a **plain `RESEARCH` memory note** (confirmed at
`apps/api/app/ai/runtime/research/execution.py:574`) as a deliberate MVP
placeholder, with explicit intent to upgrade it once Wave 3's domain model
exists.

This has been aligned: `MEMORY_MANAGEMENT_SUMMARY.md` §1 and
`MEMORY_PLATFORM_PRIORITIZED_TASKS.md`'s "Explicitly deferred" section now
both restate the same guardrail, and `PRIORITIZED_ROADMAP.md`'s existing Wave
2 note on the Socratic node now cross-references it explicitly. All four
documents agree: the upgrade path is Wave 3's typed `HumanInsight` object,
not organic growth of USER memory.

### 4.4 Not yet true gaps — explicitly deferred, no action needed
Per the backlog's own "Explicitly deferred" section, these are correctly
out of scope unless evaluation shows a concrete need, and should not be
read as missing work: full hot/warm/cold/archive tiering, generic episodic/
reflection memory, organization-wide or agent-shared memory, memory-driven
model/tool routing, and a standalone `memory_metrics.json` S3 artifact.

## 5. Remaining task list (priority order, per the backlog's own sequencing)

1. **M3 rollout** — staging dry-run review, then enable deletion + monitored
   production cadence.
2. **M6 calibration** — seed staging, capture live baseline, human-calibrate
   the judge, wire the live run into a staging deployment gate.
3. **M7 rollout** — deploy `f5a6b7c8d9e0`, verify feedback signals on
   staging, enable the online utility judge.
4. **M8–M10 calibration** — review consolidation false-merge samples, tune
   M9 candidate recall, calibrate M10's confidence threshold, all gated by
   the now-complete M6 harness.
5. **M13/M14 closing evidence** — deploy `c8d9e0f1a2b3`, publish the backup-
   expiry policy, run a real dependency-backed erasure drill, and (blocked on
   Wave 3) verify Project-scoped runtime effect.
6. **M16 scale/failure matrix** — dependency-backed load tests and staged
   failure injection against real Postgres/Qdrant/Valkey/artifact storage,
   then calibrate capacity thresholds per environment.
7. **Cross-roadmap dependency** — Wave 3's full Project/workspace model and
   authorized runtime context, which unblocks the last increment of M5/M13
   and (per §4.3) gives the Socratic Challenger note a proper typed home.

## 6. Bottom line

The memory platform's documentation is internally consistent and, on
spot-check, accurately reflects the code. There is no unimplemented M-task
hiding behind a green checkmark. The entire remaining backlog is one of two
kinds: **(a)** run-it-for-real operational evidence (staging drills, migration
deploys, policy publication, calibration) that cannot be produced by writing
more code, or **(b)** work explicitly blocked on Wave 3's Project/workspace
build landing first. Nothing here represents a design disagreement or a
missed requirement between the four documents.
