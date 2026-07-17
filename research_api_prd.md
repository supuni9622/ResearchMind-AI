# ResearchMind — Research API Platform PRD

**Document Version:** 1.1
**Platform:** Research APIs
**Milestone:** Phase 4
**Status:** Ready For Implementation
**Owner:** ResearchMind Core Platform

---

# 1. Overview

## Purpose

This milestone introduces the first usable ResearchMind product.

For the first time users can:

- Upload documents
- Ask questions against their knowledge base
- Receive grounded answers
- Receive citations and sources
- Stream long-form responses
- Replay previous research sessions

This milestone intentionally remains simple.

This is **not**:

- Research Runtime
- Planner Runtime
- Deep Research
- Multi-Agent System
- LangGraph Runtime

Those are future milestones.

---

# 2. Product Vision

This phase delivers:

```text
NotebookLM
        +
Perplexity
        ↓
ResearchMind v1
```

User Flow:

```text
Upload Documents
        ↓
Ask Question
        ↓
Retrieve Evidence
        ↓
Generate Answer
        ↓
Show Citations
        ↓
Persist Session
```

This becomes the first end-to-end product experience.

---

# 3. Goals

---

## Primary Goals

### 1. Research Question Answering

```text
Question
        ↓
Hybrid Retrieval
        ↓
Context Building
        ↓
Generation Runtime
        ↓
Grounded Answer
```

---

### 2. Source Citations

Provide:

- document references
- chunk references
- page references (future)
- source metadata

---

### 3. Streaming Research Responses

Support long responses through SSE.

---

### 4. Persist Research Sessions

Allow users to revisit previous research.

---

### 5. Reuse Existing Platforms

Research APIs must reuse:

- Retrieval Platform
- Context Platform
- Generation Runtime Platform
- Artifact Platform
- Streaming Platform

No duplicate implementations.

---

# 4. Non Goals

This milestone MUST NOT implement:

- Query Decomposition
- Research Planning
- Multi-step Research Loops
- Reflection
- Self-Critique
- Agent Workflows
- Deep Research
- Memory Systems
- LangGraph State Machines
- Supervisor Graphs
- Tool Calling
- Research Agents

---

# 5. Architecture

```text
POST /research
        ↓
ResearchService
        ↓
Retrieval Platform
        ↓
Context Platform
        ↓
Generation Runtime
        ↓
Research Artifacts
        ↓
Response
```

---

# 6. API Endpoints

---

# POST /research

Primary research endpoint.

Generates a grounded answer from uploaded documents.

---

# POST /research/stream

Streaming version of `/research`.

Uses existing Streaming Platform.

---

# POST /research/citations

Returns citations only.

Used by frontend citation panels.

---

# GET /research/{id}

Returns a previous research session.

---

# 7. API Contracts

---

## POST /research

### Request

```json
{
  "query": "How does RAG work?",
  "top_k": 10,
  "filters": {}
}
```

---

### Optional Advanced Overrides

These fields are NOT required.

They exist for:

- benchmarking
- evaluation
- admin tools
- playground APIs
- debugging

```json
{
  "query": "How does RAG work?",
  "provider": "claude",
  "routing_strategy": "research"
}
```

ResearchMind owns provider and routing decisions by default.

---

### Response

```json
{
  "research_id": "...",

  "query": "How does RAG work?",

  "answer": "...",

  "citations": [],

  "sources": [],

  "duration_ms": 1234
}
```

---

## POST /research/stream

### Request

```json
{
  "query": "Explain RAG architecture."
}
```

---

### Stream Events

```text
START

RETRIEVAL_STARTED
RETRIEVAL_COMPLETED

GENERATION_STARTED

TOKEN
TOKEN
TOKEN

COMPLETE
```

---

## POST /research/citations

### Request

```json
{
  "query": "How does RAG work?"
}
```

---

### Response

```json
{
  "citations": [...]
}
```

---

## GET /research/{id}

### Response

```json
{
  "research_id": "...",

  "query": "...",

  "answer": "...",

  "citations": [...],

  "sources": [...],

  "created_at": "..."
}
```

---

# 8. Request Models

---

## ResearchRequest

```python
class ResearchRequest(BaseModel):

    query: str

    top_k: int = 10

    filters: dict[str, Any] = Field(
        default_factory=dict,
    )

    provider: GenerationProvider | None = None

    routing_strategy: RoutingStrategy | None = None
```

---

## Important Design Rule

Provider selection and routing are backend concerns.

These fields are optional overrides only.

Normal clients should simply send:

```json
{
  "query": "How does RAG work?"
}
```

ResearchMind determines:

- provider
- routing strategy
- model selection
- cost optimization
- fallback strategies

---

# 9. Response Models

---

## ResearchResponse

```python
class ResearchResponse(BaseModel):

    research_id: UUID

    query: str

    answer: str

    citations: list[Citation]

    sources: list[ResearchSource]

    duration_ms: float
```

---

## ResearchSource

```python
class ResearchSource(BaseModel):

    document_id: UUID

    filename: str

    chunk_id: UUID

    score: float

    page: int | None = None
```

---

# 10. Research Service

Introduce:

```python
ResearchService
```

Responsibilities:

```text
retrieval orchestration
context orchestration
generation orchestration
citation construction
artifact persistence
session persistence
```

ResearchService becomes the orchestration layer.

---

# 11. Retrieval Strategy

Default flow:

```text
Hybrid Search
        ↓
Reranking
```

Reuse existing Retrieval Platform.

No new retrieval implementation.

---

## Ownership Filtering

Every retrieval request must automatically inject:

```python
owner_id=current_user.id
```

Never trust ownership filters from request payload.

---

# 12. Context Building

Reuse existing Context Platform.

---

## Pipeline

```text
Retrieved Chunks
        ↓
Deduplication
        ↓
Parent Expansion
        ↓
Adjacent Merge
        ↓
Compression
        ↓
Citation Construction
        ↓
Prompt Formatting
```

No duplicate context logic.

---

# 13. Generation Strategy

Research APIs must never call providers directly.

Always execute through:

```python
GenerationRuntime.execute_generation()
```

---

## Runtime Type

```python
runtime=RuntimeType.RESEARCH
```

---

# 14. Research Session

Introduce:

```python
ResearchSession
```

---

## Fields

```python
research_id
owner_id
query
answer
citations
created_at
runtime_metadata
```

---

# 15. Research Artifacts

Introduce:

```text
artifacts/

    research/

        {research_id}/

            request.json
            retrieval.json
            context.json
            generation.json
            citations.json
            answer.md
            metadata.json
```

Artifacts remain canonical.

Database acts as index.

---

# 16. Folder Structure

```text
api/v1/

    research.py


schemas/

    research.py


services/

    research.py


repositories/

    research.py


ai/research/

    models.py
    service.py
    artifacts/
```

---

# 17. API Flow

---

## POST /research

```text
Question
        ↓
Research Service
        ↓
Hybrid Retrieval
        ↓
Context Building
        ↓
Generation Runtime
        ↓
Artifacts
        ↓
Response
```

---

## POST /research/stream

```text
Question
        ↓
Research Service
        ↓
Hybrid Retrieval
        ↓
Context Building
        ↓
Streaming Service
        ↓
SSE
```

---

## GET /research/{id}

```text
Research ID
        ↓
Repository
        ↓
Artifacts
        ↓
Replay Response
```

---

# 18. Authentication

All endpoints require:

```python
current_user: User
```

Research sessions are user scoped.

Users may never access another user's sessions.

---

# 19. Future Evolution

This phase intentionally remains linear.

Future roadmap:

---

## Research Runtime

```text
Question
        ↓
Planning
        ↓
Sub Questions
        ↓
Parallel Retrieval
        ↓
Merge
        ↓
Answer
```

---

## Deep Research Runtime

```text
Question
        ↓
Plan
        ↓
Research
        ↓
Review
        ↓
Research Again
        ↓
Finalize
```

---

## Agent Platform

```text
Planner Agent
Research Agent
Reviewer Agent
```

---

## LangGraph

LangGraph will own:

```text
state machines
loops
branches
parallelism
checkpoints
interrupts
multi-agent execution
```

Research APIs MUST NOT implement these capabilities.

---

# 20. Acceptance Criteria

Users can:

✅ upload documents

✅ ask questions

✅ receive grounded answers

✅ receive citations

✅ stream answers

✅ revisit previous sessions

✅ access only their own research sessions

---

# 21. Definition of Done

ResearchMind becomes usable:

```text
Upload Documents
        ↓
Ask Questions
        ↓
Receive Grounded Answers
        ↓
Receive Citations
        ↓
Persist Research Sessions
```

This milestone represents the first complete product experience.

Future milestones add:

- planning
- decomposition
- deep research
- agents
- LangGraph workflows
