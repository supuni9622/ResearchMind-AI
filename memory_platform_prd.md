# ResearchMind Memory Platform PRD
Version: 1.0
Status: Approved
Phase: 11.23
Owner: AI Platform

---

# 1. Overview

The Memory Platform is responsible for storing, retrieving,
managing and reasoning over information across conversations,
research sessions and future agent executions.

Memory is a first-class platform.

It exists independently from:

- Retrieval Platform
- Research Runtime
- Agent Runtime
- Workspace Runtime

The platform provides persistent intelligence.

---

# 2. Goals

Enable ResearchMind to:

✅ remember conversations

✅ remember user preferences

✅ remember research findings

✅ remember previous reports

✅ remember useful facts

✅ support long-running research sessions

✅ support future agent collaboration

✅ support workspace experiences

---

# 3. Non Goals

Memory platform DOES NOT:

❌ perform reasoning

❌ execute workflows

❌ perform planning

❌ own research sessions

❌ own LangGraph state

❌ own retrieval

❌ own report generation

These responsibilities belong to:

- Research Runtime
- Agent Runtime
- Retrieval Platform

---

# 4. Architectural Principles

Memory is platform-owned.

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

LangGraph memory is never exposed outside providers.

---

# 5. Platform Responsibilities

The platform owns:

1. Session Memory
2. User Memory
3. Research Memory
4. Semantic Memory
5. Memory Search
6. Memory Lifecycle
7. Memory APIs
8. Memory Observability
9. Memory Artifacts

---

# 6. Memory Types

---

# 6.1 Session Memory

Purpose:

Remember active conversations.

Examples:

- previous messages
- generated answers
- retrieved context
- intermediate state

Characteristics:

- short lived
- fast access
- high read frequency

Storage:

Valkey

TTL:

7 days

---

# 6.2 User Memory

Purpose:

Remember user preferences.

Examples:

- favorite models
- writing style
- response preferences
- preferred providers
- research interests

Characteristics:

- persistent
- low write frequency

Storage:

PostgreSQL

---

# 6.3 Research Memory

Purpose:

Remember research outputs.

Examples:

- reports
- evidence
- findings
- citations
- generated artifacts

Characteristics:

- persistent
- versioned

Storage:

Postgres
S3
Vector Memory

---

# 6.4 Semantic Memory

Purpose:

Remember useful facts.

Examples:

- user likes markdown reports
- user frequently researches climate papers
- user uses Claude for reasoning

Characteristics:

- searchable
- embedding powered

Storage:

Qdrant

---

# 7. Memory Architecture

```text
Memory Service

├── Session Memory
├── User Memory
├── Research Memory
└── Semantic Memory
```

---

# 8. Folder Structure

```text
app/

    ai/

        memory/

            api/

            contracts/

            models/

            services/

            providers/

            session/

            profile/

            research/

            semantic/

            storage/

            artifacts/

            observability/

            factories/

            registries/

            create.py
```

---

# 9. Platform Components

---

# 9.1 Memory Service

Main orchestration service.

Responsibilities:

- remember
- recall
- search
- forget
- update

---

# 9.2 Session Memory Service

Responsibilities:

- conversation history
- message storage
- context retrieval

---

# 9.3 User Memory Service

Responsibilities:

- preference management
- profile updates

---

# 9.4 Semantic Memory Service

Responsibilities:

- embeddings
- similarity search
- long term facts

---

# 9.5 Research Memory Service

Responsibilities:

- reports
- findings
- evidence
- citations

---

# 10. Canonical Models

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

# MemorySearchRequest

```python
class MemorySearchRequest(BaseModel):
    query: str

    owner_id: UUID

    memory_types: list[MemoryType]

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

# MemoryContext

```python
class MemoryContext(BaseModel):
    session_memories: list[MemoryRecord]

    semantic_memories: list[MemoryRecord]

    research_memories: list[MemoryRecord]
```

---

# 11. Memory Types Enum

```python
class MemoryType(str, Enum):

    SESSION
    USER
    RESEARCH
    SEMANTIC
```

---

# 12. APIs

---

# Remember

```python
remember()
```

Stores memory.

---

# Recall

```python
recall()
```

Fetch exact memory.

---

# Search

```python
search_memories()
```

Semantic search.

---

# Forget

```python
forget()
```

Deletes memory.

---

# Update

```python
update_memory()
```

Updates memory.

---

# 13. Public APIs

---

POST /memory

POST /memory/search

GET /memory/{id}

PUT /memory/{id}

DELETE /memory/{id}

GET /memory/context

---

# 14. Storage Strategy

---

# Valkey

Stores:

- sessions
- chat history
- active runtime state

Characteristics:

- low latency
- TTL

---

# PostgreSQL

Stores:

- profiles
- reports metadata
- preferences
- structured memory

---

# Qdrant

Stores:

- semantic memory embeddings
- searchable long term facts

---

# S3

Stores:

- reports
- artifacts
- snapshots

---

# 15. Memory Lifecycle

```text
Interaction

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

Indexing
```

---

# 16. Importance Scoring

Purpose:

Avoid remembering everything.

Examples:

Low:

```text
hello
thanks
yes
```

High:

```text
favorite providers
research preferences
important findings
```

Score:

```python
0.0 → 1.0
```

---

# 17. Memory Extraction

Memory extraction is performed by LLMs.

Output:

```python
class ExtractedMemory(BaseModel):

    content: str

    type: MemoryType

    importance: float
```

This allows future automatic memory generation.

---

# 18. Search Flow

```text
Query

↓

Embed Query

↓

Semantic Search

↓

Rerank

↓

Memory Context
```

---

# 19. Research Runtime Integration

Future usage:

```text
Research Session

↓

Memory Search

↓

Previous Reports

↓

Evidence

↓

Planner Context
```

---

# 20. Agent Runtime Integration

Future usage:

```text
Agent

↓

Memory Context

↓

Execution

↓

Memory Updates
```

---

# 21. Workspace Integration

Future usage:

```text
Workspace

↓

Projects

↓

Reports

↓

Memories

↓

Notes
```

---

# 22. Observability

Metrics:

- remember_latency
- search_latency
- memory_hits
- memory_misses
- memory_count
- embedding_latency
- memory_storage_size

Artifacts:

```text
memory_metrics.json
memory_search.json
memory_context.json
```

---

# 23. Evaluation

Metrics:

- Recall@K
- Precision@K
- Latency
- Storage Cost
- Memory Utility Score

---

# 24. Provider Pattern

---

# Embedding Providers

Reuse existing embedding platform.

Examples:

- Voyage
- OpenAI
- SentenceTransformer

---

# Vector Providers

Reuse vector platform.

Examples:

- Qdrant
- PgVector
- Pinecone

---

# 25. Future LangGraph Integration

LangGraph usage remains internal.

Potential future providers:

- LangGraph Store
- LangGraph Memory

Never expose:

```python
BaseStore
CheckpointSaver
```

outside provider boundaries.

---

# 26. Future Enhancements

Phase 2:

- episodic memory
- memory decay
- memory consolidation
- memory summarization
- memory compression
- reflection memories

Phase 3:

- agent shared memory
- workspace memory
- organization memory

---

# 27. Deliverables

### Models

✅ MemoryRecord

✅ MemoryContext

✅ MemorySearchRequest

---

### Services

✅ MemoryService

✅ SessionMemoryService

✅ UserMemoryService

✅ SemanticMemoryService

✅ ResearchMemoryService

---

### APIs

✅ CRUD APIs

✅ Search APIs

---

### Storage

✅ Valkey

✅ PostgreSQL

✅ Qdrant

---

### Artifacts

✅ Memory artifacts

---

### Observability

✅ Metrics

✅ Reports

---

# Exit Criteria

Memory Platform is complete when:

✅ chat remembers context

✅ preferences persist

✅ semantic search works

✅ research sessions can reuse findings

✅ future agents can consume memory

✅ observability exists

✅ benchmarks exist

Suggested immediate implementation order
1. Canonical Models
2. Storage Layer
3. Session Memory
4. User Memory
5. Semantic Memory
6. Memory APIs
7. Observability
8. Evaluation
9. Research Memory
10. Automatic Memory Extraction

I would intentionally postpone:

memory reflection
memory decay
memory consolidation
agent shared memory

until after Research Runtime exists. Otherwise you'll risk building sophisticated memory mechanisms without real workloads to validate them against.
