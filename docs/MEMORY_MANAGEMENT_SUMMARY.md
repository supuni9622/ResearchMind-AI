# ResearchMind Memory Management Summary

**Status:** Living architecture and delivery summary  
**Last reconciled:** 2026-08-17  
**Implementation progress:** M0-M2, M4-M5, M11-M12, and M15 are
acceptance-complete. M3 and M6-M10 are implemented with rollout/calibration
gates. M13's UI affordances are implemented with Project-runtime verification
pending. M14 has background execution, polling/retry, limits, metrics, and
cross-store retry regressions; backup policy and dependency-backed staging
evidence remain. M16 hardening is partial.

This document explains the existing and planned ResearchMind memory platform in
one place. It is an orientation document, not a replacement for the accepted
[memory architecture](architecture/memory-platform.md), the executable
[prioritized task list](MEMORY_PLATFORM_PRIORITIZED_TASKS.md), or the
[manual regression guide](MEMORY_MANUAL_TEST.md).

Status and ordering follow
[the prioritized memory backlog](MEMORY_PLATFORM_PRIORITIZED_TASKS.md). The
repository-wide wave placement follows
[the prioritized roadmap](PRIORITIZED_ROADMAP.md). The Phase 2/3 roadmap and
North Star supply rationale and long-term domain direction; they do not
override memory acceptance criteria. M5's isolation foundation is now in place,
while the full Project schema remains the Wave 3 anchor for
typed research objects and Research Paths.

## 1. Goals and non-goals

ResearchMind memory should make later answers more useful without silently
turning every conversation into permanent data. The production design is guided
by five outcomes:

1. Preserve useful session state, durable preferences, facts, and research
   findings.
2. Keep memories isolated by owner and, before Projects launches, by project.
3. Bound storage, prompt tokens, write volume, latency, and model cost.
4. Let users see, correct, export, and delete what ResearchMind remembers.
5. Measure whether memory improves answer quality and detect regressions before
   release.

Full archival tiers, reflection/episodic memory, organization-wide shared
memory, agent memory, and memory-driven request routing are explicitly deferred.

## 2. Executive status

| Area | Existing today | Planned target |
|---|---|---|
| Memory types | SESSION, USER, SEMANTIC, RESEARCH with explicit personal/project scope | Activate project scope from Project-aware runtimes |
| Session state | Scope-safe Valkey keys, seven-day TTL, compact state by default | Capacity telemetry and tested expiry behavior |
| Durable storage | PostgreSQL canonical rows; Qdrant vector index; recurring lifecycle worker; reversible consolidation; scheduled drift inventory | Enable deletion after rollout evidence; add quotas and reconciliation repair tooling |
| Capture | Post-turn extraction, repeated-interest promotion, feedback preferences, complete-history topical supersession, and versioned typed preferences | Calibrate extraction/supersession thresholds |
| Retrieval | Four product surfaces share one coordinated token budget; scope-safe services are implemented | Activate authorized project context in Project-aware runtimes |
| Write safety | Legacy mutation limits and payload bounds; internal circuit breaker; throttle metrics and alerts | Apply destructive limits to M14 preview/job/retry routes; per-plan quotas and load tests |
| Feedback safety | Canonical feedback commits before isolated memory write | Durable outbox only if delivery guarantees justify it |
| User controls | M12 scope-safe API plus implemented M13-M15 Personal/Project UI, portable export, and server-confirmed erasure foundation | Move/retrieval/end-date UI, complete dialog focus behavior, job recovery UI, cross-store integration evidence, backup-expiry policy |
| Lifecycle | Recurring, batched, locked worker implemented; report-only by default | Validate staging dry runs, enable conservative deletion, and monitor production cadence |
| Quality | M6 offline benchmark plus M7 generation correlation, explicit feedback, and opt-in sampled utility/harm scoring | Staging calibration and enforced deployment gates |
| Observability | M11 dashboard/alerts for absolute size, growth, drift, lifecycle, tokens, throttles, consolidation, and utility | Production threshold calibration and notification routing |

## 3. Memory model

| Type | Purpose | Canonical store | Retention today | Retrieval behavior |
|---|---|---|---|---|
| SESSION | Active conversation state and compact summaries | Valkey | Seven-day TTL | Newest capped tail, displayed oldest-to-newest |
| USER | Durable preferences and user-specific facts | PostgreSQL | Indefinite | Recent active preferences, exact dedup, supersession |
| SEMANTIC | Reusable facts and topics | PostgreSQL | Indefinite | Qdrant similarity search with threshold |
| RESEARCH | Durable findings with research provenance | PostgreSQL | Indefinite | Qdrant similarity search with threshold |

PostgreSQL is authoritative for durable memory. Qdrant is a derived search
index, not a second source of truth. Valkey owns ephemeral session state and
short-lived extraction/rate-limit counters. S3 memory artifacts are best-effort
audit evidence and are not canonical storage.

Raw turn storage is disabled by default. Compact session state is enabled. This
reduces storage and prompt cost while avoiding unnecessary retention of full
conversation text.

## 4. Existing architecture

```mermaid
flowchart LR
    U[User request] --> S[Chat or Research surface]
    S --> C[Memory context service]
    C --> V[(Valkey<br/>SESSION)]
    C --> P[(PostgreSQL<br/>USER and canonical durable rows)]
    C --> Q[(Qdrant<br/>SEMANTIC and RESEARCH index)]
    C --> B[Bounded memory block]
    B --> M[Model request]
    M --> A[Answer]
    A --> E[Eligible post-turn extraction]
    E --> V
    E --> P
    E --> Q
    S -. best-effort audit .-> O[(S3 artifacts)]
```

Memory injection is active in:

- Chat.
- Linear Research.
- Deep Research proposal generation.
- Deep Research execution.

All memory content is untrusted context. It can inform an answer but must not
override the current user instruction, authorization checks, or system policy.

## 5. Existing capture and write flows

### 5.1 Post-turn extraction

```mermaid
flowchart TD
    T[Completed eligible turn] --> G{Deterministic eligibility}
    G -- trivial or one-off --> X[Skip]
    G -- repeated topic --> I[Valkey distinct-session counter]
    I --> J{Promotion threshold reached?}
    J -- no --> X
    J -- yes, once --> L[Extraction model]
    G -- explicit preference or finding --> L
    L --> N[Validate and cap at 5 memories]
    N --> D{Exact duplicate?}
    D -- yes --> R[Update existing evidence/importance]
    D -- no --> Y{USER preference?}
    Y -- yes --> W[Classify topic and query scope-safe historical candidates]
    Y -- no --> Z[Store canonical row]
    W --> Z
    Z --> Q{Vector-backed type?}
    Q -- yes --> P[Upsert Qdrant point]
    Q -- no --> K[Done]
    P --> K
```

An internal per-owner extraction circuit breaker currently permits 60 eligible
extraction calls per hour by default. A confirmed denial skips both the model
call and memory write. Valkey failure is fail-open for this internal optimization
so the main answer flow remains available. Extraction output is capped at five
memories per turn.

USER supersession classifies a stable preference key and bounded search terms,
then queries up to 20 topic-relevant candidates across the complete authorized
personal/project history. Classification or query failure falls back to five
recent items and never blocks creation. A conservative second model call alone
can approve update-in-place, with the replaced ID, reason, and timestamp kept
as audit metadata.

### 5.2 Feedback-derived preferences (M0 complete)

```mermaid
flowchart TD
    F[Feedback request] --> C[Classify rating, objective, or preference]
    C --> DB1[Transaction A: store feedback and user_rating eval score]
    DB1 --> COMMIT[Commit canonical feedback]
    COMMIT --> P{Preference feedback?}
    P -- no --> OK[Return success]
    P -- yes --> DB2[Transaction B: independent SQLAlchemy session]
    DB2 --> MW[Create or deduplicate USER memory<br/>source=feedback]
    MW --> MC[Commit memory transaction]
    DB2 -- failure --> RB[Rollback memory transaction]
    RB --> LOG[Log feedback.preference_memory_failed]
    MC --> OK
    LOG --> OK
```

The separate transaction is the essential production invariant: memory failure
cannot poison or roll back the already committed feedback and evaluation score.
This is intentionally fail-open for the optional memory side effect. A durable
outbox remains a future option if guaranteed eventual memory delivery becomes a
business requirement.

### 5.3 Public mutation protection (M2 complete)

The public `POST /memory` and `PUT /memory/{id}` operations share a per-owner
`memory_write` limit of 30 requests per minute by default. `DELETE /memory/{id}`
uses an independent limit of 10 requests per minute. Confirmed over-limit
requests return `429` with `Retry-After`. Reads, context assembly, and search do
not consume mutation quota.

Memory content is limited to 10,000 characters. Encoded metadata is limited to
16 KiB and nesting depth six. Accepted, rejected, and failed mutation outcomes
are emitted with bounded operation labels. Public limiter dependency failures
fail closed to prevent unbounded writes.

## 6. Existing retrieval and prompt assembly

```mermaid
flowchart TD
    R[Chat or Research request] --> O[Resolve authenticated owner]
    O --> S1[Load SESSION tail from Valkey]
    O --> U1[Load active USER preferences from PostgreSQL]
    O --> V1[Search SEMANTIC and RESEARCH in Qdrant]
    V1 --> H[Hydrate/validate canonical PostgreSQL rows]
    S1 --> F[Format by type]
    U1 --> F
    H --> F
    F --> C[Apply per-type shares and one total token cap]
    C --> B[SESSION then USER then SEMANTIC then RESEARCH]
    B --> P[Prompt: current instruction remains authoritative]
```

Each type retains an item cap of five. SEMANTIC and RESEARCH results use vector
similarity thresholds. On-demand memory search can combine type results; normal
context assembly preserves deterministic type order. M4 applies one coordinated
budget to the complete memory block, including headings, precedence text,
whole-entry selection, and omission reporting; entries are omitted intact
rather than truncated mid-fact.

The SESSION ordering defect is fixed (M1): cap selection chooses the newest
items, then renders that selected window chronologically. Older messages are not
allowed to displace newer state merely because presentation order is ascending.

## 7. Existing APIs and user controls

Existing endpoints support creating memory, searching, assembling context,
scope-aware read/update/delete/move operations, and bounded paginated durable
memory inventories. The frontend provides Personal and authorized Project
views with search, type/source/origin/date filters, edit review, capture and
inheritance controls, portable export, and server-confirmed selected or
full-scope erasure.

Owner checks must be enforced server-side on every read and mutation. Client
metadata is never a trusted authorization boundary.

## 8. Existing lifecycle and scale gap

`MemoryLifecycleService.sweep_stale()` can remove low-importance,
stale USER, SEMANTIC, and RESEARCH rows and corresponding Qdrant points. Its
current default policy uses a 90-day age and importance at or below 0.3.

The dedicated `apps.worker.memory_lifecycle_main` process now invokes the sweep
on a configurable cadence. It defaults to report-only, uses a Valkey singleton
lock, processes bounded type-specific batches, isolates row failures, and emits
lifecycle health metrics. Production growth is not yet bounded until staging
dry runs are reviewed and deletion is explicitly enabled; that rollout evidence
is the remaining M3 acceptance criterion.

```mermaid
flowchart LR
    S[Recurring lifecycle worker] --> L[Distributed lock]
    L --> D[Dry-run candidate report]
    D --> B[Batched policy sweep]
    B --> P[Delete PostgreSQL canonical rows]
    P --> Q[Delete/reconcile Qdrant points]
    Q --> M[Lifecycle metrics and alerts]
    B --> I[Scheduled aggregate inventory]
    I --> R[Rows, bytes, age, distributions, vector drift]
```

## 9. Project isolation foundation (M5)

Project isolation landed before Projects stores memory. Scope is a
first-class, indexed field—not opaque metadata—with `scope_type` and nullable
`project_id` carried through PostgreSQL, Qdrant payloads, Valkey keys, caches,
idempotency keys, metrics, and S3 audit artifacts.

```mermaid
flowchart TD
    R[Authenticated request] --> A[Authorize project membership]
    A --> S{Request scope}
    S -- Personal --> P[Personal USER memory<br/>and permitted personal context]
    S -- Project A --> PA[Permitted personal USER defaults]
    S -- Project A --> MA[Only Project A SESSION, USER,<br/>SEMANTIC, and RESEARCH]
    PA --> C[Assemble bounded context]
    MA --> C
    PB[Project B memories] -. excluded by server filter .-> C
    C --> M[Model request]
```

Implemented rules:

- USER memory is personal/global by default; project-specific preferences are
  allowed only when explicitly scoped.
- SESSION, SEMANTIC, and RESEARCH created in a project are project-scoped.
- A Project A request may receive permitted personal USER defaults plus Project
  A memory, never Project B memory.
- Project deletion must define whether memories are erased, exported, or moved
  according to an explicit retention policy.
- Integration tests must prove cross-project and cross-owner leakage is
  impossible on every API, retrieval, cache, and background path.

## 10. User-visible memory management (M12/M15 complete; M13/M14 operational gates)

The initial personal USER-memory slice shipped early on 2026-08-17 and was
expanded in the same delivery cycle. `/memory` now exposes Personal and
authorized Project inventories for durable types, with accurate pagination,
filters, provenance, edit review, capture/inheritance controls, portable JSON
export, and selected/full-scope erasure. M14-M15 require a server-authorized
preview and a hashed, single-use, five-minute confirmation token before an
immediate cross-store deletion job can run. The Project/workspace product must
still supply authorized project context before project-scoped runtime traffic
is activated; that is a product integration gate, not a missing Memory UI.

Scope move, retrieval settings, both date bounds, and accessible modal focus
behavior are exposed in the UI. Deletion runs after the response using an
independently scoped database session; the UI polls durable job status and can
retry a failed stage. The remaining governance work is a published
provider-specific backup expiry and a dependency-backed staging drill. Project
runtime effect verification remains gated on Wave 3's authorized context.

The diagram below shows the implemented M5/M12-M15 flow:

```mermaid
flowchart LR
    UI[Memory settings] --> T{Personal or Project tab}
    T --> L[Paginated, filtered inventory]
    L --> V[View content, type, scope, source,<br/>explicit/inferred status, dates]
    V --> E[Edit]
    V --> D[Delete with confirmation]
    V --> MV[Move scope if authorized]
    UI --> X[Export personal/project memory]
    UI --> B[Bulk erasure with strong confirmation]
    E --> API[Scope-aware management API]
    D --> API
    MV --> API
    X --> API
    B --> API
    API --> C[Canonical PostgreSQL mutation]
    C --> R[Qdrant/cache reconciliation]
    R --> A[Audit event and visible result]
```

The UI distinguishes explicitly provided memories from inferred memories and
shows user-safe provenance without hidden model reasoning. Erasure covers
canonical rows, vector points, applicable scope caches/SESSION state, and
derived memory artifacts, retaining only content-free confirmation/job audit
records. Encrypted backup expiry remains a deployment retention-policy concern.

## 11. Bounded lifecycle and consolidation (M3, M8)

M3 adds recurring execution, type-specific policies, dry-run/report-only mode,
batching, distributed locking, bounded retries, metrics, alerts, and PostgreSQL ↔
Qdrant reconciliation. SESSION continues to rely primarily on TTL. Durable
memory policy will vary by type rather than applying one blunt age threshold.

M8 prevents SEMANTIC and RESEARCH memory from becoming a noisy set of
near-duplicates:

```mermaid
flowchart TD
    N[New durable fact or finding] --> E[Embedding candidate lookup]
    E --> C{Typed comparison}
    C -- duplicate --> M[Merge evidence and provenance]
    C -- supersedes --> S[Mark lineage and replace active version]
    C -- conflicts --> K[Keep conflict with explicit status]
    C -- distinct --> I[Insert new memory]
    M --> R[Reindex canonical result]
    S --> R
    K --> R
    I --> R
```

Consolidation must preserve provenance and reversibility. Similar embeddings
alone are not sufficient evidence to merge facts. M9 improves USER preference
supersession with topic-aware candidates. M10 now adds a versioned typed
preference object while retaining readable text for prompting and migration.
Controlled, explicit, high-confidence preferences can supersede one unique
typed key deterministically; custom/inferred/ambiguous cases retain the
conservative M9 judge path and never become hard routing constraints.

## 12. Total prompt budget (M4 complete)

The context builder receives one model-aware token budget shared by all
memory types. Allocation policy must be deterministic, observable, and leave
reserved room for the current instruction, retrieved documents, tool output,
and answer generation. Lower-value items are truncated or omitted before
higher-priority relevant items. Metrics record tokens used, items omitted, and
the reason for omission.

This makes the cost/latency/accuracy trade-off explicit:

- **Cost:** fewer input tokens and fewer unnecessary extraction calls.
- **Latency:** bounded reads, vector queries, rendering, and prompt size.
- **Accuracy:** relevant recent preferences and evidence survive before stale or
  weakly matched content.

## 13. Implemented evaluation loop with rollout gates (M6-M7)

```mermaid
flowchart LR
    D[Versioned memory eval dataset] --> R[Retrieval evaluation]
    R --> K[Recall@K, Precision@K, MRR/nDCG,<br/>scope leak, stale/conflict rates]
    D --> A[Paired answer runs: memory on vs off]
    A --> J[Answer utility, grounding, instruction adherence]
    K --> G[Release gate]
    J --> G
    G --> P[Production rollout]
    P --> O[Privacy-safe sampled online signals]
    O --> E[(eval_scores and dashboards)]
    E --> D
```

Evaluation must include helpful, irrelevant, stale, contradictory, and
cross-scope examples. Retrieval quality alone is insufficient: paired answer
tests must show whether injected memory improves the final response without
hurting grounding or current-instruction adherence. Online scoring is sampled,
bounded, redacted, and must never block the user response.

## 14. Observability (M11 complete)

The Memory Runtime dashboard and alert rules now include:

- Canonical row count and storage bytes by type and scope.
- Qdrant point count, indexing failures, and PostgreSQL/Qdrant drift.
- Accepted/rejected mutation counts and rate-limit denials.
- Extraction skips, circuit-breaker denials, and extraction output counts.
- Supersession, consolidation, conflict, and duplicate rates.
- Lifecycle candidates, deleted rows, duration, failures, and last success.
- Memory tokens injected, items omitted, retrieval latency, and utility signals.
- Reconciliation failures without sensitive content in labels or logs.

Governance job state is durable in PostgreSQL. Bounded completion/failure-stage
and duration metrics are emitted to Prometheus, shown on the Memory dashboard,
and backed by a failed-erasure alert.

Metric dimensions must remain bounded; owner IDs, project IDs, and free-text
memory content must not become metric labels.

## 15. Failure and consistency policy

| Failure | Required behavior |
|---|---|
| Context retrieval fails | Preserve the main Chat/Research flow where safe; record bounded diagnostics |
| Optional extraction fails | Do not fail an already produced answer |
| Feedback preference write fails | Preserve committed feedback/eval score; rollback isolated memory transaction |
| Public rate limiter is unavailable | Fail closed for mutations to prevent unbounded writes |
| Internal extraction limiter is unavailable | Fail open so the main flow remains usable |
| Qdrant indexing fails after canonical write | Keep PostgreSQL authoritative; retry/reconcile and expose drift |
| Lifecycle job overlaps | Distributed lock prevents concurrent sweeps |
| Scope cannot be proven | Deny access; never broaden to personal/all-project memory |
| Bulk erasure partially fails | Report incomplete state and retry reconciliation; never claim completion early |

## 16. Delivery plan

| Order | Task | Status | Primary outcome |
|---:|---|---|---|
| 1 | M0 feedback transaction isolation | Complete | Feedback remains durable when memory fails |
| 2 | M1 SESSION ordering | Complete | Newest context selected and rendered chronologically |
| 3 | M2 mutation limits and payload bounds | Complete | All public and governance mutation routes are bounded; extraction has an independent circuit breaker |
| 4 | M3 scheduled lifecycle | Implemented; rollout pending | Validate dry runs, enable deletion, and monitor cadence |
| 5 | M4 total token budget | Complete | Bound prompt cost and context crowding |
| 6 | M5 project scope | Foundation complete; Project runtime activation pending | Prevent cross-project memory leakage |
| 7 | M6 memory evaluation | Implementation complete; staging calibration pending | Seed staging, capture live retrieval and paired answers, human-calibrate the judge/budgets, and enforce the live deployment gate |
| 8 | M7 online quality signals | Implemented; rollout/calibration pending | Generation correlation, explicit memory feedback, and opt-in sampled utility/harm scoring |
| 9 | M8 evidence-driven consolidation | Implemented; rollout/evaluation gate pending | Bounded vector nomination, typed decisions, reversible lineage, and fail-safe re-indexing |
| 10 | M9-M10 preference quality | Implemented; rollout calibration pending | Complete-history topical lookup plus additive typed values and deterministic safe-key supersession |
| 11 | M11 observability | Complete | Scheduled bounded inventory plus size, growth, lifecycle, drift, budget, consolidation, and utility panels/alerts |
| 12 | M12 management API | Complete | Scope-safe durable enumeration/mutations, safe responses, explicit edits, confirmed moves, independent settings, and two-user/two-project tests |
| 13 | M13 management UI | Implemented; product integration pending | Full Personal/Project controls work; verify the next Project request once Wave 3 supplies authorized context |
| 14 | M14 export and erasure | Implemented; operational acceptance pending | Deploy `c8d9e0f1a2b3`; verify backup expiry and run a real dependency-backed erasure drill |
| 15 | M15 destructive confirmation | Complete | Authorized previews plus hashed, single-use, five-minute confirmation tokens |
| 16 | M16 hardening | Partial | Prompt delimiters, quotas, reconciliation, 1,000-candidate budget, and retry regressions exist; staged load/failure suites remain |

The authoritative acceptance criteria and dependencies for every item remain in
[MEMORY_PLATFORM_PRIORITIZED_TASKS.md](MEMORY_PLATFORM_PRIORITIZED_TASKS.md).

## 17. Production invariants

Every implementation and review should preserve these invariants:

1. The current user instruction outranks remembered content.
2. Authentication and authorization precede retrieval; scope filters are
   server-derived and fail closed.
3. PostgreSQL is canonical for durable memory; vector and cache state is
   reconcilable.
4. Optional memory work cannot break the main Chat, Research, or feedback flow.
5. Public mutation volume, payload size, extraction calls, prompt tokens, and
   lifecycle batch size are bounded.
6. No free text, owner ID, or project ID appears in metric labels.
7. Destructive actions are confirmed, auditable, and honest about partial
   completion.
8. New retrieval or extraction behavior ships only with accuracy, latency, and
   cost measurements plus memory-on/off regression coverage.

## 18. Verification references

- Run the focused automated tests attached to each M-task before the broader
  Chat and Research suites.
- Follow [MEMORY_MANUAL_TEST.md](MEMORY_MANUAL_TEST.md) for the current M0-M4
  end-to-end checks. M3 is safe-by-default in dry-run mode and still requires
  a production rollout decision before deletion is enabled.
- Use [PRODUCTION_READINESS_EVALUATION.md](../PRODUCTION_READINESS_EVALUATION.md)
  for the repository-wide production bar.
- Treat [architecture/memory-platform.md](architecture/memory-platform.md) as
  the detailed accepted design and update it when implementation changes a
  contract described here.
