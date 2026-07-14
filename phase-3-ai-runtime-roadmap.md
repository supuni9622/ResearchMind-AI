# ResearchMind AI — Roadmap
## Retrieval, Context, Generation & Research Runtime

**Status:** Frozen (v2.0)

**Last Updated:** 2026-07-14

---

# ResearchMind Maturity Vision

```text
NotebookLM++
      ↓
Perplexity v1
      ↓
Open Deep Research
      ↓
Manus / Glean
```

Current State:

```text
NotebookLM++
    +
Perplexity Foundation
```

Hybrid Retrieval, Reranking, Parent Expansion, Compression, Guardrails, and strategy-based Prompt Formatting are all implemented — beyond a plain NotebookLM clone and closing in on Perplexity v1.

Current Focus:

```text
Phase 3.7
Context Building Platform (~90% complete — closing out)
    ↓
Phase 3.8
Generation Platform (highest priority — next)
```

---

# Purpose

The Knowledge Ingestion Platform is now complete.

```text
Upload
↓
Processing
↓
Chunking
↓
Embeddings
↓
Indexing
↓
Vector Store
```

ResearchMind now transitions into an AI Research Platform.

The next stages focus on consuming, enriching, reasoning over, and generating knowledge.

---

# Engineering Principles

- Build complete vertical slices.
- Every platform owns one business capability.
- Canonical domain models only.
- Provider independence.
- Production-first engineering.
- Evaluation-driven development.
- Documentation-first.
- Freeze architecture after validation.
- Frameworks remain implementation details.

# Overall AI Pipeline

```text
                    Upload Platform
                          │
                          ▼
                 Processing Platform
                          │
                          ▼
                 Chunking Platform
                          │
                          ▼
                Embedding Platform
                          │
                          ▼
               Vector Store Platform
                          │
                          ▼
                Retrieval Platform
                          │
                          ▼
               Reranking Platform
                          │
                          ▼
             Context Building Platform
                          │
                          ▼
                Generation Platform
                          │
                          ▼
                Evaluation Platform
                          │
                          ▼
                Research Runtime
                          │
                          ▼
                 Long-Term Platform
```

# Phase 3.4 — Retrieval Strategies

**Status:** 🟡 In Progress

---

## Parallel Retrieval

### Status: ✅ Complete

Implemented:

```python
asyncio.gather(
    dense_search(),
    sparse_search(),
)
```

Current workflow:

```text
Dense Retrieval
        │
Sparse Retrieval
        │
        ▼
Parallel Execution
        │
        ▼
Fusion
```

Future:

```python
asyncio.gather(
    dense,
    sparse,
    metadata,
)
```

---

## Parent / Child Retrieval

### Status: 🔄 Reclassified

Originally planned under Retrieval.

After architecture validation, Parent/Child retrieval has been moved into the Context Platform.

Reason:

ResearchMind persists canonical chunk artifacts.

Retrieval should find knowledge.

Context Building should enrich knowledge.

Workflow:

```text
Retriever
      ↓
Retrieved Child Chunks
      ↓
Parent Expansion
      ↓
Prompt Context
```

Implemented Foundations:

- ChunkArtifactReader
- ParentExpansionService
- AdjacentMergeService

---

## Query Decomposition

### Status: ❌ Not Started

Moved to:

### Research Runtime Platform

Workflow:

```text
Question
      ↓
Planner
      ↓
Sub Questions
      ↓
Parallel Retrieval
      ↓
Merge
```

Likely Framework:

- LangGraph

---

## Deliverables

### Complete

- ✅ Parallel Retrieval

### Context Platform

- 🔄 Parent Expansion

### Runtime Platform

- ❌ Query Decomposition

# Phase 3.7 — Context Building Platform

**Status:** 🟡 ~90% Complete

---

## Goal

Prepare retrieved knowledge for LLM consumption.

---

## Architectural Decision

Retrieval finds knowledge.

Context Building prepares knowledge.

---

## Responsibilities

### Implemented

- ✅ Deduplication
- ✅ Parent Expansion
- ✅ Adjacent Chunk Merge
- ✅ Compression Platform Foundation
- ✅ Token Budget Compression (V1)
- ✅ Embedding Redundancy Compression (V2)
- ✅ Context Guardrails (V1) — provider architecture, `RuleBasedGuardrailProvider`, risk scoring, statistics
- ✅ Citation Platform — citation IDs, pages, headings, chunk IDs
- ✅ Prompt Formatter — strategy-based (`DEFAULT`, `NOTEBOOKLM`, `PERPLEXITY`, `RESEARCH`, `AGENT`)

### Future

- LangChain contextual compression (V3)
- LLM compression (V4)
- Inline citations, source highlighting, citation evaluation
- LlamaGuard, NeMo Guardrails, Lakera (Guardrails V2)

---

## Workflow

```text
Retrieved Chunks
        ↓
Deduplicate
        ↓
Parent Expansion
        ↓
Adjacent Merge
        ↓
Ordering
        ↓
Compression (Token Budget + Embedding)
        ↓
Guardrails
        ↓
Citation Building
        ↓
Prompt Formatting
        ↓
Prompt Context
```

---

## Compression Roadmap

### V1

```text
Top 20
↓
Sort by score
↓
Fit token budget
↓
Top 5-10
```

Status:

✅ Complete

---

### V2

```text
Chunk similarity > 0.95
↓
Drop duplicate chunks
```

Status:

✅ Complete

---

### V3

LangChain

```text
ContextualCompressionRetriever
```

---

### V4

LLM Compression

```text
Chunk
↓
Relevant Summary
↓
Compressed Chunk
```

---

## Deliverables

### Complete

- ✅ Context Models
- ✅ ChunkArtifactReader
- ✅ ParentExpansionService
- ✅ AdjacentMergeService
- ✅ Compression Platform (Token Budget + Embedding, V1/V2)
- ✅ Context Guardrails (V1)
- ✅ Citation Platform
- ✅ Prompt Formatter

### Remaining

- ❌ LangChain Compression Provider (V3)
- ❌ LLM Compression Provider (V4)

# Phase 3.8 — Generation Platform

**Status:** ❌ Not Started — **highest-priority next milestone**

---

## Goal

Generate answers from prepared context.

---

## Responsibilities

- Prompt templates
- Prompt registry
- LLM provider abstraction
- Streaming
- Structured output
- Research chains

---

## Supported Providers

- Groq
- OpenAI
- Claude
- Gemini
- Ollama

---

## Architecture

```text
generation/

    models.py
    interfaces.py
    service.py
    registry.py
    create.py

    providers/

        groq.py
        openai.py
        claude.py
        gemini.py
        ollama.py
```

---

## Workflow

```text
Prompt Context
        ↓
Generation Service
        ↓
LLM Provider
        ↓
Generated Answer
```

---

## Future LangChain Usage

Potential:

- LCEL
- Prompt Templates
- Output Parsers
- Streaming

Frameworks remain implementation details.

---

## Deliverables

- Generation service
- Provider abstraction
- Prompt platform
- Streaming support
- Structured output

# Final MVP Pipeline

```text
                    User Query
                         │
          ┌──────────────┴──────────────┐
          │                             │
     Sparse Search               Dense Search
          │                             │
       Top 50                        Top 50
          └──────────────┬──────────────┘
                         │
                  Parallel Execution
                         │
                  Reciprocal Rank Fusion
                         │
                     Top 20 Results
                         │
                     Reranker
                         │
                      Top 5 Results
                         │
                  Context Builder
                         │
                  Parent Expansion
                         │
                  Adjacent Merge
                         │
               Token Budget Compression
                         │
                  Citation Builder
                         │
                  Prompt Formatter
                         │
                 Generation Platform
                         │
                    Final Answer
                    + Citations
```

Milestone	Platform	Deliverables	Status
3.1	Retrieval Foundation	Query processing, dense retrieval	✅ Complete
3.2	Sparse Retrieval	SPLADE, sparse search	✅ Complete
3.3	Hybrid Retrieval	Dense + Sparse + RRF	✅ Complete
3.4	Retrieval Strategies	Parallel Retrieval, Runtime Query Decomposition	✅ Parallel Retrieval complete (Query Decomposition moved to 3.11)
3.5	Result Processing	Metadata filtering, Top-K	✅ Complete
3.6	Reranking Platform	Voyage, CrossEncoder	✅ Complete
3.7	Context Building Platform	Parent Expansion, Merge, Compression, Guardrails, Citations, Prompt Formatter	🟡 ~90% Complete (LangChain + LLM compression remain)
3.8	Generation Platform	Multi-provider LLM runtime	❌ Not Started — highest priority
3.9	Research APIs	/research, streaming, citations	❌ Not Started
3.10	Evaluation Platform	Groundedness, Hallucinations, Citation Accuracy	🟡 Retrieval evaluation complete
3.11	Research Runtime	Planner, Query Decomposition, Agents	❌ Not Started
3.12	Long-Term Platform	Research Sessions, Memory, MCP	❌ Not Started

# Architecture Principles

- Retrieval is responsible only for finding knowledge.
- Reranking improves ordering.
- Context Building prepares knowledge for LLM consumption.
- Generation owns all LLM interactions.
- Evaluation measures every improvement.
- Runtime owns planning and reasoning.
- Artifacts remain the source of truth.
- Vector databases are acceleration mechanisms only.
- Frameworks remain implementation details.
- Provider SDKs never leak outside provider implementations.
