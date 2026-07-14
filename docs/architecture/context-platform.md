# Context Platform Architecture

**Status:** In Progress

**Last Updated:** 2026-07-14

---

# Purpose

The Context Platform is responsible for transforming retrieved knowledge into high-quality, secure, and LLM-consumable context.

Retrieval is responsible for finding information.

Context Platform is responsible for preparing information.

Generation is responsible for reasoning and producing responses.

---

# High Level Architecture

```text
Retrieved Chunks
        ↓
Deduplicate
        ↓
Parent Expansion
        ↓
Adjacent Merge
        ↓
Compression
        ↓
Guardrails
        ↓
Citation Builder
        ↓
Prompt Formatter
        ↓
Prompt Context
```

---

# Responsibilities

Context Platform owns:

- Context enrichment
- Parent context expansion
- Context compression
- Security validations
- Citation generation
- Prompt context formatting

Context Platform does NOT own:

- Retrieval
- Prompt instructions
- LLM execution
- Response generation

---

# Architectural Principles

---

## Principle 1

```text
Retrieved Context
            ≠
Instructions
```

Retrieved context is reference material only.

---

## Principle 2

```text
Retrieval
        ↓
Find Knowledge

Context
        ↓
Prepare Knowledge
```

---

## Principle 3

Artifacts remain source of truth.

Vector stores are acceleration mechanisms.

---

# Current Pipeline

```text
Retrieval
      ↓
RetrievedChunk
      ↓
ContextChunk
      ↓
PromptContext
```

---

# Core Models

---

# RetrievedChunk

Represents retrieval results.

Contains:

- score
- retrieval metadata
- chunk metadata

---

# ContextChunk

Represents enriched chunks.

Contains:

- parent content
- merged chunks
- citations
- risk metadata

---

# PromptContext

Represents final prompt-ready context.

Contains:

- formatted context
- citations
- chunks

---

# Stage 1 — Parent Expansion

Status:

✅ Implemented

---

# Purpose

Expand retrieved child chunks into richer context.

---

# Workflow

```text
Retrieved Chunk
        ↓
Parent Chunk Lookup
        ↓
ContextChunk
```

---

# Components

Implemented:

- ChunkArtifactReader
- ParentExpansionService

---

# Future

---

## V2

Hierarchical expansion.

```text
Document
    ↓
Section
    ↓
Parent
    ↓
Child
```

---

## V3

Adaptive expansion.

Expand only when:

```text
score < threshold
```

---

## V4

LangChain Integration.

Potential:

```python
ParentDocumentRetriever
```

---

# Stage 2 — Adjacent Merge

Status:

✅ Implemented

---

# Purpose

Merge nearby chunks to improve continuity.

---

# Workflow

```text
chunk15
chunk16
chunk17
        ↓
merged context
```

---

# Future

---

## V2

Semantic adjacency.

Merge based on:

- heading
- semantic similarity

---

## V3

Dynamic window sizing.

---

# Stage 3 — Compression Platform

Status:

🟡 In Progress

---

# Goal

Reduce irrelevant or redundant context.

---

# Architecture

```text
CompressionService
            ↓
CompressionRegistry
            ↓
Providers
```

---

# Current Providers

---

## Token Budget Provider

Status:

✅ Implemented

Workflow:

```text
Top 20
↓
Fit token budget
↓
Top 5-10
```

---

## Embedding Compression Provider

Status:

✅ Implemented

Workflow:

```text
Chunk Similarity
        ↓
Remove Redundancy
```

Model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

---

# Future Providers

---

## LangChain Provider

Status:

❌ Not Implemented

Potential:

```python
ContextualCompressionRetriever
```

When:

Phase 5+

---

## LLM Compression Provider

Status:

❌ Not Implemented

Workflow:

```text
Chunk
        ↓
Summarize Relevant Parts
        ↓
Compressed Chunk
```

Requires:

Generation Platform.

---

## Query-Aware Compression

Status:

❌ Future

Workflow:

```text
Question
        ↓
Chunk
        ↓
Relevance Compression
```

---

# Stage 4 — Context Guardrails

Status:

✅ Implemented (Rule Based)

---

# Purpose

Protect against prompt injection.

---

# Architecture

```text
GuardrailService
        ↓
Registry
        ↓
Providers
```

---

# Implemented Provider

---

## RuleBasedGuardrailProvider

Status:

✅

Detects:

- ignore previous instructions
- system prompt extraction
- tool calls
- jailbreak attempts

Produces:

- risk levels
- warnings
- risk reasons

---

# Future Providers

---

## Llama Guard

Status:

❌

When:

Agent Runtime.

---

## NVIDIA NeMo Guardrails

Status:

❌

When:

Enterprise deployments.

---

## Lakera

Status:

❌

When:

Production security hardening.

---

## OpenAI Prompt Shields

Status:

❌

Optional.

---

# Future Improvements

---

## Query-aware risk scoring

```text
Question
        ↓
Chunk
        ↓
Injection risk
```

---

## Tool manipulation detection

Future:

```text
MCP
LangGraph
Agents
```

---

## Runtime security policies

Future:

- planner protection
- reviewer protection
- tool execution policies

---

# Stage 5 — Citation Platform

Status:

✅ Implemented

---

# Purpose

Provide source traceability.

---

# Workflow

```text
Chunks
      ↓
Citations
```

---

# Supports

- document id
- filename
- page numbers
- heading
- chunk ids

---

# Future

---

## Citation Accuracy Evaluation

Phase 6.

---

## Inline Answer Citations

```text
Answer [S1]
```

---

## NotebookLM Style Citations

---

## Source Highlighting

---

## Research Session Traceability

---

# Stage 6 — Prompt Formatter

Status:

❌ Not Implemented

---

# Purpose

Transform context objects into prompt-ready text.

---

# Responsibilities

- source formatting
- citation formatting
- parent context formatting
- chunk ordering

---

# Does NOT own

- prompt instructions
- question
- response schemas

---

# Future Strategies

---

## Default

Simple formatting.

---

## NotebookLM

Rich formatting.

---

## Perplexity

Answer optimized.

---

## Research

Large context formatting.

---

## Agent

Tool optimized formatting.

---

# Example Pipeline

```text
ContextChunk
        ↓
Prompt Formatter
        ↓
Formatted Context
```

---

# Relationship to Prompt Templates

```text
Prompt Formatter
        ↓
Knowledge Representation

Prompt Template
        ↓
LLM Instructions
```

---

# Final Context Pipeline

```text
Retrieved Chunks
        ↓
Deduplicate
        ↓
Parent Expansion
        ↓
Adjacent Merge
        ↓
Embedding Compression
        ↓
Token Budget Compression
        ↓
Context Guardrails
        ↓
Citation Builder
        ↓
Prompt Formatter
        ↓
Prompt Context
```

---

# Future Roadmap

---

# Phase 4

✅ Parent Expansion
✅ Adjacent Merge
✅ Compression Foundation
✅ Embedding Compression
✅ Guardrails
✅ Citation Platform
❌ Prompt Formatter

---

# Phase 5

- Generation Platform
- LangChain Integration
- LLM Compression

---

# Phase 6

- Citation Evaluation
- Groundedness
- Faithfulness
- Hallucination Evaluation

---

# Phase 7

- LangGraph Runtime
- Planner
- Query Decomposition
- Research Agents
- Reviewer
- Summarizer

---

# Phase 8

- MCP
- Research Sessions
- Long-Term Memory
- Feedback Learning
- Enterprise Security
