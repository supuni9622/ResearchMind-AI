# Memory Platform Prioritized Tasks

**Status:** Active backlog  
**Last reviewed:** 2026-08-17
**Next implementation task:** M14 export and bulk erasure; M3
and M6-M10 retain their separate operational rollout/calibration work.
**Scope:** `app/ai/memory/`, `/memory` APIs, runtime injection, storage,
evaluation, observability, lifecycle, governance, and upcoming Projects
integration.

This is the implementation backlog for making ResearchMind's memory system
bounded, measurable, useful, and safe to extend. It reconciles the current
source tree, `docs/architecture/memory-platform.md`, the platform review, and
the next-wave Projects requirement. The broader product sequence remains in
`docs/PRIORITIZED_ROADMAP.md`.

**Cross-roadmap contract:** this file is authoritative for memory task IDs,
acceptance criteria, and internal sequencing. `PRIORITIZED_ROADMAP.md` decides
product-wave placement; `PHASE_2_3_ROADMAP.md` preserves V2/V3 rationale; and
`NORTH_STAR.md` defines the long-term product model. M5 provides the required
storage and authorization foundation for Project-scoped memory writes, but it does not replace the broader Project
schema and typed research-object work in product Wave 3.

## Current baseline

USER-memory prompt injection is live across Chat, Linear Research, and both
Deep Research checkpoints. Preference feedback can create USER memory, exact
duplicates are updated, and M9 now nominates same-topic supersession candidates
from the owner's complete scope-safe history rather than only the 20 most
recent rows. The bounded, fail-open LLM judge remains overwrite authority.

M3's code path was implemented on 2026-08-17; staging/production rollout
evidence remains open. M12-M13 now provide a scope-aware management API and
complete Personal/Project Memory UI. M5's memory-platform foundation was
implemented on 2026-08-17; broader Project creation and workspace routing
remain product-wave work. The following are
ordered by dependency and operational risk.
"P0" means complete before characterizing the memory platform as production
scale. Tasks inside a phase are in recommended implementation order.

## P0 — Bound growth and close immediate correctness gaps

### M0. ✅ Isolate feedback-derived memory writes transactionally

**Completed:** 2026-08-12. `FeedbackService` now commits feedback and its
`eval_scores` mirror before invoking `PreferenceMemoryWriter`, which creates,
commits/rolls back, and closes a separate SQLAlchemy session. A real PostgreSQL
constraint-failure integration test proves a failed memory commit cannot undo
the canonical rows. Rating-only and objective-comment feedback never create
the extra session or invoke preference-memory supersession, preserving their
cost and latency path. The transactional outbox below remains a future upgrade
for retryability and moving preference-memory latency off the request path.

**Why now:** the staged feedback path calls `remember_extracted()` before the
feedback/eval-score commit and catches memory exceptions. Because both use the
same SQLAlchemy session, a database error can leave that transaction unusable;
catching the exception alone does not guarantee feedback submission can still
succeed. The current mock-based test does not exercise this transaction state.

**Chosen transaction boundary:** feedback and its mirrored `eval_scores` row
are canonical and must commit first. Preference-memory processing runs only
after that commit in a separately owned SQLAlchemy session/unit of work. A
savepoint is acceptable only as a short-lived patch; it is not the target
design because it retains memory latency and cross-store failure concerns in
the canonical feedback transaction.

Implementation sequence:

1. Commit feedback plus `eval_scores` in their existing transaction.
2. Open a new session for `remember_extracted()`; commit it independently and
   roll back only that session on failure.
3. Ensure feedback returns successfully when USER-memory supersession or
   PostgreSQL persistence fails. Feedback-derived USER memory does not use
   embeddings or Qdrant today; those failure cases belong to SEMANTIC/RESEARCH
   memory tests.
4. Record the failed memory attempt with enough non-sensitive identifiers for
   diagnosis and retry.
5. Move to a transactional-outbox design when reliable background memory jobs
   are introduced: save a `preference_memory_requested` event beside feedback,
   commit once, and let an idempotent worker classify/supersede/persist it.

- Do not reuse the request's SQLAlchemy session for the post-commit memory
  unit of work.
- Define an idempotency key from owner, generation, source, and policy version
  so retries cannot create duplicate memory.
- Add a database-backed test where the memory repository raises a flush/
  integrity error and prove feedback plus `eval_scores` still commit.
- Add failure tests for the LLM and Qdrant sides as well as PostgreSQL, and
  verify retrying the same event converges to one result.
- Measure the added classifier/supersession latency on the feedback endpoint;
  move nonessential memory work to a reliable async job if it harms UX.

**Done when:** a real database failure in preference persistence cannot poison
or roll back the canonical feedback transaction.

### M1. ✅ Fix SESSION context ordering

**Completed:** 2026-08-12. SESSION retrieval continues to return its newest
window oldest-to-newest. Formatting now selects the newest configured `N`
records from the tail while preserving that chronological order. SEMANTIC,
RESEARCH, and USER selection remain unchanged. This adds no storage reads,
sorting, tokens, provider calls, or model cost.

**Why now:** `get_recent()` returns the selected window oldest-first, while the
formatter takes the front of that list. When the list exceeds the formatting
cap, the newest entries are dropped.

- Define one ordering contract: storage returns chronological history for
  prompting, but the cap selects the newest `N` records.
- Fix the selection without reversing the final conversational order.
- Add tests with more entries than both the retrieval and formatting caps.

**Done when:** the newest `N` SESSION records are rendered oldest-to-newest and
the regression is covered at service and formatting boundaries.

### M2. ✅ Rate-limit all memory mutations

**Completed:** 2026-08-12. Public creates/updates share a configurable
owner-scoped `memory_write` bucket (default 30/minute); deletes use a separate
`memory_delete` bucket (default 10/minute). Public limiter uncertainty fails
closed before storage. Reads/searches do not consume either bucket. Request
schemas cap content (10,000 characters), encoded metadata (16 KiB), and
metadata depth (6). Accepted/rejected/failed mutations emit operation-labelled
metrics. Eligible background extraction has an independent owner-scoped
provider-cost circuit breaker (default 60/hour) that skips the LLM/write only
on a positive denial and fails open on Valkey outages so answers remain
available. Extraction output is also capped at 5 memories per turn to prevent
one malformed model response from amplifying writes. No new model calls were
added.

**Why now:** authenticated `POST`, `PUT`, and `DELETE /memory` operations are
currently unbounded.

- Reuse `ValkeyRateLimiter` and owner-scoped keys.
- Add separate configurable budgets for writes and destructive operations;
  do not count `GET /memory/context` or search against the write budget.
- Bound payload sizes and metadata size/depth at schema validation as a second
  line of defense.
- Add 429/retry-after and fail-open/fail-closed tests consistent with the
  existing Chat and Research rate-limit policy.
- Track accepted, rejected, and failed mutations by operation.

**Done when:** a single owner cannot create/update/delete memory above a
configured rate and normal extraction traffic is not accidentally throttled by
the public API budget. Internal extraction also needs its own per-owner
daily/hourly creation quota or circuit breaker.

### M3. 🟡 Put the lifecycle sweep on a real recurring execution path

**Implemented:** 2026-08-17. A dedicated worker runs bounded, type-specific
sweeps on a configurable cadence, defaults to dry-run, uses a token-safe Valkey
singleton lock, commits per row, and preserves the canonical PostgreSQL row
when Qdrant deletion fails so retries converge. Settings control cadence, lock
TTL, batch size, dry-run, and separate USER/SEMANTIC/RESEARCH age and importance
thresholds. Metrics cover examined/deleted/failed rows, duration, oldest
candidate age, and last success. Focused service/worker tests are green.

**Rollout pending:** run the worker in staging, inspect dry-run distributions,
then explicitly enable conservative deletion and production scheduling. M3 is
not marked complete until those operational acceptance criteria are observed.

**Why now:** `MemoryLifecycleService.sweep_stale()` is implemented, but nothing
runs it. Durable memory and Qdrant points therefore grow indefinitely.

- Add a small recurring-job entry point compatible with the deployed worker
  model (or use the deployment platform's managed scheduler to invoke a CLI
  job); document ownership, cadence, retries, and singleton locking.
- Move stale age, importance cutoff, batch size, and dry-run mode into settings.
- Process bounded batches with per-row failure isolation and idempotent retries.
- Delete PostgreSQL and Qdrant data coherently; record and repair orphaned
  index points instead of silently accepting partial cleanup.
- Emit examined/deleted/failed counts, duration, oldest row age, and last
  successful run time. Alert on missed or repeatedly failing sweeps.
- Start in report-only mode, inspect real age/importance distributions, then
  enable deletion with conservative, type-specific retention policies.

**Policy correction:** USER preferences should not inherit the same automatic
90-day low-importance deletion rule as transient facts without product
validation. Define retention independently for USER, SEMANTIC, and RESEARCH.

**Done when:** staging proves scheduled dry runs and deletions, production has
a monitored cadence, and repeated runs converge without Postgres/Qdrant drift.

### M4. ✅ Enforce one total memory-context token budget

**Completed:** 2026-08-17. All four injection surfaces continue through the
single shared formatter, which now enforces a configurable 1,200-token total
cap including headings, precedence instructions, and omission summaries. It
allocates explicit per-type shares, returns unused shares to a priority-ordered
common pool, selects whole entries, preserves newest chronological SESSION
state, and exposes omitted counts. An optional selected-model context window
tightens the cap after reserving configurable evidence and output space; the
fixed total remains the safe bound before routing resolves a model. The
deterministic estimator matches the existing input token-budget validator and
adds no provider calls. Selected/dropped tokens, omissions by bounded type, and
budget utilization are registered Prometheus metrics.

**Why now:** per-type item/character caps do not bound the combined prompt or
reserve room for document evidence and the response.

- Add a model-aware total token budget supplied by the Context Platform.
- Allocate explicit per-type shares with priority/fallback rules; do not rely
  on fixed concatenation alone.
- Select whole entries, account for headings/instructions, and expose omitted
  counts rather than truncating facts mid-sentence.
- Preserve a configurable minimum budget for retrieved document evidence and
  generation output.
- Record tokens selected/dropped by type and total memory share of context.

**Done when:** every runtime uses the same budgeted formatter and tests prove
the memory block cannot crowd out the reserved retrieval/output budgets.

## P0 — Define project isolation before Projects ships

### M5. ✅ Adopt an explicit memory-scope model

**Implemented:** 2026-08-17. Memory records and requests now use a validated
`personal`/`project` scope with nullable `project_id`. A migration backfills
legacy rows to personal scope, adds the composite lookup index, and introduces
the minimal Project/membership authorization foundation. SQL, Qdrant, Valkey,
deduplication, supersession, extraction, context caches, and S3 artifact paths
all carry the same scope. Project operations authorize membership before
touching memory, and project context can inherit personal USER defaults without
crossing into another project's memory.

The existing Chat, Research, and Deep Research entry points continue to resolve
personal scope because the Project/workspace request context has not shipped.
Their memory event and service plumbing accepts an authorized project scope so
the Projects wave can activate it without weakening the storage boundary.

Retrofitting scope after project data exists is both a migration risk and a
privacy boundary risk. Implement the contract before the Projects wave writes
production data.

Recommended scope policy:

| Memory type | Default scope | Cross-project behavior |
|---|---|---|
| SESSION | Project when the conversation belongs to a project; otherwise personal | Never implicitly searched across projects |
| USER | Personal/global | May be included in a project only when explicitly allowed; project-specific preferences remain project-scoped |
| SEMANTIC | Project when learned inside a project; otherwise personal | Never implicitly crosses project boundaries |
| RESEARCH | Project when the run belongs to a project; otherwise personal | Never implicitly crosses project boundaries |

Implementation tasks:

- Introduce a first-class scope (`scope_type` plus nullable `project_id`, or an
  equivalent validated scope object). Do not hide scope only in JSON metadata.
- Make repositories require `owner_id` **and** resolved scope for list, search,
  recall, update, delete, exact dedup, supersession, consolidation, and sweep.
- Put the same scope fields in Qdrant payload filters, SESSION/interest Valkey
  keys, idempotency keys, cache keys, metrics labels where cardinality is safe,
  and S3 artifact paths/metadata.
- Thread scope through extraction events, feedback-derived writes, Chat,
  Research, Deep Research, and all `/memory` request/response models.
- Make project membership authorization precede every project-scoped operation.
  A caller-provided project UUID alone is never authorization.
- Decide inheritance explicitly: a project request may combine global USER
  defaults with that project's memories, but must not search another project's
  memories. Current-turn instructions still win.
- Backfill existing rows as personal/global with a reversible migration. Add
  indexes beginning with `(owner_id, scope_type, project_id, type)` and update
  dedup/idempotency boundaries to include scope.
- Add adversarial integration tests using two users and two projects, covering
  SQL reads, vector retrieval, caches, exports, lifecycle jobs, and mutations.

**Done when:** cross-project retrieval is impossible by construction and test,
legacy rows have a documented scope, and every storage backend applies the same
authorization boundary.

Runtime inheritance must remain simple and visible:

```text
Personal request -> personal memory only

Project A request -> permitted personal USER defaults + Project A memory

Project B request -> permitted personal USER defaults + Project B memory

Project A memory -/-> Project B
```

## P1 — Make memory quality measurable

### M6. Build the memory evaluation harness and release gate

**Implementation complete; staging calibration pending:** 2026-08-17. M6 provides a strict,
versioned synthetic dataset and a captured-result scorer integrated with the
canonical `BenchmarkReport` model. It measures Recall@5, Precision@5, MRR,
nDCG@5, irrelevant/stale/contradictory/unsafe injection, latency, selected
tokens, and per-query evidence. An authenticated live API capture adapter,
paired memory-on/off LLM judge, and `eval_scores` persistence are implemented.
The deterministic contract runs in normal CI. Release gates reject any
scope/unsafe/stale/contradictory injection, Recall@5 below 0.8, average latency
above 500 ms, or average selected context above 1,200 tokens. Ground truth and
captured runtime output are deliberately separate.

Operational work remaining before M6 is closed: seed the versioned scenarios
in staging, capture the first live retrieval and paired-answer baseline,
compare judge scores with human labels, calibrate the provisional latency/token
budgets, and make the live run a staging deployment gate. CI cannot safely run
the authenticated live benchmark without a seeded environment and secrets.

- Create a versioned offline dataset covering exact recall, semantic recall,
  contradictory preferences, stale facts, no-relevant-memory cases, project
  isolation, and prompt-injection-shaped stored content.
- Measure Recall@K, Precision@K, MRR/nDCG where useful, irrelevant-injection
  rate, stale/contradictory-injection rate, and scope-leak rate (target: zero).
- Run paired answer evaluations with memory on/off: task correctness,
  personalization adherence, citation/evidence quality, and harm from
  irrelevant memory.
- Record retrieval candidates, selected memories, scores, policy version,
  budget decisions, and answer-level `memory_utility` in `eval_scores` or the
  established evaluation pipeline.
- Add latency and token/cost budgets and a CI/staging regression threshold.

**Done when:** caps, thresholds, retention, and consolidation changes can be
accepted or rejected using a repeatable benchmark rather than intuition.

### M7. Add online quality signals with safe sampling

**Implemented; rollout pending:** 2026-08-17. Chat, Linear Research, and Deep
Research now carry exact post-budget injected memory UUIDs into their
answer-producing generation metadata and persist them on `generation_usage`,
linking memory to generation and LangSmith run IDs without putting memory
content in metrics. Deep Research propagates its execution-time memory block
through synthesis so utility scoring measures the final report, not merely its
planner. Its durable session metadata preserves the final generation ID and
the safe memory-used flag for both approved PDF reports and rejected reports
published as plain answers, so either UI path can submit correlated feedback.
User-facing responses expose only a `memory_used` boolean. The shared
feedback control offers independent “Memory helped” and “Memory was wrong” signals,
stored owner-scoped in `memory_feedback` and mirrored to `eval_scores` as
`memory_user_signal`. The existing risk-weighted online scoring sample can run
an opt-in structured memory-utility judge and records `memory_utility` plus
`irrelevant_memory_harm` using categorical, non-content reasons.

Operational rollout: apply migration `f5a6b7c8d9e0`, deploy API/web and the
evaluation worker, verify explicit feedback on staging, and enable
`MEMORY_ONLINE_UTILITY_JUDGE_ENABLED=true` only after accepting its additional
sampled OpenAI cost. The judge uses the existing online sample rates.

- Correlate injected memory IDs with generation IDs and user feedback.
- Sample an LLM-as-judge memory-utility score: helpful, irrelevant, stale,
  contradictory, or unsafe.
- Track explicit "used memory" and "memory was wrong" feedback without
  interpreting a generic thumbs-down as proof that memory caused the problem.
- Avoid storing raw sensitive memory text in metrics/logs.

**Done when:** staging confirms owner isolation and trace correlation, sampled
scores have a human-reviewed calibration set, and utility/harm alerts have
enough traffic for meaningful thresholds.

## P1 — Improve quality and prevent semantic drift

### M8. Implement evidence-driven consolidation for SEMANTIC/RESEARCH

**Implemented; rollout/evidence gate pending:** 2026-08-17. The lifecycle
worker can now run a separately gated, bounded consolidation batch. Embedding
similarity only nominates same-owner/scope/project/type pairs; a structured
judge classifies each pair as duplicate, mergeable, contradiction, or
unrelated. Duplicate/mergeable sources remain in Postgres as reversible
lineage records while disappearing from normal reads, and the canonical vector
is updated before the source vector is removed. Failed vector or database
operations are compensated/rolled back. Contradictions are retained. The
feature defaults disabled and dry-run, with bounded outcome metrics for sample
review before mutation is enabled.

- First instrument near-duplicate candidate rates and build a reviewed sample;
  tune from observed data.
- Use embedding similarity only to nominate a small candidate set. Require a
  typed decision: duplicate, compatible/mergeable, contradiction/supersession,
  or unrelated.
- Preserve provenance, source timestamps, citations/research IDs, and a
  reversible lineage (`merged_from`/supersession relation). Never silently
  summarize away conflicting evidence.
- Consolidate in bounded background batches and re-index atomically enough to
  repair partial failures.
- Prefer update-in-place for a canonical memory where audit history is retained.
- Gate rollout by the M6 benchmark and monitor false merges.

**Done when:** durable growth and duplicate injection decrease without lowering
Recall@K, losing provenance, or merging contradictory findings.

### M9. ✅ Remove the USER supersession recency blind spot

**Implemented; rollout calibration pending:** 2026-08-17. New USER
preferences now receive a cheap structured topic classification containing a
stable `preference_key` and bounded search terms. PostgreSQL uses those hints
to nominate up to 20 matching preferences across the owner's complete history,
within the exact personal/project boundary; recency no longer determines
eligibility. The existing conservative supersession judge remains the only
component allowed to approve update-in-place. Its reason, replaced memory ID,
and decision timestamp are retained in metadata. Topic-classification or query
failure falls open to a five-item recent scan and never blocks memory creation.
M6 v1.1 adds dormant-old-preference and similar-but-distinct false-positive
scenarios.

- Give USER preferences a stable topic/key or embedding-assisted candidate
  lookup so old preferences on the same subject remain discoverable.
- Retrieve a bounded topically relevant set, not an unbounded owner profile.
- Keep fail-open behavior and audit the decision/replaced ID.
- Add dormant-old-preference and false-positive regression cases to M6.

**Done when:** a staging sample demonstrates that dormant same-topic
preferences are found while related-but-distinct preferences are retained,
with no owner/project leakage and no M6 retrieval regression.

### M10. ✅ Introduce typed preference attributes gradually

**Implemented; rollout calibration pending:** 2026-08-17. The M9 classifier
now emits a controlled kind (`response_length`, `tone`, `citation_style`,
`preferred_model`, `preferred_tool`, or `custom`), normalized typed value,
confidence, and explicit/inferred signal. USER metadata retains readable
content while adding a versioned `preference` object with source, effective
time, and bounded provenance. One uniquely matching, already-typed controlled
preference can be superseded deterministically when the new statement is
explicit and clears the confidence threshold. Custom, inferred, uncertain,
ambiguous, and legacy rows continue through M9's conservative judge. No typed
preference is used as a hard model/tool routing constraint.

Keep natural-language content for prompting, while adding optional normalized
fields such as `preference_key`, typed `value`, confidence, source, effective
time, and provenance. Begin with a small controlled namespace (response length,
tone, citation style, preferred models/tools) and retain `custom` for everything
else. Do not turn inferred interests into hard routing constraints.

**Done when:** common preferences can be deterministically superseded and
queried without breaking free-text memories or overclaiming uncertain inference.
Implementation satisfies this contract; staging calibration of the controlled
namespace and confidence threshold remains part of rollout.

## P1 — Operational visibility

### M11. ✅ Bring the dashboard and alerts up to date

- Add the staged `memory.superseded` signal to `memory-runtime.json`.
- Add absolute Postgres row counts by type/scope, estimated table/index bytes,
  Qdrant point counts, orphan/drift counts, oldest row age, and owner/project
  distribution percentiles. Avoid high-cardinality owner/project labels in
  Prometheus; use aggregate SQL panels or scheduled gauges.
- Add lifecycle last-success/deleted/failed panels and alerts.
- Add total context tokens, omitted-memory count, write throttles, consolidation
  outcomes, and memory-utility trends.
- Reconcile §21's aspirational metric list with the metrics actually emitted;
  either implement `memory_size`/`memory_count` or mark them accurately.

**Done when:** operators can answer "how large is memory, is it growing safely,
is cleanup running, and is memory helping?" without manual database queries.

Implemented 2026-08-17. The lifecycle worker now publishes a low-frequency,
bounded-cardinality inventory covering PostgreSQL rows/bytes/age/distribution,
Qdrant points and drift, plus collection freshness. The Memory Runtime
dashboard includes supersession, lifecycle, prompt-budget, throttle,
consolidation, and utility panels; stale lifecycle/inventory, lifecycle
failures, and vector drift have alerts. §21 now distinguishes emitted metrics
from historical aspirational names.

## P2 — User control and governance

### M12. ✅ Build the scope-aware memory-management API

**Completed 2026-08-17:** the management API enumerates every canonical durable
type with personal/project, project, type, source, date, and origin filters.
Responses expose a safe management projection rather than owner IDs/raw
metadata. All mutations authorize scope first; edits record explicit bounded
provenance, deduplicate, re-index vector memory, and invalidate caches. A
confirmed move endpoint validates both scopes and destination duplicates.
Per-scope capture/retrieval settings are independent from retention, and real
PostgreSQL tests cover two users/two projects and project membership.

- Add paginated `GET /memory` with filters for personal/project scope, project,
  type, source, created/updated dates, and inferred/explicit origin.
- Return user-safe fields: ID, content, type, scope, project reference, source,
  confidence when available, created/updated/last-used dates, and whether the
  record is editable. Do not expose internal prompts or sensitive diagnostics.
- Make `POST`, `PUT`, and `DELETE` scope-aware and authorize project membership
  server-side before repository access.
- Define edit semantics: user edits are explicit, keep audit provenance, update
  the canonical row, re-index vector-backed types, and invalidate relevant
  caches. An edit must not silently change scope.
- Add an explicit move/promote operation for changing project memory to
  personal memory or the reverse. Require confirmation and re-run relevant
  validation/deduplication in the destination scope.
- Add per-scope memory enable/disable settings. Disabling capture must not
  silently delete existing memory; retrieval and retention behavior must be
  separately stated in the UI/API contract.
- Apply mutation rate limits and payload limits from M2.
- Add two-user/two-project authorization and leakage integration tests.

**Done when:** an authorized client can safely enumerate, create, edit, delete,
and deliberately move memories within one resolved scope without accessing
another user's or project's records.

### M13. ✅ Complete the Personal Memory and Project Memory UI

**Completed 2026-08-17:** `/memory` is now a
first-class navigation destination. It lists durable USER preferences and
supports debounced server-side search, feedback-source filtering, pagination,
validated inline editing, a product-native confirmed deletion dialog, refresh,
and loading/error/empty states. A clearly disabled Project Memory section
states its M5 dependency. M13 replaces that placeholder with authorized project
selection, an explicit isolation boundary, persisted personal-inheritance and
capture switches, durable-type/origin/source/date filters, provenance and usage
metadata, review-before-edit, scoped JSON export, and selected-memory deletion.
M14 remains responsible for durable cross-store export/erasure jobs.

Add a first-class **Memory** area rather than hiding these controls inside chat.

Personal Memory view:

- Show durable personal preferences and permitted cross-project facts.
- Group or filter by preference, semantic fact, and research finding.
- Explain that personal defaults may be used in projects unless the user or
  project disables that inheritance.

Project Memory view:

- Show only memory belonging to the selected project.
- Make the active project and isolation boundary prominent.
- Explain when personal USER defaults are also inherited, with a project-level
  switch to disable that inheritance.

Both views must support:

- pagination, search, filtering, and useful empty/loading/error states;
- clear **Explicitly provided** versus **Inferred by ResearchMind** labels;
- source/provenance, confidence where meaningful, and last-used/updated dates;
- inline or modal editing with validation and a review of the final text;
- single-memory deletion with confirmation;
- scoped export and bulk-delete entry points;
- global personal-memory and per-project capture controls;
- accessible keyboard/focus behavior and responsive layouts.

Do not expose raw SESSION implementation entries as durable profile facts by
default. If session memory is shown, present it separately as temporary and
include its expiry.

**Done when:** a user can understand what ResearchMind remembers personally and
for the current project, correct it, remove it, and see the effect reflected in
the next eligible request.

### M14. Add export and bulk erasure

- Export all owner memory in a documented portable format, including scope and
  provenance but excluding internal secrets.
- Add "delete all my memories" and project-scoped deletion. Cover Postgres,
  Qdrant, Valkey SESSION/interest/idempotency keys, caches, and derived artifacts
  according to the product's retention policy.
- Make bulk deletion an idempotent, auditable job with progress and partial
  failure recovery; verify erasure across stores.
- Define how backups and immutable audit artifacts satisfy the published
  retention/erasure policy.

### M15. Require confirmation for destructive memory actions

- Add a preview/confirmation contract for single and bulk deletion, including
  affected scope/count and a short-lived confirmation token.
- Keep API authorization server-side; UI confirmation alone is insufficient.
- Decide whether a short undo/tombstone window is appropriate before physical
  erasure. Do not retain data contrary to an immediate-erasure request.

## P2 — Hardening and maintainability

### M16. Add safety, capacity, and failure-mode tests

- Stored prompt-injection content must be quoted/delimited as untrusted memory
  and never override system/current-turn instructions.
- Test unavailable Postgres, Valkey, Qdrant, embedding, and LLM providers;
  document which reads/writes fail open and which fail closed.
- Load-test large owner/project histories, context assembly, lifecycle sweeps,
  consolidation, export, and bulk delete.
- Add reconciliation tooling for Postgres/Qdrant drift and run it periodically.
- Establish per-owner/project memory quotas with explicit UX when reached.

## Explicitly deferred

These are not needed for a useful, manageable Projects-era memory system unless
evaluation demonstrates a concrete need:

- full hot/warm/cold/archive tiering;
- generic episodic or reflection memory;
- organization-wide and agent-shared memory;
- memory-driven model/tool routing;
- an S3 `memory_metrics.json` artifact when dashboards/eval records already
  provide the required operational history.

## Recommended delivery sequence

1. **Stability patch:** M0, M1, M2, dashboard supersession panel from M11.
2. **Bounded operations:** M3 implementation and M4 complete; M3 operational rollout remains.
3. **Projects prerequisite:** M5 isolation foundation complete; wire the full
   Project/workspace model and authorized runtime context before project-scoped
   production writes.
4. **Measurement:** M6, then M7.
5. **Quality:** M8–M10, each gated by evaluation results.
6. **User control:** retain the shipped personal M12/M13 slice; after the
   Project product activates M5's scope boundary, complete the Project Memory
   behavior, then M14–M15
   export/erasure before broad external rollout.
7. **Ongoing hardening:** M16 load, failure-mode, prompt-safety, and capacity work.
