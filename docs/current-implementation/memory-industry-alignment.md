# Memory Architecture — Current Implementation Evaluation

> Reconciled 2026-08-17: memory hardening M0-M2 and M4-M16 is implemented. The M3
> lifecycle worker remains dry-run by default pending production rollout;
> M6-M10 retain their documented staging calibration/rollout gates. M12's
> scope-aware management API and M13's Personal/Project Memory UI are
> live with listing, filtering, pagination, editing, capture/inheritance
> controls, export, and confirmed erasure. M14-M16 add portable export,
> retryable cross-store governance jobs, single-use confirmations, prompt
> delimiters, quotas, and drift reconciliation. M5's
> storage and authorization isolation is live; broader Project/workspace runtime
> activation remains.

## 1. Purpose and scope

This document evaluates ResearchMind AI's memory implementation against the architecture, components, and criteria shown in the supplied memory reference images.

The evaluation focuses on concepts rather than framework or vendor choices. Valkey, PostgreSQL, Qdrant, or another technology is considered aligned when it fulfills the required memory role.

The assessment separates:

- **Active default** — used by the current Chat or Research runtime.
- **Available capability** — implemented and callable, but optional or not automatically used.
- **Partial alignment** — the core concept exists, but is incomplete or has a meaningful behavioral difference.
- **Gap** — no material equivalent was found.

### Status legend

| Status | Meaning |
|---|---|
| **Strongly aligned** | The important concept is implemented, integrated, and used. |
| **Aligned** | The criterion is materially covered. |
| **Partially aligned** | Useful coverage exists, but behavior or scope is incomplete. |
| **Available, not default** | Implemented, but not active in the primary runtime path. |
| **Gap** | No material equivalent was found. |
| **Not currently necessary** | A legitimate pattern that is not required for the current product behavior. |

> A gap is not automatically a recommendation. Memory increases personalization and continuity, but also creates privacy, stale-fact, security, cost, and deletion risks. The goal is appropriate coverage, not remembering everything.

---

## 2. Executive assessment

ResearchMind AI has a substantial, production-oriented memory platform rather than a simple conversation buffer.

The current implementation includes:

- canonical Chat conversations and messages persisted in PostgreSQL;
- bounded recent-message context;
- deterministic summaries of older Chat turns;
- session-topic state distilled after completed turns;
- TTL-bound session memory in Valkey;
- persistent user, semantic, and research memories in PostgreSQL;
- a dedicated Qdrant collection for semantic and research-memory retrieval;
- owner-scoped vector filtering and owner-scoped CRUD;
- automatic post-turn memory extraction for Chat and Research;
- a local extraction policy that avoids LLM calls for trivial or low-value turns;
- importance scoring and a minimum storage threshold;
- exact normalized deduplication for automatically extracted durable memories;
- relevance score thresholds for semantic recall;
- parallel semantic and research-memory retrieval using one shared query embedding;
- memory-context injection before Chat, Linear Research, Deep Research planning, and research execution;
- explicit remember, search, context, recall, update, and forget APIs;
- memory artifacts, logs, latency metrics, hit/miss metrics, extraction metrics, and context metrics;
- a recurring, singleton-locked stale-memory worker with per-type policies,
  dry-run safety, bounded batches, row isolation, and Prometheus metrics;
- coordinated memory prompt budgeting with whole-entry truncation and
  omission reporting;
- Personal and authorized Project memory management, independent capture and
  retrieval controls, scoped export, and immediate server-confirmed erasure;
- durable-record quotas, untrusted-memory prompt delimiters, aggregate
  capacity inventory, and PostgreSQL/Qdrant drift reconciliation.

The largest differences from the reference architecture are:

1. autonomous agents are not given `SaveMemory` and `SearchMemory` tools;
2. persisted `USER` preferences are injected into the normal `MemoryContext`,
   with current-turn instructions taking precedence;
3. episodic history exists as conversations, research runs, events, and artifacts, but not as a dedicated searchable episode model;
4. automatic extraction only creates `USER` and `RESEARCH` memories, not general `SEMANTIC` facts;
5. exact duplicate handling and USER-preference supersession exist, while
   broader contradiction and temporal fact versioning remain deferred;
6. the stale-memory sweep is scheduled by a dedicated worker but defaults to
   dry-run; there is still no hot/warm/cold/archive lifecycle;
7. session memory is TTL-bound and fail-open, while canonical conversation history is separately durable;
8. durable research-runtime checkpointing exists as a construction path but is disabled by default and not wired to startup;
9. quality evaluation, lifecycle deletion, and capacity thresholds are
   implemented but still require the documented staging/production calibration.

### Overall alignment

| Area | Assessment | Summary |
|---|---|---|
| Sensory/current-input memory | **Aligned** | Current prompt, retrieved evidence, memory context, and runtime state are assembled per request. |
| In-context/short-term memory | **Strongly aligned** | Recent turns, bounded summaries, persisted history, and distilled session state are active. |
| Vector/semantic long-term memory | **Strongly aligned** | PostgreSQL source of truth plus Qdrant similarity index and memory injection are active. |
| User/profile memory | **Strongly aligned** | Persistent preferences are extracted, owner-scoped, superseded when appropriate, and automatically injected by `get_context()`. |
| Episodic memory | **Partially aligned** | Durable, timestamped conversations and research execution records exist, but episode-specific semantic retrieval is absent. |
| External/tool memory | **Gap for autonomous tool use** | Memory HTTP/service APIs exist, but agents do not autonomously select save/search memory tools. |
| Memory-augmented RAG | **Strongly aligned** | Memory retrieval precedes generation and is combined with document/web/paper context. |
| Memory writing and extraction | **Strongly aligned** | Post-turn policy, structured extraction, importance filtering, idempotency, and deduplication are integrated. |
| Memory lifecycle and governance | **Aligned foundation** | Scope-aware CRUD/settings, portable export, confirmed retryable cross-store erasure, TTL, owner/project isolation, quotas, and scheduled dry-run lifecycle evaluation exist; lifecycle deletion rollout, archival, sensitive-category consent, and generic temporal correction remain. |
| Observability and evaluation | **Aligned foundation** | M11 exposes aggregate storage, drift, lifecycle, budget, consolidation, and utility signals; M6/M7 provide offline and sampled online quality evaluation, with staging calibration still required. |

---

## 3. Evaluation against the four memory types in the reference

| Reference memory type | Current implementation | Alignment | Misalignment or gap |
|---|---|---|---|
| **Sensory memory** — raw current input and active request tokens | The current user prompt, generated transcript, memory block, retrieved document context, web/paper context, and runtime metadata are assembled into the generation request. | **Aligned.** The model receives the current turn plus explicitly constructed context. | Sensory memory is transient by design. It is not represented as a first-class `MemoryType`, which is appropriate. |
| **Short-term / in-context memory** — active session history | Canonical messages persist in PostgreSQL. Chat loads recent messages, compacts older history into a bounded deterministic summary, folds both into the prompt, and maintains an additional short `current_topic` session state in Valkey. | **Strongly aligned.** It exceeds a simple sliding conversation buffer by combining recent verbatim turns, compacted history, and distilled topic state. | Provider requests currently receive history as a plain-text transcript inside one user prompt rather than native multi-message arrays. Session-state distillation is best-effort and can fail open. |
| **Long-term vector / semantic memory** — durable facts retrieved by similarity | `SEMANTIC` and `RESEARCH` memories persist canonically in PostgreSQL and are indexed in a dedicated Qdrant collection. Queries use Voyage embeddings, owner/type filters, score thresholds, and top-K retrieval. | **Strongly aligned.** The architecture correctly separates durable CRUD storage from the similarity index. | Automatic extraction creates `USER` and `RESEARCH` memories, but not `SEMANTIC` memories. General semantic facts therefore require explicit API writes or other callers. |
| **Episodic memory** — timestamped records of past sessions/events | Conversations and messages have timestamps; research sessions, runs, run events, plans, evidence, reports, and artifacts persist with identifiers and lifecycle metadata. | **Partially aligned.** The raw material for episodic memory is strong and durable. | There is no canonical `Episode` object with summary, tags, outcome, temporal range, and semantic retrieval. The memory search API searches durable memory records, not whole prior sessions as episodes. |
| **External/tool memory** — agent autonomously saves/searches through tools | The platform exposes authenticated memory APIs and a `MemoryService` with remember/search/context/recall/update/forget operations. Research execution also persists artifacts and state. | **Partially aligned as a platform service; gap as agent autonomy.** | No agent-facing `SaveMemory`/`SearchMemory` tool registration or model-selected memory tool loop was found. Runtime orchestration decides when memory is retrieved or written. |

---

## 4. ResearchMind AI's native memory taxonomy

The implementation uses a more product-specific taxonomy than the reference images.

| ResearchMind type | Storage | Retrieval behavior | Active use | Industry interpretation |
|---|---|---|---|---|
| **SESSION** | Valkey, TTL-bound | Recent records by owner and session ID; no free-text semantic search | Distilled current-topic state is stored after Chat/Research turns. Raw-turn storage is disabled by default. | Short-term/session memory |
| **USER** | PostgreSQL | Recent preference listing; not vector-indexed | Automatically extracted durable preferences/profile facts can be stored. Explicit CRUD/search API supports it. | Profile or personalized long-term memory |
| **SEMANTIC** | PostgreSQL + Qdrant | Embedding similarity with owner/type filter and score threshold | Included in memory context when records exist; usually written explicitly rather than by automatic extraction. | General vector/semantic long-term memory |
| **RESEARCH** | PostgreSQL + Qdrant | Embedding similarity with owner/type filter and score threshold | Significant findings/evidence can be automatically extracted after turns and injected into future Chat/Research. | Domain long-term memory and research knowledge |
| **Canonical conversation history** | PostgreSQL conversations/messages | Recent messages plus compacted older summary | Active in Chat and available for replay | Durable conversation history; separate from `MemoryRecord` |
| **Research runtime state** | PostgreSQL run/session/event records and artifacts; optional graph checkpoints | Lookup/replay by owner, conversation, research, or run IDs | Active durable records; Postgres LangGraph checkpointing disabled by default | Agent execution state and episodic evidence |

This separation is generally sound:

- canonical conversation history remains complete and auditable;
- short-term session state is optimized for quick, expiring recall;
- profile facts remain relational and editable;
- semantic and research facts gain vector retrieval;
- reports and evidence remain owned by the Research and Artifact platforms instead of being duplicated into memory.

---

## 5. In-context and short-term memory

| Criterion | Status | Current alignment | Gap or limitation |
|---|---|---|---|
| Persist every completed conversation turn | **Strongly aligned** | Both user and assistant messages are committed to PostgreSQL with role and timestamp. | Incomplete/failed streamed turns require careful handling so only valid exchanges are persisted. |
| Load recent history into the model context | **Aligned** | A configurable number of recent messages is loaded oldest-first and folded into the generation prompt. | History is flattened into text rather than supplied as native role-separated provider messages. |
| Bound context growth | **Strongly aligned** | Older turns are compacted while a recent-message window remains verbatim. | Character bounds approximate rather than directly enforce model token budgets. |
| Preserve older context | **Aligned** | Older messages remain canonical database rows and are also summarized for prompt use. | The deterministic summary is extractive and can truncate information once the bound is reached. |
| Preserve preferences/decisions during compaction | **Aligned** | Explicit interest, preference, “remember,” and decision markers are prioritized before general turn excerpts. | Pattern-based detection can miss implicitly expressed preferences or decisions. |
| Resolve ambiguous pronouns and follow-ups | **Strongly aligned** | A cheap structured-output model maintains one evolving `current_topic` state after each turn. Paper-query extraction also receives recent context. | Session-state distillation is best-effort; failures skip the update instead of blocking the completed turn. |
| Sliding window / recent-turn limit | **Aligned** | Recent-message limits and memory-context item limits are configurable. | Separate limits across transcript, session memory, semantic memory, and research memory need joint token-budget monitoring. |
| Session expiry | **Aligned** | Valkey session memory expires after seven days by default, with a maximum index length of 200 entries. | The session index can retain expired record IDs until the index itself expires; reads safely skip missing records. |
| Durable history beyond session TTL | **Strongly aligned** | PostgreSQL conversation history remains available even when Valkey session memory expires. | Chat history and memory records form two overlapping sources that require deduplication and clear ownership. |
| Deduplicate session memory against transcript | **Aligned** | Context assembly removes raw session records already present in the canonical transcript. | Deduplication is normalized-text based rather than semantic. |
| Session-state growth control | **Strongly aligned** | The `current_topic` record is updated in place instead of appending a new snapshot every turn. | Only one current topic summary is retained; nuanced parallel threads may be compressed too aggressively. |

### Short-term-memory conclusion

ResearchMind AI is strongly aligned with production short-term memory. It uses three complementary representations:

1. complete canonical messages for replay and audit;
2. recent verbatim turns plus an older summary for prompt continuity;
3. a compact session-state slot for pronoun and topic resolution.

This is more resilient than simply appending the entire chat buffer until the context window fills.

---

## 6. Long-term semantic and profile memory

| Criterion | Status | Current alignment | Gap or limitation |
|---|---|---|---|
| Durable source of truth | **Strongly aligned** | PostgreSQL is canonical for `USER`, `SEMANTIC`, and `RESEARCH` memory CRUD and ownership. | None material. |
| Vector similarity index | **Strongly aligned** | Qdrant stores embeddings for semantic and research memories in a dedicated collection. | User-profile memories are intentionally not vector-indexed. |
| Owner isolation | **Strongly aligned** | Database reads and vector searches require `owner_id`; Qdrant payload filters include owner and memory type. | Continue adversarial tests for every API and background path. |
| Similarity threshold | **Aligned** | A default cosine score threshold prevents unrelated nearest neighbors from being injected merely because they are top-K. | Threshold quality should be evaluated by memory type and embedding model. |
| Shared query embedding | **Aligned** | Context retrieval creates one query embedding and reuses it for semantic and research searches. | None material. |
| Parallel retrieval | **Aligned** | Semantic and research searches run concurrently by default. | Each branch fails independently and fails open, which favors availability over completeness. |
| Multiple memory sources fused | **Aligned** | General memory search uses reciprocal-rank fusion across user, semantic, and research result lists. | `get_context()` returns categories separately rather than globally reranking them together. |
| Importance score | **Aligned** | Each memory has a score from 0 to 1; low-importance writes are skipped. | Importance does not decay with time or change based on successful recall. |
| Automatic durable-memory extraction | **Strongly aligned** | A structured-output LLM extracts stable preferences and research findings after eligible Chat/Research turns. | Extraction only proposes `USER` or `RESEARCH`, not `SEMANTIC`, and can produce incorrect or overgeneralized facts. |
| Avoid remembering everything | **Strongly aligned** | Local policy skips trivial, short, non-user-facing, and non-durable turns before invoking the extractor. | Durable-signal patterns are English-specific and may miss other languages or implicit signals. |
| Explicit “remember this” intent | **Aligned** | Explicit phrases route to synchronous extraction intent. | The surrounding API flow should make success/failure visible to the user if explicit remembering becomes a UX promise. |
| Repeated-interest promotion | **Aligned** | Repeated topics across distinct sessions can make an otherwise generic turn eligible for extraction. | Promotion is heuristic and requires monitoring for accidental profiling. |
| Exact and evidence-driven deduplication | **Aligned foundation** | Exact duplicates update provenance/importance; M8 additionally nominates same-scope SEMANTIC/RESEARCH pairs by vector similarity and uses a typed judge for duplicate, mergeable, contradiction, or unrelated outcomes with reversible lineage. | M8 defaults disabled/dry-run pending reviewed rollout evidence; generic temporal contradiction resolution remains deferred. |
| Contradiction and supersession | **Gap by deliberate design** | The code explicitly avoids semantic supersession without a subject/version contract. | A later “I now prefer concise answers” can coexist with an older contradictory preference. |
| Temporal validity | **Partial** | Created and updated timestamps are stored, and metadata can carry provenance. | No `valid_from`, `valid_to`, subject key, confidence, or explicit superseded-by relation exists. |
| Automatic user-profile injection | **Gap in normal context assembly** | User memories can be listed through search/API. | `MemoryContext` deliberately excludes `user_memories`, so persisted profile/preferences are not automatically included in Chat/Research prompt memory. |
| Research finding traceability | **Aligned** | Research memories can carry `research_id`, source turn ID, and policy version. | Claim-level source/citation references are not guaranteed inside every extracted memory record. |

### Important personalization gap

The extractor can create `USER` memories such as response preferences or research interests. However:

- `MemoryContext` only contains session, semantic, and research memories;
- `format_memory_context()` only formats those three categories;
- `UserMemoryService.list_preferences()` is used by the explicit general memory search path, not normal per-turn context retrieval.

Therefore, ResearchMind stores profile memories more completely than it consumes them. This is a meaningful misalignment with the reference's long-running personalized-assistant goal.

---

## 7. Episodic memory

| Criterion | Status | Current alignment | Gap or limitation |
|---|---|---|---|
| Timestamped past sessions | **Strongly aligned** | Conversations, messages, research sessions, runs, and run events have durable timestamps. | These records are distributed across domain models rather than unified as episodes. |
| Session summaries | **Aligned for Chat** | Older Chat history has a bounded persisted summary; session topic state also exists. | Research conversations do not use the identical Chat compaction model. |
| Store actions and outcomes | **Strongly aligned for Research** | Research plans, evidence, approvals, web-search decisions, draft reviews, reports, costs, events, and artifacts are persisted. | Normal Chat episodes store turns but less structured outcome metadata. |
| Episode metadata and tags | **Partially aligned** | Runtime metadata, conversation IDs, research IDs, turn IDs, status, and artifact metadata exist. | No standard episode tags, participants, objective, outcome, or lesson schema. |
| Retrieve a relevant prior episode | **Partially aligned** | Condensed research findings are semantically searchable and can point back to a research session. Conversation/research replay APIs retrieve known sessions by ID. | The system cannot generally search whole past episodes by semantic similarity, time range, tags, or outcome. |
| Reason over earlier outcomes | **Partially aligned** | Relevant prior research memories are injected into later planning and generation. | Only extracted findings participate; the full earlier plan/action/outcome trajectory is not automatically recalled. |
| Episode consolidation | **Gap** | No periodic process converts old session logs into durable episode summaries. | Potentially useful after real workload data exists; not required immediately. |

### Episodic-memory conclusion

ResearchMind has durable episodic evidence but not a first-class episodic memory service. The current design is effective for audit and replay, while semantic cross-session recall depends on extracted research findings rather than retrieval of entire past episodes.

This is a reasonable staged architecture. A dedicated episode model is only justified if users need questions such as:

- “What happened in the research session where we rejected web search?”
- “Find earlier runs with similar evidence gaps.”
- “Reuse the successful workflow from last month's climate comparison.”

---

## 8. External and tool memory

| Criterion | Status | Current alignment | Gap or limitation |
|---|---|---|---|
| Programmatic memory service | **Strongly aligned** | `MemoryService` exposes remember, recall, search, context, update, and forget operations. | None at the application-service layer. |
| Authenticated memory API | **Strongly aligned** | `/memory` endpoints support remember, semantic search, context assembly, recall, update, and delete, scoped to the current user. | API consumers must decide when and why to call the operations. |
| Agent-selected memory read | **Gap** | Orchestration automatically retrieves memory before relevant model calls. | The LLM/agent cannot independently decide to call `SearchMemory` midway through a reasoning loop. |
| Agent-selected memory write | **Gap** | Post-turn extraction and deterministic runtime logic decide writes. | The agent cannot autonomously call `SaveMemory` as a tool during a multi-step task. |
| Tool descriptions and schemas | **Gap for memory tools** | The HTTP/API schemas are structured. | No native agent tool registration with carefully bounded descriptions was found. |
| Approval for sensitive writes | **Not applicable to current automated path** | Memory extraction is constrained to low-risk user/research facts and is owner-scoped. | There is no user confirmation before automatic durable memory extraction. |
| Long-running agent work state | **Partially aligned** | Research run state, events, artifacts, and approval checkpoints persist outside the LLM context. | PostgreSQL LangGraph checkpointing is disabled by default; full recovery from graph checkpoints is not the standard deployment path. |

### Architectural judgment

Not exposing memory as a general autonomous tool is not necessarily a defect.

The current deterministic pattern:

1. retrieves memory at known safe boundaries;
2. injects it with explicit “background memory” framing;
3. writes memory only after a completed user-facing turn;
4. runs an extraction policy and structured classifier;
5. keeps failures from breaking the main task.

This is easier to secure and evaluate than unrestricted agent memory tools. Agent-driven memory tools become valuable if future workflows need mid-run cross-referencing, but they should include strict owner scope, read/write separation, provenance, budgets, and approval policies.

---

## 9. Memory-augmented RAG pipeline

The reference pipeline is:

`User Query → Memory Retrieval → Document Retrieval → Prompt Assembly → LLM Response → Memory Update`

### Current Chat path

| Stage | Current implementation | Alignment |
|---|---|---|
| User query | User prompt enters an owner-scoped conversation. | **Aligned** |
| Conversation history | Older history is compacted; recent messages and summary are loaded. | **Strongly aligned** |
| Memory retrieval | Session, semantic, and research memories are retrieved before generation; semantic/research branches may run in parallel. | **Strongly aligned** |
| Other retrieval | Optional web and paper evidence are gathered. | **Aligned and broader than the reference** |
| Prompt assembly | Memory is prepended as explicitly labeled background; web and paper evidence are appended; transcript contains recent/summary history and the current query. | **Strongly aligned** |
| LLM response | Generation runtime routes the request and streams the answer. | **Aligned** |
| Persist turn | Completed user and assistant messages are stored canonically. | **Strongly aligned** |
| Update session memory | Current-topic state is distilled and upserted, unless raw-turn storage is explicitly enabled. | **Strongly aligned** |
| Extract durable memory | Eligible turns are classified and stored as user preferences or research findings. | **Strongly aligned** |

### Current Research path

| Stage | Current implementation | Alignment |
|---|---|---|
| Query and conversation | Research conversation/session is owner-scoped and persisted. | **Aligned** |
| Memory retrieval | Memory context is retrieved ahead of Linear Research generation, Deep Research proposal/planning, and execution stages. | **Strongly aligned** |
| Knowledge retrieval | Hybrid document retrieval and optional broader evidence gathering run separately from memory retrieval. | **Strongly aligned** |
| Planner context | Relevant memories can influence research planning and proposal generation. | **Strongly aligned** |
| Generation and evidence | Memory is background; documents/evidence remain the citable knowledge source. | **Strong architectural separation** |
| Persist outcome | Research runs, evidence, reports, costs, events, and artifacts are stored. | **Strongly aligned** |
| Update memory | Session state and durable research findings are extracted after completed user-facing work. | **Strongly aligned** |

### Key strength

The memory block is explicitly framed as potentially unrelated background that should be used only when directly relevant. This reduces the risk that an old memory is mistaken for the current question or authoritative retrieved evidence.

### Key weakness

Conversation history and memory are injected for response generation, but normal document retrieval does not universally rewrite the search query using that memory. The model may understand a follow-up after retrieval while the retriever itself searched the unresolved phrase.

---

## 10. Memory creation and update quality

| Criterion | Status | Current alignment | Gap or limitation |
|---|---|---|---|
| Extract after successful user-facing turns | **Aligned** | Chat and Research share post-turn extraction orchestration. | Extraction should not run on failed, cancelled, or untrusted outputs; current policy checks final user-facing status. |
| Local eligibility before LLM extraction | **Strongly aligned** | Trivial, short, empty, non-final, and non-durable turns are skipped cheaply. | Rules are language- and phrase-dependent. |
| Structured extraction output | **Strongly aligned** | Extraction uses a strict model for memory content, type, and importance. | Structured validity does not ensure factual correctness. |
| Cheap model and fallback | **Aligned** | The composition prefers inexpensive providers and can fall back. | Fallback consistency should be monitored. |
| Fail-open enrichment | **Aligned** | Extraction failure does not fail the completed Chat/Research turn. | Users may believe explicit “remember this” succeeded when it did not unless UX surfaces status. |
| Idempotent processing | **Aligned** | A Redis key prevents repeated extraction of the same turn and policy version. | If Redis is unavailable, extraction continues without the idempotency guarantee. |
| Exact duplicate update | **Aligned** | Exact matches update provenance and retain maximum importance. | Normalization in the SQL expression may not be identical to Python whitespace normalization for all inputs. |
| Provenance metadata | **Aligned** | Source turn, policy version, and optional research ID are attached. | Model/provider version, source citations, and extraction confidence are not consistently first-class fields. |
| User correction | **Aligned for preferences** | Memory CRUD supports explicit correction, and the USER supersession policy can update a matching preference in place. | General contradiction handling and temporal versioning for semantic/research facts remain deferred. |
| Memory confidence | **Partially aligned** | Importance is stored. | Importance is not the same as extraction confidence or truth confidence; those dimensions are not separated. |

---

## 11. Memory retrieval and context assembly

| Criterion | Status | Current alignment | Gap or limitation |
|---|---|---|---|
| Retrieve by semantic relevance | **Strongly aligned** | Semantic and research memories use Qdrant cosine similarity. | No lexical memory search for exact names, IDs, or rare terms. |
| Enforce a relevance floor | **Aligned** | `memory_search_score_threshold` defaults to 0.5. | One threshold may not suit both personal facts and research findings. |
| Avoid unnecessary vector calls | **Strongly aligned** | Durable-memory availability is cached; vector retrieval is skipped for owners with no durable memories. | Cache invalidation correctness is critical and is explicitly handled on writes/deletes. |
| Parallel category search | **Aligned** | Semantic and research branches run concurrently by default. | Partial branch failures quietly reduce context. |
| Fuse search result lists | **Aligned for explicit search** | Reciprocal-rank fusion preserves each backend's ranking and deduplicates by memory ID. | Per-turn `get_context()` keeps categories separate rather than fusing globally. |
| Deduplicate memory and transcript | **Aligned** | Redundant raw session entries are removed when canonical transcript already contains them. | Durable semantic/research memories can still paraphrase each other. |
| Bound injected items | **Strongly aligned** | One coordinated token budget, per-type shares, whole-entry inclusion, evidence/output reserves, and omission counts bound session, user, semantic, and research context. | Token estimation remains approximate rather than provider-tokenizer-specific. |
| Label memory categories | **Strongly aligned** | Prompt formatting distinguishes active session state, durable user preferences, semantic knowledge, and prior research findings. | The coordinated budget can omit lower-priority entries and reports those omissions. |
| Separate memory from evidence | **Strongly aligned** | Memory modifies prompt text without changing document chunks or citation records. | Old research memory can influence an answer without itself being directly citable unless the linked research artifact is resolved. |
| Retrieval observability | **Aligned operationally** | Context latency, durable availability, skips, search latency, parallel searches, hits/misses, result counts, and artifacts are recorded. | No measured precision/recall or usefulness label for recalled memories. |

---

## 12. Persistence, lifecycle, and forgetting

| Criterion | Status | Current alignment | Gap or limitation |
|---|---|---|---|
| Short-term TTL | **Aligned** | Session memory has a seven-day default TTL. | TTL refresh on state updates can extend the current-topic record indefinitely during active use, which is reasonable. |
| Durable long-term store | **Strongly aligned** | User, semantic, and research memories persist in PostgreSQL. | Retention is otherwise open-ended unless deleted or swept. |
| Separate vector index | **Aligned** | Qdrant is a search index; PostgreSQL remains the source of truth. | Vector upsert/delete failures are logged and may temporarily desynchronize search from canonical records. |
| Explicit recall by ID | **Aligned** | Owner-scoped recall API works across memory types. | Generic recall tries backends sequentially when type is unknown. |
| User update | **Aligned** | Owner-scoped update supports content, metadata, and importance changes. | Content updates reindex vector-backed memories, but profile semantics and contradiction handling remain manual. |
| User forgetting | **Strongly aligned** | Owner-scoped deletion removes the database row and vector point where applicable. | Session-index lists retain deleted IDs until expiry, though missing records are ignored. |
| Cascade on user deletion | **Aligned for PostgreSQL** | Memory rows use an owner foreign key with cascade deletion. | External indexes/caches require coordinated cleanup beyond the database cascade. |
| Importance-based retention | **Aligned, rollout pending** | Low-importance writes are skipped; a recurring worker evaluates per-type age and importance policies. | Production deletion remains disabled until operators review dry-run candidates. |
| Hot/warm/cold/archive lifecycle | **Gap by design** | The lifecycle module explicitly postpones tiering until real usage data exists. | No archive state or retrieval-aware decay. |
| Time decay | **Gap** | Created/updated timestamps exist. | Retrieval ranking does not combine semantic relevance with recency decay. |
| Consolidation | **Aligned foundation; rollout pending** | The lifecycle worker can run bounded, separately gated M8 consolidation batches with same-scope vector nomination, typed decisions, reversible lineage, and compensated vector/database updates. | It defaults disabled and dry-run until reviewed samples demonstrate no false merges or Recall@K regression. |
| Scheduled cleanup | **Aligned, rollout pending** | A dedicated recurring worker invokes `sweep_stale()` under a Valkey singleton lock and exports metrics. | It intentionally defaults to dry-run; production must explicitly enable deletion. |

---

## 13. Privacy, security, and governance

| Criterion | Status | Current alignment | Gap or limitation |
|---|---|---|---|
| Owner-scoped storage and retrieval | **Strongly aligned** | All user-facing database and vector operations include owner scope. | Administrative lifecycle sweep can intentionally span owners and must remain operator-only. |
| User-accessible memory CRUD | **Strongly aligned** | `/memory` provides Personal and authorized Project inventories, filters, edit review, move support through the API, settings, export, and confirmed selected/full-scope erasure. | The broader Project product must still supply authorized runtime context before project-scoped generation traffic is activated. |
| Data minimization | **Aligned in extraction policy** | The system skips most turns and stores only candidate durable preferences/findings. Raw session-turn storage is disabled by default because canonical history already exists. | Research findings and profile facts may still include sensitive data extracted from conversation content. |
| Consent for automatic memory | **Partially aligned** | Personal and per-project capture can be disabled independently without deleting retained memory; project inheritance and retrieval are separate controls. | Category-specific permission and a per-conversation “never remember this” control are not implemented. |
| PII filtering before memory storage | **Gap** | General input/output PII guardrails exist elsewhere in the platform. | Memory extraction/storage does not visibly anonymize or block PII before persistence and embedding. |
| Deletion from all stores | **Strongly aligned for memory-owned data** | M14 jobs delete canonical rows and vectors, purge scope state/caches where applicable, remove derived memory artifacts, verify completion, and retain content-free audit state for retry. | Canonical conversation history is a separate product record, and encrypted backups remain until published backup expiry. |
| Memory injection safety | **Strongly aligned** | Durable memory is framed as untrusted quoted data inside explicit delimiters; embedded closing delimiters are escaped and current system/current-turn instructions take precedence. | Continue adversarial testing as prompts and providers evolve. |
| Provenance | **Partially aligned** | Source turn, research ID, policy version, timestamps, and owner are retained. | The exact source quote/citation and extraction model version are not uniformly preserved. |
| Auditability | **Aligned operationally** | Memory artifacts, structured logs, metrics, and canonical conversations support investigation. | Automated user-facing explanations for why a memory was recalled are absent. |

---

## 14. Reliability and checkpointing

| Criterion | Status | Current alignment | Gap or limitation |
|---|---|---|---|
| Memory failure does not break Chat/Research | **Aligned** | Retrieval, extraction, state distillation, Valkey operations, and vector searches generally fail open with logs. | Availability is favored over continuity; a degraded answer may silently lack memory. |
| Canonical conversation durability | **Strongly aligned** | Completed turns persist in PostgreSQL independently of session-memory availability. | None material. |
| Durable research run records | **Strongly aligned** | Runs, dispatch, events, checkpoints/approvals, evidence, and artifacts are persisted in domain records. | This is application-level state, not necessarily a fully restorable graph checkpoint. |
| Graph checkpoint implementation | **Available, not default** | An async PostgreSQL saver and provisioning function exist. | The module states it is not wired to startup; the setting defaults to disabled. |
| Session-memory durability | **Intentionally limited** | Valkey memory is TTL-bound and not the source of truth for conversation history. | A Valkey loss removes distilled session state until it is rebuilt by future turns. |
| Vector/database consistency | **Partially aligned** | PostgreSQL is authoritative and vector hits are hydrated from owner-scoped rows. | Cross-store writes are not transactional; failed index operations can create temporary missing or stale search entries. |

---

## 15. Observability and memory evaluation

| Criterion | Status | Current alignment | Gap or limitation |
|---|---|---|---|
| Remember latency | **Aligned** | Dedicated duration metric exists. | None material. |
| Search/context latency | **Aligned** | Search, context, durable search, and embedding latencies are measured and visualized. | Alert thresholds still require production calibration. |
| Hit/miss counts | **Aligned** | Memory hit and miss metrics exist. | A hit is not proof that the memory helped the answer. |
| Retrieval-path metrics | **Strongly aligned** | Durable availability, empty/skip state, parallel search, semantic/research searches, and loaded session items are tracked. M6 includes Recall@5/Precision@5/MRR/nDCG scoring, authenticated API capture, paired answer utility, and release budgets. | The first live staging baseline, human calibration, and final budget calibration remain. |
| Extraction metrics | **Strongly aligned** | Evaluated, skipped, requested, rate-limited, success, failure, empty, created, updated, superseded, and duplicate metrics are registered and visualized. | No broad human-labeled extraction corpus yet. |
| Artifacts | **Aligned** | Search and context artifacts persist inputs and results for debugging. | Retention and PII controls for these artifacts need explicit governance. |
| Memory usefulness | **Aligned foundation** | M7 correlates recalled memory to generation traces, accepts explicit feedback, and records sampled utility/harm scores; M11 visualizes their trends. | Sampling and thresholds require staging/production calibration. |
| Extraction accuracy | **Partially aligned** | Structured output, typed preference tests, M6 fixtures, and explicit feedback provide measurable signals. | The labeled extraction corpus remains narrow. |
| Personalization quality | **Aligned foundation** | USER memory is automatically injected and M6 paired memory-on/off evaluation measures downstream answer impact. | Human calibration and live deployment gates remain. |
| Contradiction/staleness rate | **Partially aligned** | M8 classifies consolidation relationships with reversible lineage; lifecycle age/failure and consolidation outcomes are visible. | Generic cross-fact contradiction detection is not implemented. |
| User trust controls | **Strongly aligned** | Personal and Project views provide pagination, search/filtering, provenance, edit review, capture/inheritance controls, export, and server-confirmed selected/full-scope erasure; explicit utility feedback is available on eligible answers. | Category-specific capture consent and per-conversation exclusion remain product-policy gaps. |

### Recommended memory-specific evaluation metrics

| Metric | What it should answer |
|---|---|
| Memory extraction precision | Of the facts saved, how many were genuinely durable and correct? |
| Memory extraction recall | Of the durable facts users expected to be remembered, how many were saved? |
| Type accuracy | Was the memory classified correctly as user preference, research finding, or another category? |
| Recall relevance@K | Were injected memories relevant to the current question? |
| Harmful recall rate | How often did stale, contradictory, or unrelated memory worsen an answer? |
| Memory utilization | Did the generated answer actually use the recalled memory? |
| Correction success | When a user corrected a memory, was the old version removed or superseded? |
| Forget completeness | Was a deleted memory removed from every canonical, vector, cache, and artifact location required by policy? |
| Memory-added latency | What p50/p95 latency does availability check, embedding, retrieval, and formatting add? |
| Personalization success | Do persisted preferences measurably improve user-rated answers? |

---

## 16. Strong alignments

| Capability | Why it aligns with production memory practice |
|---|---|
| Separate canonical and retrieval stores | PostgreSQL provides ownership and CRUD; Qdrant is only the semantic search index. |
| Multiple memory categories | Session, user, semantic, and research facts have distinct storage and retrieval behavior. |
| Canonical conversation history plus bounded prompt history | Complete history is retained while model context remains controlled. |
| Session-topic distillation | Creates compact state specifically for ambiguous follow-ups without retaining unlimited raw turns in Valkey. |
| Memory-before-generation injection | Both Chat and Research retrieve memory at defined orchestration boundaries. |
| Selective post-turn extraction | The system does not indiscriminately store every exchange. |
| Importance threshold | Low-value memories are rejected at write time. |
| Exact deduplication and provenance update | Repeat extractions do not create an unbounded pile of identical records. |
| Semantic relevance threshold | Unrelated “nearest” memories are not automatically treated as relevant. |
| Owner-filtered vector retrieval | Cross-user memory leakage is structurally constrained. |
| Explicit forget/update APIs | Memory is correctable and deletable rather than immutable hidden state. |
| Fail-open memory enrichment | Memory outages do not take down the primary Chat/Research operation. |
| Rich operational metrics | The memory pipeline is observable as its own production subsystem. |

---

## 17. Misalignments and meaningful gaps

| Area | Current behavior | Reference/industry expectation | Consequence |
|---|---|---|---|
| User preference consumption | User memories are persisted and included in normal context assembly under a coordinated budget. | Stable preferences personalize future sessions. | Quality evaluation and product-level preference controls still need hardening. |
| Episodic retrieval | Sessions and runs are replayable by known identifiers. | Relevant prior episodes can be searched by meaning, time, tags, and outcome. | Cross-session workflow reuse depends on extracted findings rather than whole episodes. |
| Agent tool memory | Orchestrator controls reads/writes. | Agent can choose save/search memory tools during long tasks. | Mid-run memory lookup is unavailable, but safety and determinism are better. |
| Semantic memory creation | Explicit API can store semantic memory; automatic extraction creates only user/research types. | General durable facts can enter semantic memory automatically. | Semantic context may remain empty unless another caller writes it. |
| Contradiction handling | Exact duplicates merge; differing facts coexist. | Newer corrections supersede or version older facts. | Conflicting preferences/findings can both be recalled. |
| Temporal validity | Created/updated timestamps only. | Facts have validity windows, subjects, versions, and confidence. | Old facts may remain semantically relevant after becoming false. |
| Lifecycle automation | TTL exists; a recurring singleton worker evaluates configurable per-type stale policies and separately gated M8 consolidation, both defaulting to dry-run. | Production deletion/consolidation rollout, decay, and archive policies. | Durable stores continue growing until operators approve and enable live mutation. |
| Privacy consent | Automatic extraction enabled globally. | User/category-level consent and sensitive-memory policies. | Users may not know durable facts are being extracted. |
| Memory-specific security | Owner isolation and background framing exist. | Stored-memory sanitization and prompt-injection defenses. | Malicious remembered text could influence later prompts. |
| Quality evaluation | Detailed operational metrics. | Labeled extraction/recall/usefulness and harm evaluation. | High hit rates can conceal irrelevant or harmful memories. |

---

## 18. Gaps that do not necessarily need implementation

| Gap | Recommendation |
|---|---|
| Autonomous `SaveMemory`/`SearchMemory` tools | Do not add merely for framework parity. Add only when agents need mid-run recall that deterministic preloading cannot provide. |
| Full episodic vector database | Defer until users need semantic retrieval of complete prior sessions rather than extracted findings. |
| Hot/warm/cold/archive tiers | Defer until corpus growth and recall patterns provide evidence for retention boundaries. |
| Memory time decay | Benchmark first. Some stable preferences should not decay, while transient facts should. A single global formula would be harmful. |
| LLM-based consolidation | Defer until duplicates and contradictions are measured; consolidation can incorrectly merge distinct facts. |
| Native multi-message provider history | Useful, but the current transcript representation already provides continuity. Prioritize only if provider-role semantics measurably improve quality. |
| Raw-turn duplication in session memory | Current default correctly avoids it because canonical conversation history already stores the full turn. |

---

## 19. Prioritized improvement plan

| Priority | Improvement | Reason | Suggested acceptance evidence |
|---|---|---|---|
| **Done (M0)** | Include applicable `USER` preferences in runtime memory context | The stored profile now affects later turns within a bounded coordinated prompt budget. | Owner-scoped injection and precedence tests are in place. |
| **Done (M1)** | Add USER preference correction semantics | New applicable USER preferences can supersede an existing row instead of accumulating contradictions. | Supersession tests are in place; general temporal fact versioning remains future work. |
| **Done for M12-M16; policy follow-up remains** | Complete memory privacy controls | Scope-aware enumeration/mutations, independent settings, confirmed moves, Personal/Project UI, portable export, server-confirmed cross-store erasure, and cross-tenant tests are implemented. | Add sensitive-category restrictions, memory-specific PII tests, and per-conversation capture exclusion if product policy requires them. |
| **P0, operational rollout (M6)** | Complete the memory evaluation dataset and regression suite | The versioned dataset, scorer, live capture adapter, paired answer judge, persistence, provisional budgets, and deterministic CI gate are implemented. | Seed and capture staging, human-calibrate answer judgments and budgets, then enforce the live staging gate. |
| **Rollout (M3)** | Enable stale-memory lifecycle deletion after dry-run review | The recurring worker, policies, locking, metrics, and report-only default are implemented. | Reviewed candidate counts, alerting, explicit `DRY_RUN=false`, and PostgreSQL/Qdrant consistency checks. |
| **Done (M16), continue regression coverage** | Delimit memory as untrusted prompt data | Stored memory is untrusted historical text. | Explicit delimiters, closing-tag escaping, and precedence regressions are implemented; extend the adversarial corpus as providers change. |
| **P1** | Preserve richer provenance | Enables trust, correction, and traceability. | Source quote/message ID, extraction model/prompt version, research citation IDs, confidence, and timestamps. |
| **P1** | Add lexical or hybrid memory retrieval for exact terms | Semantic-only recall can miss identifiers, names, acronyms, and exact citations. | Benchmark showing Recall@K lift on exact-term memory queries without unrelated recall. |
| **P2** | Add first-class episode summaries if demanded by use cases | Enables reuse of prior workflows and outcomes. | Episode schema, semantic/tag/time search, and tests on prior-run retrieval. |
| **P2** | Expose bounded memory tools to agents if mid-run recall is required | Supports long multi-step autonomous research. | Separate read/write tools, owner scope, budgets, provenance, approval policy, and full trace coverage. |
| **P2** | Enable durable graph checkpointing when operationally ready | Improves resumability of long research graphs. | Startup provisioning, recovery tests, schema migration plan, checkpoint retention, and cleanup policy. |

---

## 20. Code evidence map

| Concern | Primary implementation evidence |
|---|---|
| Memory types and canonical models | `apps/api/app/ai/memory/enums.py`, `apps/api/app/ai/memory/models.py` |
| Memory orchestration | `apps/api/app/ai/memory/services/memory_service.py` |
| Memory API | `apps/api/app/api/v1/memory.py` |
| Session memory | `apps/api/app/ai/memory/session/service.py`, `storage/valkey_store.py` |
| Session-topic distillation | `apps/api/app/ai/memory/session/state_updater.py` |
| User/profile memory | `apps/api/app/ai/memory/profile/service.py` |
| Semantic memory | `apps/api/app/ai/memory/semantic/service.py` |
| Research memory | `apps/api/app/ai/memory/research/service.py` |
| Vector-backed memory behavior | `apps/api/app/ai/memory/storage/vector_backed_service.py` |
| Memory vector index | `apps/api/app/ai/memory/storage/vector_index.py` |
| Durable memory storage | `apps/api/app/ai/memory/storage/postgres_store.py`, `apps/api/app/models/memory.py` |
| Memory extraction | `apps/api/app/ai/memory/extraction/service.py` |
| Extraction orchestration/idempotency | `apps/api/app/ai/memory/extraction/orchestrator.py` |
| Extraction policy | `apps/api/app/ai/memory/policy/service.py` |
| Repeated-interest promotion | `apps/api/app/ai/memory/policy/interest_promotion.py` |
| Importance scoring | `apps/api/app/ai/memory/importance.py` |
| Memory fusion | `apps/api/app/ai/memory/retrieval/fusion.py` |
| Durable availability optimization | `apps/api/app/ai/memory/retrieval/availability.py` |
| Prompt formatting/injection | `apps/api/app/ai/memory/services/formatting.py` |
| Chat memory integration | `apps/api/app/api/v1/chat.py` |
| Chat history compaction | `apps/api/app/services/conversation.py`, `conversation_compaction.py` |
| Research memory integration | `apps/api/app/ai/research/service.py` |
| Deep Research memory integration | `apps/api/app/ai/runtime/research/proposal_service.py`, `execution.py` |
| Memory lifecycle | `apps/api/app/ai/memory/lifecycle/service.py` |
| Memory observability | `apps/api/app/ai/memory/observability/` |
| Memory artifacts | `apps/api/app/ai/memory/artifacts/` |
| Memory settings | `apps/api/app/core/settings.py` |
| Research checkpoint construction | `apps/api/app/ai/runtime/research/checkpointing.py` |
| Conversations and messages | `apps/api/app/models/conversation.py`, `apps/api/app/repositories/conversation.py` |
| Research episodes/runs/events | `apps/api/app/models/research*.py`, `apps/api/app/repositories/research*.py` |

---

## 21. Final conclusion

ResearchMind AI aligns strongly with industry memory architecture in the areas that matter most for a stateful research assistant:

- durable conversation continuity;
- bounded short-term context;
- cross-session semantic recall;
- research finding memory;
- selective automatic extraction;
- importance filtering;
- ownership isolation;
- explicit correction and forgetting;
- memory-augmented Chat and Research generation;
- operational observability.

It should be described as a **multi-tier memory platform with session, profile, semantic, and research memory**, not merely a chat-history buffer.

The most important next work is not adding every memory pattern from the reference images. It is making the current system safer and more effective:

1. consume the user preferences it already stores;
2. handle corrections, contradictions, and temporal validity;
3. add user consent and sensitive-memory governance;
4. evaluate memory relevance and usefulness, not only hits and latency;
5. automate the existing stale-memory lifecycle;
6. preserve richer provenance for recalled facts.

Agent-controlled memory tools and first-class episodic retrieval are valid future extensions, but they are not prerequisites for industry alignment at the platform's current stage.
