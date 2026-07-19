# Memory Platform Architecture
Version: 1.0
Status: Accepted
Phase: 11.23

---

# Implementation Status Corrections (2026-07-19)

This doc describes the target design; the sections below have drifted from what `app/ai/memory/` actually does. Corrected in place, summarized here for a quick diff against the original:

- **§6.3/§6.4/§19 Storage** — Semantic Memory is **Postgres (canonical) + Qdrant (search index)**, not Qdrant alone. Research Memory is **Postgres (canonical) + Qdrant (search index)**, not "PostgreSQL, S3, Qdrant" — S3 only holds a best-effort, platform-wide audit artifact for any `search()`/`get_context()` call, it is not a memory storage backend for any specific type.
- **§7/§8 Internal Architecture / Folder Structure** — no `Classification Engine` or `Consolidation Engine` module exists; no `contracts/`, `providers/`, `registries/`, `factories/`, `scoring/`, `search/`, or `classification/` directories exist. See the corrected tree in §8.
- **§13 Memory Lifecycle** — the hot → warm → cold → archive staging shown is aspirational. What's actually implemented: Valkey TTL (SESSION) and a callable-but-unscheduled stale-row sweep straight to delete (USER/SEMANTIC/RESEARCH) — no status field, no archive tier.
- **§14 Memory Consolidation** — not implemented at all (no code exists under any name).
- **§16 Memory Extraction** — the example's `"type": "USER_PREFERENCE"` isn't a real `MemoryType` value (the enum is `session`/`user`/`research`/`semantic`); corrected to `"user"`. Extraction is not hypothetical — it's wired live into both Chat and Research.
- **§20 Integration Points** — only the Chat integration is actually live. Research memory is wired directly into today's linear `ResearchService`, not into a "Planner" stage — no Research Runtime/Planner exists yet. Agent Runtime and Workspace Runtime don't exist.
- **§21 Observability** — `memory_metrics.json` is not written anywhere; only `memory_context.json`/`memory_search.json` are real.
- **§22 Evaluation / §25 Exit Criteria** — no evaluation harness (Recall@K/Precision@K/etc.) exists; the exit-criteria checkmark for it was wrong.

---

# 1. Purpose

The Memory Platform provides persistent intelligence for ResearchMind.

Unlike Retrieval, which retrieves external knowledge, Memory retrieves
information learned through interactions, research sessions and user behavior.

Memory enables:

- Personalized conversations
- Long-running research sessions
- Context continuity
- Future agent collaboration
- Workspace intelligence

---

# 2. Philosophy

ResearchMind separates:

```text
Knowledge

≠

Memory
```

---

## Knowledge

External information.

Examples:

- PDFs
- Web pages
- Research papers
- Databases

---

## Memory

Internal information.

Examples:

- User preferences
- Previous conversations
- Research findings
- Session context
- Learned facts

---

# 3. Architectural Principle

Memory is a first-class platform.

```text
Runtime
      ↓
Memory Platform
      ↓
Storage Providers
```

Frameworks remain implementation details.

```text
ResearchMind Memory
          ↓
Interfaces
          ↓
Providers
          ↓
Framework Runtime
```

Never:

```text
ResearchMind
      ↓
LangGraph Memory Everywhere
```

---

# 4. Position Inside ResearchMind

```text
Request
     ↓
Memory Platform
     ↓
Knowledge Platform
     ↓
Context Platform
     ↓
Generation Platform
     ↓
Response
     ↓
Memory Update
```

Memory is executed both:

1. Before generation
2. After generation

---

# 5. High Level Architecture

```text
Memory Platform

├── Session Memory
├── User Memory
├── Research Memory
├── Semantic Memory
└── Future Workspace Memory
```

---

# 6. Memory Types

---

# 6.1 Session Memory

Purpose:

Remember active interactions.

Examples:

- chat history
- retrieved context
- runtime state

Characteristics:

- short-term
- low latency
- TTL based

Storage:

Valkey

---

# 6.2 User Memory

Purpose:

Remember preferences.

Examples:

- preferred provider
- response style
- formatting preferences
- interests

Storage:

PostgreSQL

---

# 6.3 Semantic Memory

Purpose:

Remember meaningful facts.

Examples:

- repeated interests
- important discoveries
- behavioral patterns

Storage:

PostgreSQL (canonical row — CRUD/ownership)
Qdrant (embedding — search-index only, not source of truth)

---

# 6.4 Research Memory

Purpose:

Remember research outputs.

Examples:

- reports
- findings
- evidence
- citations

Storage:

PostgreSQL (canonical row — CRUD/ownership)
Qdrant (embedding — search-index only, not source of truth)

Note: the full report/citations/sources for a research answer are **not**
stored here — they persist via the separate Research API Platform's own
`ResearchSession` Postgres row and its S3 Research Artifact. This memory
type instead stores a condensed, searchable *finding*, tagged with the
originating `research_id`, so a future turn can retrieve it via
`search()`. S3 does not back this memory type directly — see §17.

---

# 7. Internal Architecture

```text
Memory Platform

├── Memory Service            (services/memory_service.py — orchestrator)
├── Extraction Engine         (extraction/ — LLM-driven, via Generation Runtime)
├── Scoring Engine            (importance.py — rule-based heuristic, not an LLM engine)
├── Classification Engine     ❌ not a separate module — folded into Extraction
│                                (ExtractedMemory.type carries it)
├── Search Engine             (retrieval/ — Reciprocal Rank Fusion across per-type results)
├── Consolidation Engine      ❌ not implemented (see §14)
├── Lifecycle Manager         (lifecycle/ — stale-row sweep only, see §13)
└── Storage Router            not a distinct class — routing lives in create.py's
                                 composition root + MemoryService's per-type dispatch
```

---

# 8. Folder Structure

As designed (above) vs. as actually built (below) — no `contracts/`,
`providers/`, `registries/`, or `factories/` directories exist;
`models.py`/`enums.py`/`exceptions.py`/`importance.py` are single root
files, not directories; `search/`/`classification/`/`consolidation/`
don't exist under any name:

```text
app/

    ai/

        memory/

            models.py           # MemoryRecord, MemoryContext, MemorySearchRequest/Result
            enums.py             # MemoryType, MemoryOperation
            exceptions.py
            importance.py        # rule-based scoring (doc's "Scoring Engine")

            extraction/          # LLM-driven, via Generation Runtime
            retrieval/           # Reciprocal Rank Fusion (doc's "Search Engine")
            lifecycle/           # stale-row sweep (doc's "Lifecycle Manager")
            observability/       # metric name constants

            session/             # SessionMemoryService (Valkey)
            profile/             # UserMemoryService (Postgres) -- doc's "User Memory"
            semantic/            # SemanticMemoryService (Postgres + Qdrant)
            research/            # ResearchMemoryService (Postgres + Qdrant)

            storage/             # ValkeySessionStore, PostgresMemoryStore,
                                  # MemoryVectorIndex, VectorBackedMemoryService
            services/            # MemoryService (the orchestrator, doc's "Memory Service")
            artifacts/           # MemoryContextArtifact/MemorySearchArtifact + writer (S3)

            create.py            # composition root
```

---

# 9. Memory Creation Flow

```text
Interaction
      ↓
Memory Extraction
      ↓
Importance Scoring
      ↓
Memory Classification
      ↓
Storage Routing
      ↓
Persistence
      ↓
Embedding
      ↓
Vector Indexing
```

---

# 10. Memory Retrieval Flow

```text
Request
      ↓
Memory Search
      ↓
Session Retrieval
      ↓
Semantic Retrieval
      ↓
Research Retrieval
      ↓
Merge
      ↓
Deduplicate
      ↓
Rerank
      ↓
Memory Context
```

---

# 11. Runtime Flow

```text
Request
     ↓
Memory Retrieval
     ↓
Knowledge Retrieval
     ↓
Context Platform
     ↓
Generation
     ↓
Validation
     ↓
Artifacts
     ↓
Memory Update
```

---

# 12. Memory Search Architecture

Memory search behaves similarly to Retrieval.

```text
Query
    ↓
Embedding
    ↓
Vector Search
    ↓
Metadata Filtering
    ↓
Reranking
    ↓
Memory Results
```

Note: "Reranking" here is **Reciprocal Rank Fusion** across each memory
type's own already-ranked result list (same `k=60` RRF algorithm the
Knowledge Platform's `RetrievalFusionService` uses for dense/sparse
retrieval), not a cross-encoder/LLM reranker model. Also, SESSION memory
is excluded from embedding-based `search()` entirely (Valkey has no
vector index); USER memory's "search" is a recency-ordered listing, not
a semantic search — only SEMANTIC and RESEARCH actually go through
vector search.

---

# 13. Memory Lifecycle

```text
Create
   ↓
Hot
   ↓
Warm
   ↓
Cold
   ↓
Archive
   ↓
Delete
```

**❌ Not implemented as staged above.** There is no status field and no
archive tier. What actually exists is simpler:

- SESSION — Valkey's own TTL is the entire lifecycle (create → expire);
  nothing colder than "expired" applies to a conversation turn.
- USER / SEMANTIC / RESEARCH — no automatic staging at all until
  `MemoryLifecycleService.sweep_stale()` deletes rows past an age
  threshold with importance below a cutoff (defaults: 90 days,
  importance ≤ 0.3) — a direct create → delete jump, no warm/cold
  tiering in between. This method is callable but **not scheduled** —
  no cron/scheduler infrastructure exists in this codebase to run it
  periodically.

Different memory types have different retention policies.

---

# Session Memory

TTL:

```text
7 days
```

---

# User Preferences

TTL:

```text
Never
```

---

# Research Reports

TTL:

```text
Never
```

---

# Temporary Facts

TTL:

Configurable.

---

# 14. Memory Consolidation

**❌ Not implemented.** No code exists under this or any other name —
deferred pending real usage data to tune merge/similarity thresholds
against, per this doc's own §23 "Future Extensions." What follows is
the target design.

Without consolidation memory grows infinitely.

Purpose:

- merge duplicates
- compress memories
- remove noise

Flow:

```text
Memories
      ↓
Similarity Clustering
      ↓
Merge Candidates
      ↓
LLM Consolidation
      ↓
Delete Old Memories
      ↓
Create Consolidated Memory
```

---

# 15. Importance Scoring

Not every interaction becomes memory.

Examples:

Low Importance:

```text
hello
thanks
yes
```

High Importance:

```text
favorite model
research preferences
important findings
```

Importance score:

```python
0.0 -> 1.0
```

---

# 16. Memory Extraction

LLMs can automatically create memories. This is not hypothetical — it's
live: `MemoryExtractionService` (`extraction/service.py`) is wired into
both Chat and Research today, running after every turn via the
Generation Runtime. Classification is folded into extraction rather
than a separate stage (the model's `type` field carries it in one call).

Example:

Input:

```text
I prefer Claude for reasoning tasks.
```

Output:

```json
{
    "content": "User prefers Claude for reasoning tasks",
    "importance": 0.93,
    "type": "user"
}
```

(`type` must be one of the real `MemoryType` values — `session`, `user`,
`research`, `semantic` — not the `USER_PREFERENCE` label shown in an
earlier version of this example.)

---

# 17. Storage Architecture

```text
                 Memory Platform
                         ↓
 ┌──────────┬──────────┬──────────┬──────────┐
 │ Valkey   │Postgres  │ Qdrant   │   S3     │
 └──────────┴──────────┴──────────┴──────────┘
```

---

## Valkey

Stores:

- session memory
- active conversations
- runtime state

---

## PostgreSQL

Stores:

- user profiles
- metadata
- reports
- preferences

---

## Qdrant

Stores:

- semantic memory embeddings
- memory search indexes

---

## S3

Stores:

- reports
- snapshots
- artifacts

---

# 18. Canonical Models

---

# MemoryRecord

```python
class MemoryRecord(BaseModel):
    id: UUID

    owner_id: UUID

    type: MemoryType

    content: str

    metadata: dict

    importance_score: float

    created_at: datetime
    updated_at: datetime
```

---

# MemoryContext

```python
class MemoryContext(BaseModel):

    session_memories: list[MemoryRecord]

    semantic_memories: list[MemoryRecord]

    research_memories: list[MemoryRecord]
```

---

# MemorySearchRequest

```python
class MemorySearchRequest(BaseModel):

    query: str

    owner_id: UUID

    top_k: int
```

---

# MemorySearchResult

```python
class MemorySearchResult(BaseModel):

    memories: list[MemoryRecord]

    latency_ms: float
```

---

# 19. Provider Architecture

```text
MemoryService
       ↓
MemoryProvider
       ↓
Storage Providers
```

---

## Providers

### Session Provider

Valkey

### Semantic Provider

PostgreSQL (canonical) + Qdrant (search index) — via a shared
`VectorBackedMemoryService` base class, not Qdrant alone

### User Provider

PostgreSQL

### Research Provider

PostgreSQL (canonical) + Qdrant (search index) — not PostgreSQL + S3.
S3 only holds a best-effort, cross-cutting audit artifact for
`search()`/`get_context()` calls (any memory type), never the memory
record itself — see §6.4

---

# 20. Integration Points

Only Chat's integration below is actually live end-to-end today.

---

# Chat Runtime — ✅ Live

```text
Question
      ↓
Memory Search
      ↓
Generation
```

`chat.py` calls `MemoryService.get_context()` before generation
(prepended into `PromptContext.context`) and stores/extracts memory
after, via Runtime Memory Injection.

---

# Research Runtime — 🟡 Partially live (no Planner exists)

```text
Research Goal
       ↓
Research Memory
       ↓
Planner
```

Memory *is* wired live — but directly into today's linear
`ResearchService` (the Research API Platform), the same
get-context-before/store-after pattern as Chat. There is no separate
"Research Runtime" or "Planner" stage yet — decomposition/planning is
an explicit Non-Goal of the current Research API Platform (see
`research_api_prd.md` §4) and is future work. When a real Research
Runtime with a Planner is built, it will sit in front of the
already-wired memory integration, not replace it.

---

# Agent Runtime — ❌ Not built

```text
Task
   ↓
Agent Memory
   ↓
Execution
```

No Agent Runtime exists in this codebase yet — this integration point
is aspirational.

---

# Workspace Runtime — ❌ Not built

```text
Workspace
      ↓
Reports
      ↓
Memories
      ↓
Knowledge
```

No Workspace Runtime exists in this codebase yet — this integration
point is aspirational.

---

# 21. Observability

Metrics:

```text
memory_hits
memory_misses
memory_count
memory_size
remember_latency
search_latency
embedding_latency
```

Artifacts:

```text
memory_context.json    ✅ real — MemoryArtifactWriter.write_context(), best-effort, S3
memory_search.json     ✅ real — MemoryArtifactWriter.write_search(), best-effort, S3
memory_metrics.json    ❌ not implemented — no write_metrics() method exists;
                          only counter/duration metric names are recorded
                          via MetricsRecorder, no S3 snapshot
```

---

# 22. Evaluation

**❌ Not implemented.** No evaluation harness exists for the Memory
Platform — `tests/integration/test_memory.py` is still an empty stub.
Deferred, matching this doc's own §23 "Future Extensions" framing.
Target metrics (not yet measured by anything):

- Recall@K
- Precision@K
- Latency
- Storage Cost
- Memory Utility Score

---

# 23. Future Extensions

Phase 2:

```text
episodic memory
reflection memory
memory decay
memory compression
memory summarization
```

Phase 3:

```text
workspace memory
organization memory
agent shared memory
```

---

# 24. Complete Production Flow

```text
                           User
                             ↓
                       Runtime Request
                             ↓
                    Memory Platform
                             ↓
     ┌────────────┬────────────┬─────────────┐
     │ Session    │ Semantic   │ Research    │
     │ Memory     │ Memory     │ Memory      │
     └────────────┴────────────┴─────────────┘
                             ↓
                      Memory Fusion
                             ↓
                        Deduplication
                             ↓
                           Rerank
                             ↓
                      Memory Context
                             ↓
                     Knowledge Retrieval
                             ↓
                       Context Platform
                             ↓
                    Generation Platform
                             ↓
                         Response
                             ↓
                    Memory Extraction
                             ↓
                    Importance Scoring
                             ↓
                    Classification
                             ↓
                         Storage
```

---

# 25. Exit Criteria

Memory Platform is complete when:

✅ session continuity works

✅ preferences persist

✅ semantic memory search works

✅ research findings are searchable/reusable (via Research Memory
search — not full reports, which are a separate platform's concern;
see §6.4)

✅ memory observability exists (basic — counters + best-effort S3
audit artifacts; no dashboards, no `memory_metrics.json`, see §21)

❌ memory evaluation exists — **not built**, corrected from the
original ✅ (see §22)

✅ future runtimes can consume memory (Chat and Research today; Agent/
Workspace runtimes don't exist yet to consume it — see §20)
