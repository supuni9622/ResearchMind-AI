# ResearchMind Memory Platform Optimization Plan

**Document:** `memory_platform_optimization_plan.md`  
**Status:** Implemented; awaiting staged live-traffic validation
**Priority:** High  
**Target:** Optimize the existing Memory Platform without redesigning or over-engineering it  
**Primary runtime surfaces:** Chat and Research  
**Implementation style:** Incremental, backward-compatible, measurable, production-safe

---

## 1. Purpose

ResearchMind's Memory Platform is functionally complete and safely integrated into both Chat and Research. However, the current runtime performs more memory work than necessary on every completed generation.

The goal of this optimization is to reduce:

- unnecessary LLM extraction calls
- duplicate prompt context
- avoidable embedding and Qdrant operations
- serial memory-retrieval latency
- Groq/OpenAI rate-limit pressure
- memory-related generation cost
- noisy traces and low-value memory writes

This plan does **not** replace the current Memory Platform architecture. It improves the existing implementation while preserving:

- the current four memory types
- canonical PostgreSQL storage
- Qdrant as the semantic/research search index
- Valkey session memory
- best-effort memory behavior
- current `/memory` API contracts
- existing Chat and Research behavior
- provider fallback for memory extraction

### Implementation addendum — 2026-07-19

The optimization is implemented without replacing the original four-memory
architecture. The baseline flow in §2 is intentionally retained as the
pre-optimization reference.

- Durable retrieval now checks owner-scoped availability first, computes a
  query embedding once, and searches SEMANTIC and RESEARCH memory concurrently;
  either search can fail without dropping the other branch or SESSION context.
- SESSION storage now holds compact state rather than raw Q/A transcript
  copies. Canonical persisted conversation/research history remains the source
  for transcript context.
- Policy version `v2` evaluates only final user-facing turns. It uses canonical
  Chat message/turn IDs for idempotency and excludes future planner, reviewer,
  tool, retry, and helper nodes by default.
- LLM extraction remains available where it adds value: an explicit statement
  of a durable interest is eligible immediately; a generic lexical topic needs
  two distinct sessions, then receives one owner/topic-bound LLM validation
  protected by a 90-day claim. Assistant inferences are never profile evidence.
- PostgreSQL remains canonical. USER memory is persisted there; durable
  SEMANTIC/RESEARCH memory is indexed in Qdrant for retrieval. Promotion does
  not write directly to a vector index or backfill prior traffic.
- Structured decision/failure/latency events and `/usage/summary` distinguish
  answer-generation cost from `memory_extraction` cost. The remaining work is
  representative staged/production observation, not synthetic ledger traffic.

Focused verification completed: 19 Memory Platform unit tests and 16 Chat /
Research regression tests passed. See ADR-029 and
`docs/architecture/memory-platform.md` §26 for the original-versus-optimized
architecture record.

### Chat-history companion delivery — 2026-07-19

The optimization does not rely on raw SESSION-memory transcript copies to
control Chat context growth. That concern is now handled explicitly at the
canonical Chat layer: cursor pagination replays older persisted rows on demand,
while ADR-030's deterministic rolling summary keeps the generation transcript
bounded (newest 12 messages verbatim; older history capped at 4,000 summary
characters). This preserves the four-memory design and adds neither an LLM
extraction nor a provider cost.

---

## 2. Current State

The current Memory Platform supports:

| Memory type | Storage | Purpose |
|---|---|---|
| `SESSION` | Valkey | Short-lived conversation/session state |
| `USER` | PostgreSQL | Stable user preferences and profile-like facts |
| `SEMANTIC` | PostgreSQL + Qdrant | Durable semantically retrievable knowledge |
| `RESEARCH` | PostgreSQL + Qdrant | Durable research findings and research-specific knowledge |

The runtime currently performs the following flow for most Chat and Research turns:

```text
Request
  ↓
Load persisted conversation history
  ↓
Read SESSION memory from Valkey
  ↓
Search SEMANTIC memory
      → query embedding
      → Qdrant search
  ↓
Search RESEARCH memory
      → query embedding again
      → Qdrant search
  ↓
Format and inject memory context
  ↓
Generate answer
  ↓
Persist conversation/research turn
  ↓
Store raw turn as SESSION memory
  ↓
Run MemoryExtractionService using an LLM
  ↓
Persist extracted USER / RESEARCH memories
```

### Already optimized

The current implementation already includes useful optimizations:

- query embeddings are cached in Valkey
- query embedding cache TTL is approximately 24 hours
- session-memory reads use batched Valkey operations
- memory extraction fails open
- extraction failures do not break the answer path
- Groq is the primary extraction provider
- OpenAI is the fallback extraction provider
- memory importance filtering already exists
- Qdrant is only a search index; PostgreSQL remains canonical
- semantic/research search results use Reciprocal Rank Fusion

### Current inefficiencies

1. Semantic and research memory searches execute sequentially.
2. Each durable-memory service asks for the query embedding independently.
3. The second embedding request is usually a cache hit, but still performs another cache lookup and another service call.
4. Durable-memory retrieval runs even when the user has no semantic or research memories.
5. Durable-memory extraction runs after every answer.
6. Trivial turns still trigger an LLM extraction request.
7. Generic questions can trigger extraction even when no durable memory is possible.
8. SESSION memory duplicates persisted conversation history.
9. Duplicate context increases prompt tokens without adding information.
10. Internal Research Runtime nodes could later accidentally trigger memory extraction if extraction remains coupled to all generation calls.
11. Memory behavior is not yet covered by a dedicated automated test suite.
12. Current metrics do not clearly reveal extraction usefulness, skip rate, duplicate rate, or durable-memory retrieval efficiency.

---

## 3. Architectural Decision

### Decision

Introduce a lightweight **Memory Runtime Policy layer** between completed runtime events and expensive memory operations.

The new rule is:

> Every completed Chat or Research turn may be evaluated for memory, but not every completed turn should invoke the memory extraction LLM.

The target runtime flow is:

```text
Request
  ↓
Persisted conversation history
  ↓
SESSION memory containing only non-history state
  ↓
Durable Memory Availability Check
  ↓
If durable memory exists:
    embed query once
    search SEMANTIC + RESEARCH concurrently
  ↓
Generation
  ↓
Always persist canonical conversation/research state
  ↓
Always update required SESSION state
  ↓
Memory Eligibility Gate
  ├── SKIP
  ├── EXTRACT_SYNC
  └── EXTRACT_ASYNC_READY
```

For this milestone, `EXTRACT_ASYNC_READY` may still execute inline after streaming completes if no job infrastructure exists. The policy contract must nevertheless distinguish it so the future Research Runtime or worker platform can move extraction to a background job without redesigning memory logic.

---

## 4. Scope

### In scope

- one query embedding per memory-context retrieval
- concurrent semantic and research Qdrant searches
- durable-memory existence checks
- retrieval short-circuiting for users with no durable memories
- cheap extraction eligibility gate
- explicit extraction decisions
- session-memory de-duplication against persisted history
- memory-specific metrics and tracing metadata
- configuration flags and thresholds
- unit and integration tests
- backward-compatible migration of Chat and Research call sites
- clear separation between canonical history, session state, and durable memory

### Out of scope

Do not implement the following in this optimization:

- memory reflection
- autonomous memory consolidation
- hot/warm/cold memory tiers
- memory decay redesign
- agent-shared memory
- LangGraph memory checkpoints
- background queue infrastructure
- embedding model changes
- Qdrant collection redesign
- PostgreSQL schema redesign unless a minimal existence query/index is required
- full memory relevance evaluation platform
- automatic summarization of full conversations
- replacing persisted conversation history with SESSION memory
- caching final extraction results across mutable memory versions
- extracting memory from every internal future Research Runtime node

---

## 5. Target Ownership Boundaries

The optimization must preserve these boundaries.

### Conversation Platform owns

- canonical chat messages
- conversation ordering
- conversation replay
- persisted multi-turn history
- conversation title
- user and assistant message storage

### Research Platform owns

- research conversations
- research turns
- research sessions and artifacts
- grounded answers and citations
- future planner/workflow state

### Memory Platform owns

- memory retrieval decisions
- memory eligibility decisions
- session-state memory
- durable-memory extraction
- memory de-duplication
- memory persistence
- memory lifecycle
- memory-specific observability

### Generation Platform owns

- provider routing
- generation
- structured output
- validation
- guardrails
- retries
- fallback
- generation caching
- generation observability

### Critical rule

`GenerationService` and `GenerationRuntime` must **not** automatically extract memory.

Chat, Research, and future runtimes emit or call memory processing at their runtime boundary after a meaningful completed turn.

---

## 6. Target Runtime Flows

## 6.1 Chat

```text
Chat request
  ↓
Load canonical persisted transcript
  ↓
Load non-history SESSION state
  ↓
Check whether user has durable memories
  ↓
If yes:
    create query embedding once
    run semantic and research memory searches concurrently
  ↓
Build memory context
  ↓
De-duplicate memory context against transcript
  ↓
Generate streamed answer
  ↓
Persist canonical user + assistant turn
  ↓
Update SESSION state
  ↓
Evaluate extraction policy
  ├── SKIP
  ├── EXTRACT_SYNC
  └── EXTRACT_ASYNC_READY
  ↓
If extraction selected:
    run MemoryExtractionService
    de-duplicate/update memories
    persist useful memories
```

## 6.2 Research

```text
Research request
  ↓
Load research conversation history
  ↓
Load non-history SESSION state
  ↓
Check whether user has durable memories
  ↓
If yes:
    create query embedding once
    run semantic and research memory searches concurrently
  ↓
Retrieve document evidence
  ↓
Build grounded prompt context
  ↓
Inject only relevant, non-duplicate memory context
  ↓
Generate research answer/report
  ↓
Persist research turn and artifact
  ↓
Update SESSION state
  ↓
Evaluate extraction policy only for the final user-facing turn
  ↓
Skip extraction for internal planner/retriever/reviewer/tool nodes
```

---

## 7. Implementation Milestones

# Milestone 1 — Baseline Instrumentation

**Goal:** Measure current memory behavior before changing it.

### Add metrics

Extend `apps/api/app/ai/memory/observability/metrics.py` with:

```text
memory_context_requests_total
memory_context_durable_available_total
memory_context_durable_empty_total
memory_context_retrieval_skipped_total

memory_query_embedding_requests_total
memory_query_embedding_cache_hits_total
memory_query_embedding_cache_misses_total

memory_semantic_search_total
memory_research_search_total
memory_parallel_search_total

memory_extraction_evaluated_total
memory_extraction_skipped_total
memory_extraction_requested_total
memory_extraction_succeeded_total
memory_extraction_failed_total
memory_extraction_empty_total

memory_created_total
memory_updated_total
memory_duplicate_total

memory_session_items_loaded_total
memory_session_items_injected_total
memory_session_duplicates_removed_total

memory_context_latency_ms
memory_embedding_latency_ms
memory_durable_search_latency_ms
memory_extraction_latency_ms
```

### Add structured logs

Recommended events:

```text
memory.context.started
memory.context.completed
memory.context.skipped_durable_retrieval

memory.retrieval.embedding.completed
memory.retrieval.parallel.completed

memory.extraction.policy_decided
memory.extraction.started
memory.extraction.completed
memory.extraction.skipped
memory.extraction.failed

memory.session.deduplicated
```

### Required metadata

Every memory operation should include where available:

```text
owner_id
session_id
conversation_id
research_id
runtime
query_length
has_durable_memory
policy_action
policy_reasons
semantic_result_count
research_result_count
session_result_count
extracted_count
created_count
updated_count
duplicate_count
provider
model
latency_ms
```

### Acceptance criteria

- Existing runtime behavior remains unchanged.
- LangSmith and structlog can distinguish answer generation from memory extraction.
- The extraction usefulness ratio can be calculated:

```text
useful_memory_writes / memory_extraction_requested_total
```

- Empty extraction rate can be calculated.
- Durable retrieval skip rate can be calculated after later milestones.

---

# Milestone 2 — Durable Memory Availability Check

**Goal:** Avoid embedding and Qdrant work for users with no semantic or research memories.

## 2.1 Add repository capability

Add a lightweight existence/count method to the canonical PostgreSQL memory store.

Suggested interface:

```python
class PostgresMemoryStore:
    async def exists_for_owner(
        self,
        *,
        owner_id: UUID,
        memory_types: set[MemoryType],
    ) -> bool:
        ...
```

Alternative:

```python
async def count_for_owner_by_type(
    self,
    *,
    owner_id: UUID,
) -> dict[MemoryType, int]:
    ...
```

Prefer `exists_for_owner()` for the first implementation because it is cheaper and sufficient for the runtime gate.

### Query behavior

Use an indexed `EXISTS` query:

```sql
SELECT EXISTS (
    SELECT 1
    FROM memories
    WHERE owner_id = :owner_id
      AND type IN ('semantic', 'research')
    LIMIT 1
);
```

Verify the existing `owner_id` and `type` indexes. Add a composite index only if query analysis shows it is needed:

```text
(owner_id, type)
```

Do not add a migration without checking existing indexes first.

## 2.2 Add availability service

Recommended file:

```text
apps/api/app/ai/memory/retrieval/availability.py
```

Suggested contract:

```python
class DurableMemoryAvailabilityService:
    async def has_durable_memory(
        self,
        *,
        owner_id: UUID,
    ) -> bool:
        ...
```

## 2.3 Add short-lived Valkey cache

A durable-memory existence result changes rarely relative to request frequency.

Suggested key:

```text
memory:durable-exists:{owner_id}
```

Suggested values:

```text
1
0
```

Suggested TTL:

```text
60–300 seconds
```

Default recommendation:

```text
120 seconds
```

### Invalidation

Set or invalidate the key when:

- semantic memory is created
- research memory is created
- the last semantic/research memory is deleted
- lifecycle sweep deletes durable memories
- memory type changes between durable and non-durable categories

A simple safe first implementation:

- set `1` after a successful durable-memory write
- delete the cache key after any durable-memory delete
- let a cached `0` expire naturally after a short TTL

## 2.4 Integrate with `MemoryService.get_context()`

Target behavior:

```python
if not await availability_service.has_durable_memory(owner_id=owner_id):
    return MemoryContext(
        session_memories=session_memories,
        semantic_memories=[],
        research_memories=[],
    )
```

### Acceptance criteria

- New users with no semantic/research memory do not call the query embedding service.
- New users with no semantic/research memory do not query Qdrant.
- SESSION memory still loads normally.
- A newly created durable memory becomes searchable immediately or within the documented short TTL.
- Cache/backend failures fail open by performing the durable-memory check or search rather than breaking the request.

---

# Milestone 3 — Embed Once and Search Concurrently

**Goal:** Remove duplicate embedding-service calls and serial search latency.

## 3.1 Current problem

`SemanticMemoryService.search()` and `ResearchMemoryService.search()` independently call the shared `QueryEmbeddingService`.

Even with a Valkey cache hit, the current path still performs:

```text
semantic search
  → query embedding cache lookup
  → Qdrant search
then
research search
  → query embedding cache lookup
  → Qdrant search
```

## 3.2 Add embedding-aware search contracts

Do not expose provider SDK objects. Continue using the canonical query embedding model.

Recommended additions to `VectorBackedMemoryService`:

```python
async def search_with_embedding(
    self,
    *,
    owner_id: UUID,
    query: str,
    embedding: DenseQueryEmbedding,
    top_k: int,
) -> list[MemorySearchResult]:
    ...
```

Keep the existing public `search()` method for backward compatibility:

```python
async def search(...):
    embedding = await self._query_embedding_service.embed(query)
    return await self.search_with_embedding(
        owner_id=owner_id,
        query=query,
        embedding=embedding,
        top_k=top_k,
    )
```

## 3.3 Add memory retrieval orchestrator

Recommended file:

```text
apps/api/app/ai/memory/retrieval/service.py
```

Suggested contract:

```python
class DurableMemoryRetrievalService:
    async def search(
        self,
        *,
        owner_id: UUID,
        query: str,
        semantic_top_k: int,
        research_top_k: int,
    ) -> DurableMemoryRetrievalResult:
        ...
```

Suggested result:

```python
class DurableMemoryRetrievalResult(BaseModel):
    semantic_memories: list[MemorySearchResult]
    research_memories: list[MemorySearchResult]
    embedding_cache_hit: bool | None = None
    embedding_latency_ms: float
    search_latency_ms: float
```

If `QueryEmbeddingService` does not expose cache-hit metadata today, do not force a large refactor. Add that metadata only if it can be done cleanly.

## 3.4 Run Qdrant searches concurrently

```python
semantic_results, research_results = await asyncio.gather(
    semantic_memory_service.search_with_embedding(...),
    research_memory_service.search_with_embedding(...),
)
```

### Failure behavior

Use best-effort isolation:

```python
results = await asyncio.gather(
    semantic_call,
    research_call,
    return_exceptions=True,
)
```

A failure in one memory category should not remove successful results from the other category.

Log failures separately:

```text
memory.semantic_search.failed
memory.research_search.failed
```

Do not fail the Chat or Research request.

## 3.5 Integrate with `MemoryService.get_context()`

`MemoryService.get_context()` should orchestrate:

1. SESSION memory read
2. durable-memory availability check
3. one embedding
4. concurrent semantic/research search
5. canonical `MemoryContext` construction

### Acceptance criteria

- Only one query-embedding service call occurs per memory-context retrieval.
- Semantic and research Qdrant searches execute concurrently.
- A failure in one search branch preserves the other branch.
- Existing `SemanticMemoryService.search()` and `ResearchMemoryService.search()` remain usable.
- Existing `/memory/search` behavior remains backward-compatible.
- Memory context ordering remains deterministic.

---

# Milestone 4 — Memory Extraction Eligibility Policy

**Goal:** Stop calling the extraction LLM for low-value turns.

## 4.1 Add policy package

Recommended structure:

```text
apps/api/app/ai/memory/policy/
├── __init__.py
├── enums.py
├── models.py
├── eligibility.py
├── signals.py
├── config.py
└── service.py
```

## 4.2 Add canonical action enum

```python
class MemoryExtractionAction(str, Enum):
    SKIP = "skip"
    EXTRACT_SYNC = "extract_sync"
    EXTRACT_ASYNC_READY = "extract_async_ready"
```

## 4.3 Add canonical decision model

```python
class MemoryExtractionDecision(BaseModel):
    action: MemoryExtractionAction
    reasons: list[str]
    candidate_types: list[MemoryType] = Field(default_factory=list)
    explicit_request: bool = False
    confidence: float | None = None
```

## 4.4 Add runtime event model

Avoid passing loosely structured arguments from each caller.

```python
class MemoryTurnEvent(BaseModel):
    owner_id: UUID
    session_id: UUID | str
    runtime: Literal["chat", "research", "planner", "reviewer", "agent", "tool"]
    user_message: str
    assistant_message: str
    conversation_id: UUID | None = None
    research_id: UUID | None = None
    is_final_user_facing_turn: bool = True
```

## 4.5 Deterministic skip rules

The policy must skip extraction without an LLM call when any of these apply:

### Runtime/source exclusions

```text
planner
retriever
reranker
context_builder
reviewer
validator
guardrail
tool
internal_helper
title_generation
memory_extraction
```

Only final user-facing Chat and Research turns should currently be eligible.

### Trivial-turn exclusions

Examples:

```text
thanks
thank you
ok
okay
great
got it
continue
yes
no
sure
cool
bye
```

Use normalized exact matching plus limited punctuation removal.

Do not implement an over-broad fuzzy classifier that may suppress meaningful messages.

### Minimum-content checks

Initial default thresholds:

```text
minimum user characters: 12
minimum user tokens estimate: 3
```

These checks should not suppress explicit memory requests.

### Generic informational questions

A generic question alone should not normally create durable memory:

```text
What is RAG?
How does BM25 work?
Explain LangGraph.
```

Do not rely only on the presence of `?`. Use positive durable signals instead.

## 4.6 Positive durable-memory signals

Start with deterministic patterns for:

### Explicit memory intent

```text
remember this
remember that
save this
keep this in mind
note this
from now on
going forward
do not forget
```

Action:

```text
EXTRACT_SYNC
```

### User preference

Examples:

```text
I prefer ...
I like ...
I do not want ...
Always use ...
Please avoid ...
```

Candidate type:

```text
USER
```

### Stable goal

Examples:

```text
My goal is ...
I am planning to ...
I want to become ...
I am building ...
```

Candidate type:

```text
USER
```

Only save goals that appear reasonably durable. The LLM extractor remains responsible for final judgment.

### Correction or supersession

Examples:

```text
That is no longer correct.
Use X instead of Y.
I changed my decision.
From now on, ...
```

Action:

```text
EXTRACT_SYNC
```

### Architecture/project decision

Examples:

```text
We decided to ...
We will use ...
The architecture is frozen as ...
Do not use CrewAI for ResearchMind.
```

Candidate type:

```text
RESEARCH
```

### Research finding or conclusion

Examples:

```text
The benchmark showed ...
The result confirms ...
Our evaluation found ...
The research conclusion is ...
```

Candidate type:

```text
RESEARCH
```

Default action:

```text
EXTRACT_ASYNC_READY
```

## 4.7 Default policy

Recommended initial behavior:

```text
Explicit remember/correction
  → EXTRACT_SYNC

Positive durable signal
  → EXTRACT_ASYNC_READY

No durable signal
  → SKIP
```

Because no queue runtime currently exists, Chat and Research may process `EXTRACT_ASYNC_READY` best-effort after the response has completed. The action remains distinct for future worker migration.

## 4.8 No LLM classifier in this milestone

Do not replace one unconditional extraction LLM call with another unconditional classification LLM call.

Eligibility must be:

- deterministic
- cheap
- local
- testable
- configurable

The existing extraction LLM performs the final semantic decision only after the gate passes.

### Acceptance criteria

- “Thanks” does not invoke the extraction LLM.
- “What is RAG?” does not invoke the extraction LLM.
- “Remember that I prefer concise answers” invokes extraction.
- “We decided to use LangGraph for Research Runtime” invokes extraction.
- Internal runtime events never invoke extraction.
- Extraction remains best-effort.
- Existing provider fallback remains unchanged.
- Policy reasons are logged and measurable.

---

# Milestone 5 — Extraction Orchestration Service

**Goal:** Remove duplicate extraction logic from Chat and Research.

## 5.1 Add orchestration service

Recommended file:

```text
apps/api/app/ai/memory/extraction/orchestrator.py
```

Suggested contract:

```python
class MemoryExtractionOrchestrator:
    async def process_turn(
        self,
        event: MemoryTurnEvent,
    ) -> MemoryExtractionOutcome:
        ...
```

Suggested outcome:

```python
class MemoryExtractionOutcome(BaseModel):
    decision: MemoryExtractionDecision
    extracted_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    duplicate_count: int = 0
    failed: bool = False
```

## 5.2 Orchestration responsibilities

```text
receive completed turn
  ↓
evaluate eligibility
  ↓
if SKIP:
    return
  ↓
run MemoryExtractionService
  ↓
for each extracted candidate:
    validate allowed type
    score importance
    check for duplicate/superseded memory
    remember/update through MemoryService
  ↓
record metrics
  ↓
return outcome
```

## 5.3 Preserve extraction service responsibility

`MemoryExtractionService` should continue to:

- call Generation Runtime
- use structured output
- use Groq primary
- use OpenAI fallback
- return `ExtractedMemory`
- fail open
- clamp importance score

It should **not** own:

- runtime eligibility
- Chat/Research source filtering
- session-state persistence
- duplicate transcript detection
- asynchronous scheduling

## 5.4 Idempotency

Add a lightweight completed-turn idempotency key.

Suggested key:

```text
memory:extraction:{owner_id}:{runtime}:{turn_id}:{policy_version}
```

If a canonical turn ID exists, use it.

For Chat:

```text
conversation turn artifact ID or assistant message ID
```

For Research:

```text
research turn ID or research execution ID
```

Avoid hashing only message content because identical content may appear in different legitimate turns.

Suggested TTL:

```text
7 days
```

Value:

```json
{
  "status": "completed",
  "extracted_count": 1,
  "processed_at": "..."
}
```

A failed extraction should generally not be marked completed unless retries are intentionally suppressed.

## 5.5 Version the policy

Add:

```text
MEMORY_EXTRACTION_POLICY_VERSION=v1
```

Include the version in:

- idempotency key
- metrics metadata
- logs
- future artifacts

### Acceptance criteria

- Chat and Research call one shared extraction orchestrator.
- The same completed turn cannot be extracted twice accidentally.
- Explicit memory requests remain immediately processed.
- Extraction failures do not affect the main response.
- Policy logic is not duplicated across HTTP, SSE, and WebSocket paths.

---

# Milestone 6 — SESSION Memory De-duplication

**Goal:** Stop injecting conversation history twice.

## 6.1 Define the role of SESSION memory

SESSION memory should contain temporary, non-canonical state such as:

- active task
- pending clarification
- selected documents
- current research scope
- active filters
- temporary user constraints
- unresolved decisions
- current workflow step
- UI/runtime state that is useful across turns

SESSION memory should not mirror:

- raw user messages
- raw assistant messages
- full transcript
- entire generated answers already stored in canonical history

## 6.2 Change session write policy

Current behavior stores every raw turn as SESSION memory.

Replace it with one of these incremental options.

### Preferred initial option

Stop writing the full raw assistant answer into SESSION memory.

Store a compact structured session record only when needed:

```python
class SessionStateMemory(BaseModel):
    kind: str
    content: str
    source_turn_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

Examples:

```json
{
  "kind": "active_goal",
  "content": "Optimize the Memory Platform before starting Research Runtime."
}
```

```json
{
  "kind": "pending_clarification",
  "content": "User has not chosen whether memory extraction should become background queued."
}
```

### Transitional option

If raw turn storage must remain temporarily:

- do not inject raw SESSION entries already present in persisted history
- tag session entries with `source_message_id` or `source_turn_id`
- remove matching entries during context formatting

## 6.3 Add context de-duplication service

Recommended file:

```text
apps/api/app/ai/memory/retrieval/deduplication.py
```

Suggested contract:

```python
class MemoryContextDeduplicationService:
    def deduplicate(
        self,
        *,
        context: MemoryContext,
        transcript: str | list[Message],
    ) -> MemoryContext:
        ...
```

Initial matching strategy:

1. exact normalized text match
2. matching `source_message_id` / `source_turn_id`
3. conservative containment check for sufficiently long text

Do not introduce embedding-based de-duplication in the request path for this milestone.

## 6.4 Formatting rules

Update `services/formatting.py` to:

- omit empty memory categories
- cap entries per category
- truncate excessively large session state
- keep USER/SEMANTIC/RESEARCH labels clear
- never inject duplicate raw history
- keep citations unaffected
- keep memory outside `PromptContext.chunks`

Suggested default caps:

```text
session memories: 5
semantic memories: 5
research memories: 5
```

These should be settings-driven.

### Acceptance criteria

- The canonical transcript remains the source of truth for conversation history.
- SESSION memory no longer duplicates the whole transcript.
- Existing multi-turn Chat and Research behavior remains intact.
- Prompt token usage decreases for repeated conversations.
- Memory citations and document citations remain separate.
- No semantic de-duplication LLM call is added.

---

# Milestone 7 — Configuration

Add settings with conservative defaults.

Suggested settings:

```env
MEMORY_DURABLE_RETRIEVAL_ENABLED=true
MEMORY_DURABLE_AVAILABILITY_CACHE_ENABLED=true
MEMORY_DURABLE_AVAILABILITY_TTL_SECONDS=120

MEMORY_PARALLEL_SEARCH_ENABLED=true
MEMORY_SEMANTIC_TOP_K=5
MEMORY_RESEARCH_TOP_K=5

MEMORY_EXTRACTION_POLICY_ENABLED=true
MEMORY_EXTRACTION_POLICY_VERSION=v1
MEMORY_EXTRACTION_MIN_USER_CHARACTERS=12
MEMORY_EXTRACTION_MIN_USER_TOKENS=3
MEMORY_EXTRACTION_IDEMPOTENCY_TTL_SECONDS=604800

MEMORY_SESSION_RAW_TURN_STORAGE_ENABLED=false
MEMORY_SESSION_MAX_CONTEXT_ITEMS=5
MEMORY_SEMANTIC_MAX_CONTEXT_ITEMS=5
MEMORY_RESEARCH_MAX_CONTEXT_ITEMS=5

MEMORY_CONTEXT_DEDUPLICATION_ENABLED=true
```

### Rollout flags

Each major optimization should be independently switchable:

- availability short-circuit
- parallel search
- extraction gate
- session de-duplication
- raw session-turn storage

This enables safe production rollout and rapid rollback.

---

# Milestone 8 — Chat Integration

Update all live Chat paths:

```text
POST /api/v1/chat/stream
/api/v1/chat/ws
```

## Required changes

1. Load canonical transcript first.
2. Call optimized `MemoryService.get_context()`.
3. Pass the transcript to memory de-duplication.
4. Inject memory context once.
5. Generate the response.
6. Persist the canonical turn.
7. Update structured SESSION state.
8. Build a `MemoryTurnEvent`.
9. Call `MemoryExtractionOrchestrator.process_turn()`.
10. Do not call `MemoryExtractionService` directly.

## WebSocket rule

The WebSocket path uses plain-Python factories and its own `AsyncSession`.

Update composition roots so the WebSocket path receives the same:

- availability service
- durable retrieval service
- extraction policy service
- extraction orchestrator
- idempotency service

Do not create a separate WebSocket-specific memory implementation.

### Acceptance criteria

- SSE and WebSocket behavior match.
- New conversations with no durable memories avoid embeddings/Qdrant.
- Trivial Chat messages do not trigger extraction.
- Explicit memory requests do trigger extraction.
- Conversation replay remains unchanged.
- No duplicate prompt history is injected.

---

# Milestone 9 — Research Integration

Update:

```text
apps/api/app/ai/research/service.py
```

## Required changes

1. Preserve current hybrid document retrieval.
2. Load optimized memory context independently from document evidence.
3. De-duplicate SESSION memory against research conversation history.
4. Inject durable memory only once.
5. Persist the final research turn and artifact.
6. Process memory only for the final user-facing research answer.
7. Do not attach extraction to internal future graph nodes.

## Future-proof runtime-source rule

The policy must be able to receive:

```text
runtime=research
is_final_user_facing_turn=true
```

Future nodes should use:

```text
runtime=planner
runtime=reviewer
runtime=tool
runtime=internal_helper
```

Those must default to `SKIP`.

## Research findings

Do not automatically save full reports as memory.

Save only compact durable findings or decisions selected by the extractor.

Research artifacts remain the canonical source for full report content.

### Acceptance criteria

- Research remains grounded in document evidence.
- Memory context does not become citation evidence.
- Full reports are not copied into memory.
- Internal future Research Runtime calls are excluded by policy.
- Follow-up research conversations retain useful state without duplicated transcript tokens.

---

# Milestone 10 — Tests

The Memory Platform currently lacks dedicated automated coverage. This optimization must add it.

## 10.1 Unit tests

Recommended structure:

```text
tests/unit/ai/memory/
├── policy/
│   ├── test_eligibility.py
│   └── test_service.py
├── retrieval/
│   ├── test_availability.py
│   ├── test_parallel_retrieval.py
│   └── test_deduplication.py
├── extraction/
│   ├── test_orchestrator.py
│   └── test_idempotency.py
├── services/
│   └── test_memory_service_context.py
└── formatting/
    └── test_formatting.py
```

### Required policy tests

| Input | Expected |
|---|---|
| `Thanks` | `SKIP` |
| `Okay, continue` | `SKIP` |
| `What is RAG?` | `SKIP` |
| `Remember that I prefer concise answers` | `EXTRACT_SYNC` |
| `From now on, use Groq by default` | `EXTRACT_SYNC` |
| `We decided to use LangGraph for Research Runtime` | extraction eligible |
| planner runtime output | `SKIP` |
| reviewer runtime output | `SKIP` |
| final research conclusion | extraction eligible |
| empty assistant response | `SKIP` or safe no-op |

### Required retrieval tests

- no durable memory → embedding service not called
- no durable memory → Qdrant not called
- durable memory → embedding called once
- semantic and research searches both receive the same embedding
- searches execute concurrently
- semantic failure preserves research results
- research failure preserves semantic results
- both failures return session-only context
- availability cache fails open
- memory retrieval remains owner-scoped

### Required de-duplication tests

- exact transcript duplicate removed
- source message ID duplicate removed
- unrelated session state preserved
- semantic memory matching transcript conservatively removed
- short common phrases are not over-deduplicated

### Required extraction tests

- skipped decision does not call LLM
- eligible decision calls extraction once
- idempotent turn does not call extraction twice
- empty extraction result is recorded
- provider failure fails open
- invalid extracted type is rejected
- importance threshold remains enforced
- durable write invalidates availability cache

## 10.2 Integration tests

Implement:

```text
tests/integration/test_memory.py
```

Required scenarios:

1. New user, first Chat question.
2. User with no durable memory.
3. User explicitly asks to remember a preference.
4. Next Chat turn retrieves that preference.
5. Trivial follow-up does not extract.
6. Research final answer can save a compact finding.
7. Research report body is not copied wholesale into memory.
8. SESSION state does not duplicate canonical transcript.
9. SSE and WebSocket produce equivalent memory side effects.
10. Owner A cannot retrieve Owner B memory.

## 10.3 Regression tests

Add regression coverage to existing Chat/Research tests:

- response still succeeds when memory backend fails
- response still succeeds when extraction provider fails
- memory extraction does not run on cache-hit replay unless a new canonical turn was actually completed
- repeated stream-completion events do not duplicate extraction
- fallback provider usage is recorded correctly
- extraction cost is categorized as `memory_extraction`

---

## 8. Data and Cache Safety

## 8.1 Do not use Generation Runtime cache as the Memory Platform cache

Memory extraction depends on mutable state:

- owner
- current durable memories
- message/turn identity
- policy version
- extraction schema version

A generic prompt cache may return stale or cross-context results.

## 8.2 Safe caches

### Query embedding cache

Keep the existing 24-hour Valkey query-embedding cache.

### Durable-memory availability cache

Add a short TTL owner-level cache.

### Extraction idempotency cache

Cache processed turn identity, not generic extraction output.

### Optional memory-context cache

Do not implement initially.

If later required, the key must include:

```text
owner_id
query hash
memory version
session id
policy version
```

A memory version mechanism does not currently exist, so defer this cache.

## 8.3 Tenant isolation

Every key and query must remain scoped by:

```text
owner_id
```

Where relevant also include:

```text
session_id
conversation_id
research_id
```

No memory cache key may omit owner scope.

---

## 9. Observability and Success Metrics

Track the following before and after rollout.

## 9.1 Primary targets

Initial target ranges:

| Metric | Target |
|---|---:|
| extraction calls skipped | 50–80% |
| empty extraction rate | under 20% |
| duplicate memory write rate | under 10% |
| query embedding calls per memory context | 1 maximum |
| Qdrant durable searches for users with no memory | 0 |
| durable search branches | concurrent |
| memory-caused request failures | 0 |
| duplicate session/transcript prompt tokens | materially reduced |

These are starting targets, not permanent SLOs. Tune after real usage data.

## 9.2 Cost metrics

Use the existing owner-scoped generation usage ledger and ensure memory extraction remains categorized as:

```text
memory_extraction
```

Compare:

```text
memory extraction cost per 100 user turns
```

before and after optimization.

## 9.3 Latency metrics

Compare:

```text
memory context P50/P95 latency
durable memory retrieval P50/P95 latency
query embedding P50/P95 latency
memory extraction P50/P95 latency
```

The main user-facing latency improvement should come from:

- durable retrieval short-circuit
- parallel Qdrant search
- extraction decoupling from response completion where possible

---

## 9.4 Staged live-traffic validation procedure

The implementation emits the required structured events now; target values
must only be declared after a representative, owner-scoped traffic window.
Do not create synthetic provider calls or insert ledger rows solely to make
the metrics look complete.

1. Deploy the current API to staging (or start the normal local API with
   `./scripts/dev.sh`) with structured application logs retained.
2. Select one test account and record its authenticated
   `GET /api/v1/usage/summary` response immediately before the window.
3. Send a representative mix of at least 30 completed Chat and Research
   answer turns, including trivial follow-ups, substantive preference/fact
   turns, repeated questions, and users with and without durable memories.
4. Record the same owner's `/usage/summary` response after the window. Use
   the deltas in `answer_turns`, `memory_extraction_requests`, and
   `memory_extraction_cost_usd`; the endpoint also returns the resulting
   `memory_extraction_cost_per_100_turns`.
5. Aggregate the structured log events for the same time window:

   - counters: `memory.extraction_evaluated`, `memory.extraction_skipped`,
     `memory.extraction_requested`, `memory.extraction_empty`,
     `memory.extraction_failed`, `memory.context_retrieval_skipped`, and
     `memory.duplicate`;
   - durations: `memory.extraction_latency`, `memory.context_latency`, and
     `memory.durable_search_latency` from `memory.metric.duration` events.

   Calculate extraction skip rate as `skipped / evaluated`, empty extraction
   rate as `empty / requested`, and P50/P95 from each duration event's
   `duration_ms`. Keep the event time, owner/session/conversation scope, and
   deployment revision in the query so unrelated traffic is not mixed in.
6. Compare the resulting values with the targets in §9.1, investigate any
   failed extraction or memory-caused request failure, and retain the before/
   after summary plus the log query in the rollout record.

The current recorder intentionally writes stable structured log events rather
than introducing a memory-specific metrics backend. A future shared
Prometheus/OpenTelemetry sink can consume the same metric names without
changing the Memory call sites.

### Interest-promotion policy

LLM extraction is not removed; it remains the final validator for durable
profile memories. Explicit statements such as “I am learning RAG” are eligible
immediately. A generic topic is tracked with a bounded lexical candidate only;
after it appears in two distinct sessions, one LLM validation may promote it to
a `USER` research-interest memory. A per-owner/topic claim prevents subsequent
new sessions from repeatedly paying for the same promotion during the 90-day
retention window. The assistant's own inferences are never evidence for a
profile write.

---

## 10. Rollout Strategy

## Phase A — Observe

Enable baseline metrics with no behavior changes.

Duration:

```text
1–3 days of local/staging testing
```

## Phase B — Retrieval optimization

Enable:

- durable-memory availability gate
- one embedding
- parallel semantic/research search

Keep extraction behavior unchanged temporarily.

Validate:

- context quality
- owner isolation
- latency
- failure handling

## Phase C — Extraction gate

Enable deterministic policy in staging.

Start with conservative rules:

- skip acknowledgements
- skip short generic turns
- allow explicit remember intent
- allow clear preference/decision signals

Inspect:

- skipped examples
- false negatives
- extraction usefulness ratio

## Phase D — Session de-duplication

Disable raw turn storage in SESSION memory behind a flag.

Validate:

- multi-turn continuity
- prompt token reduction
- Chat and Research history behavior
- no lost temporary state

## Phase E — Production default

Make optimized behavior the default after tests and trace review pass.

Keep rollback flags for at least one release cycle.

---

## 11. Suggested File Changes

### New files

```text
apps/api/app/ai/memory/policy/__init__.py
apps/api/app/ai/memory/policy/enums.py
apps/api/app/ai/memory/policy/models.py
apps/api/app/ai/memory/policy/signals.py
apps/api/app/ai/memory/policy/eligibility.py
apps/api/app/ai/memory/policy/service.py

apps/api/app/ai/memory/retrieval/availability.py
apps/api/app/ai/memory/retrieval/service.py
apps/api/app/ai/memory/retrieval/deduplication.py

apps/api/app/ai/memory/extraction/orchestrator.py
apps/api/app/ai/memory/extraction/idempotency.py
```

### Existing files likely to change

```text
apps/api/app/ai/memory/create.py
apps/api/app/ai/memory/models.py
apps/api/app/ai/memory/services/memory_service.py
apps/api/app/ai/memory/services/formatting.py
apps/api/app/ai/memory/storage/postgres_store.py
apps/api/app/ai/memory/storage/vector_backed_service.py
apps/api/app/ai/memory/semantic/service.py
apps/api/app/ai/memory/research/service.py
apps/api/app/ai/memory/session/service.py
apps/api/app/ai/memory/extraction/service.py
apps/api/app/ai/memory/observability/metrics.py

apps/api/app/ai/research/service.py
apps/api/app/api/v1/chat.py

apps/api/app/config/settings.py
.env.example
```

Codex must inspect the actual repository paths before editing. Some settings may live under AI-specific settings rather than the global config module.

### Tests

```text
tests/unit/ai/memory/
tests/integration/test_memory.py
tests/integration/ai/test_chat_stream.py
tests/unit/ai/research/
```

---

## 12. Developer Execution Order

Codex should implement in this exact order.

### Step 1

Inspect the current memory call graph:

```text
MemoryService.get_context()
SemanticMemoryService.search()
ResearchMemoryService.search()
VectorBackedMemoryService
MemoryExtractionService
chat.py
ResearchService
```

Document exact current signatures before editing.

### Step 2

Add baseline metrics and tests around current behavior.

### Step 3

Add `PostgresMemoryStore.exists_for_owner()` and its tests.

### Step 4

Add durable-memory availability service and short TTL cache.

### Step 5

Add `search_with_embedding()` to vector-backed memory services while preserving `search()`.

### Step 6

Add durable retrieval orchestrator with one embedding and concurrent searches.

### Step 7

Update `MemoryService.get_context()` to use availability + optimized retrieval.

### Step 8

Add extraction policy models, deterministic rules, and tests.

### Step 9

Add extraction idempotency and orchestration service.

### Step 10

Replace direct extraction calls in Chat and Research.

### Step 11

Add SESSION memory de-duplication and disable raw turn duplication behind a flag.

### Step 12

Add integration tests and run the full quality suite.

---

## 13. Quality Gates

Before marking complete, all must pass:

```bash
ruff format --check .
ruff check .
mypy apps/api/app
pytest
```

Also run targeted tests:

```bash
pytest tests/unit/ai/memory -q
pytest tests/integration/test_memory.py -q
pytest tests/integration/ai/test_chat_stream.py -q
```

Perform live verification in LangSmith:

1. Ask `What is RAG?`
   - one answer generation trace
   - no extraction trace

2. Send `Thanks`
   - no extraction trace

3. Send `Remember that I prefer concise answers`
   - extraction trace exists
   - durable memory created

4. Ask a follow-up
   - durable memory retrieved
   - one embedding operation
   - semantic and research searches concurrent

5. Test a new user
   - no query embedding
   - no Qdrant durable-memory searches

6. Trigger Groq extraction rate limit
   - OpenAI fallback works
   - answer path remains successful

---

## 14. Definition of Done

This optimization is complete when:

- memory extraction no longer runs after every generation
- a deterministic policy controls extraction eligibility
- explicit memory requests still work immediately
- generic and trivial turns skip extraction
- users with no durable memory skip embedding and Qdrant retrieval
- semantic and research memory searches share one query embedding
- semantic and research searches execute concurrently
- Chat and Research use one shared extraction orchestrator
- SESSION memory no longer duplicates canonical conversation history
- memory failures remain non-blocking
- tenant isolation remains intact
- memory behavior has dedicated unit and integration tests
- metrics show extraction skip rate, usefulness, duplicates, cost, and latency
- existing APIs remain backward-compatible
- Research artifacts remain canonical for full reports
- future internal LangGraph nodes are excluded from automatic extraction by default

Implementation status: all code, migration-safe behavior, metrics, and focused
test coverage above are complete. The only open Definition-of-Done item is to
measure the staged/live-traffic targets in §9.4 with representative traffic.

---

## 15. Non-Negotiable Engineering Constraints

1. Do not move Memory Platform behavior into Generation Platform.
2. Do not call an LLM merely to decide whether to call the extraction LLM.
3. Do not make memory failures block Chat or Research.
4. Do not share memory cache entries across owners.
5. Do not store full research reports as durable memory.
6. Do not use SESSION memory as a duplicate transcript database.
7. Do not break existing `/memory` API contracts.
8. Do not remove existing provider fallback.
9. Do not bypass canonical PostgreSQL ownership for durable memories.
10. Do not add broad new infrastructure such as queues or LangGraph solely for this optimization.
11. Do not extract memory from internal future planner, reviewer, tool, or validation nodes.
12. Do not over-engineer memory consolidation before real usage data exists.

---

## 16. Final Target Architecture

```text
┌────────────────────────────────────────────────────────────┐
│ Chat / Research Runtime                                    │
└───────────────────────────┬────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ Canonical Conversation / Research History                  │
└───────────────────────────┬────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ Memory Context Service                                     │
│                                                            │
│  1. Load non-history SESSION state                         │
│  2. Check durable-memory availability                      │
│  3. Embed query once                                       │
│  4. Search SEMANTIC + RESEARCH concurrently                │
│  5. De-duplicate against canonical transcript              │
│  6. Format bounded memory context                          │
└───────────────────────────┬────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ Generation Runtime                                         │
└───────────────────────────┬────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ Persist Canonical Turn / Artifact                          │
└───────────────────────────┬────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ Memory Extraction Orchestrator                             │
│                                                            │
│  Policy Gate                                               │
│   ├── SKIP                                                 │
│   ├── EXTRACT_SYNC                                         │
│   └── EXTRACT_ASYNC_READY                                  │
│                                                            │
│  Idempotency                                               │
│  LLM Extraction                                            │
│  Importance Filter                                         │
│  De-duplicate / Update / Persist                           │
│  Metrics                                                   │
└────────────────────────────────────────────────────────────┘
```

This design keeps the existing Memory Platform intact while making its runtime behavior materially cheaper, faster, and more production-appropriate.
