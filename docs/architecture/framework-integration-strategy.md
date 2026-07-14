# Framework Integration Strategy

**Status:** Active
**Last Updated:** 2026-07-14
**Related ADR:** ADR-024 — Framework Integration Strategy

---

# Purpose

This document defines how ResearchMind integrates with:

- LangChain
- LangGraph
- LangSmith

The goal is to maximize leverage from mature ecosystem tools while preserving:

- platform ownership
- architectural boundaries
- domain independence
- future flexibility

---

# Guiding Philosophy

ResearchMind follows:

```text
Platform-Owned Architecture
+
Framework-Powered Runtime
```

ResearchMind is the source of truth.

Frameworks are implementation tools.

---

# Core Principle

```text
ResearchMind Architecture
            ↓
Interfaces
            ↓
Providers
            ↓
Framework Runtime
```

NOT:

```text
ResearchMind
      ↓
Framework Architecture
```

---

# High-Level Architecture

```text
ResearchMind Platform
─────────────────────────────

Artifacts
Knowledge Services
Metadata
Sessions
Memory Models
Research Runtime
APIs
Evaluation Contracts

─────────────────────────────
        ↓
Provider Interfaces
─────────────────────────────
        ↓
LangChain
LangGraph
LangSmith
```

---

# Ownership Boundaries

---

# ResearchMind Owns

The following are considered long-term platform differentiators.

---

## Artifacts

Examples:

```text
ProcessingArtifact
ChunkArtifact
EmbeddingArtifact
IndexArtifact
ResearchArtifact
```

Responsibilities:

- lineage
- persistence
- versioning
- auditing

---

## Document Lifecycle

Examples:

```text
UPLOADED
PROCESSING
CHUNKED
EMBEDDED
INDEXED
FAILED
ARCHIVED
```

Responsibilities:

- orchestration
- retries
- state transitions

---

## Metadata Model

Examples:

```text
owner_id
workspace_id
research_session_id
citations
permissions
security_labels
```

Responsibilities:

- filtering
- access control
- knowledge organization

---

## Knowledge Services

Examples:

```text
Knowledge APIs
Research APIs
Workspace APIs
```

Responsibilities:

- orchestration
- service contracts
- business rules

---

## Platform APIs

Examples:

```text
Upload APIs
Artifact APIs
Research APIs
Session APIs
```

Responsibilities:

- public interfaces
- backward compatibility
- API versioning

---

## Evaluation Contracts

Examples:

```text
Retrieval Metrics
Groundedness
Faithfulness
Citation Accuracy
Research Quality
```

Responsibilities:

- benchmarks
- evaluation datasets
- quality gates

---

# LangChain Integration

LangChain is primarily used for:

```text
Runtime Primitives
Retrieval Utilities
Prompt Components
```

---

# Approved Usage Areas

---

## Parent Retrieval

Purpose:

```text
Retrieve child chunks
Expand parent context
```

ResearchMind:

```text
ParentRetrievalService
```

LangChain:

```text
ParentDocumentRetriever
```

Architecture:

```text
ResearchMind Interface
            ↓
LangChain Provider
            ↓
ParentDocumentRetriever
```

---

## Context Compression

Purpose:

```text
Reduce token usage
Improve context quality
```

ResearchMind:

```text
Context Platform
```

LangChain:

```text
ContextualCompressionRetriever
```

Architecture:

```text
ContextBuilder
        ↓
CompressionProvider
        ↓
LangChain Compression
```

---

## Prompt Runtime

ResearchMind:

```text
Prompt Contracts
Research Chains
```

LangChain:

```text
Prompt Templates
LCEL
Output Parsers
```

---

## Utilities

Examples:

```text
Text Splitters
Document Transformers
Runnable Pipelines
```

---

# Avoid

ResearchMind should avoid:

```text
LangChain-first architecture
LangChain domain models
LangChain APIs becoming source of truth
```

Bad:

```text
ResearchMind
      ↓
LangChain Everywhere
```

---

# LangGraph Integration

LangGraph is primarily used for:

```text
Workflow Runtime
State Management
Execution Engine
```

---

# Approved Usage Areas

---

## Research Runtime

ResearchMind owns:

```text
Planner Contracts
Workflow Definitions
Execution Artifacts
```

LangGraph provides:

```text
StateGraph
Parallel Execution
Branching
Interrupts
```

Architecture:

```text
Research Workflow
        ↓
Runtime Provider
        ↓
LangGraph
```

---

## Research Sessions

ResearchMind owns:

```text
Session Domain
Reports
Artifacts
Ownership
```

LangGraph provides:

```text
Threads
Checkpointing
State Persistence
```

Architecture:

```text
ResearchSession
        ↓
LangGraph Thread
        ↓
Persistence
```

---

## Memory Runtime

ResearchMind owns:

```text
Research Memory
Long-Term Memory
Knowledge Memory
```

LangGraph provides:

```text
Stores
Checkpointers
Session State
```

Architecture:

```text
ResearchMemory
        ↓
Memory Provider
        ↓
LangGraph Store
```

---

## Human-in-the-Loop

Potential usage:

```text
Research Approval
Feedback Collection
Agent Interrupts
```

---

# LangSmith Integration

LangSmith is primarily used for:

```text
Observability
Experiments
Tracing
Evaluation Infrastructure
```

---

# Approved Usage Areas

---

## Runtime Tracing

Examples:

```text
Retrieval traces
Generation traces
Agent traces
Graph execution traces
```

---

## Experiments

Examples:

```text
Prompt comparisons
Retriever comparisons
Reranker comparisons
Agent evaluation
```

---

## Datasets

Examples:

```text
RAG evaluation datasets
Research evaluation datasets
```

---

## Debugging

Examples:

```text
Prompt debugging
Workflow debugging
Failure analysis
```

---

# Long-Term Evaluation

ResearchMind may eventually extend LangSmith with:

```text
Research dashboards
Citation analytics
Quality analytics
Cost analytics
```

---

# Ownership Matrix

| Capability | ResearchMind | Framework |
|------------|---------------|------------|
| Artifacts | ✅ | ❌ |
| Document Lifecycle | ✅ | ❌ |
| Metadata Model | ✅ | ❌ |
| Platform APIs | ✅ | ❌ |
| Knowledge Services | ✅ | ❌ |
| Evaluation Contracts | ✅ | ❌ |
| Parent Retrieval Runtime | Interface | LangChain |
| Compression Runtime | Interface | LangChain |
| Prompt Runtime | Interface | LangChain |
| Research Runtime Engine | Interface | LangGraph |
| Memory Runtime | Interface | LangGraph |
| Session Runtime | Interface | LangGraph |
| Observability | Extensions | LangSmith |
| Experiment Infrastructure | Extensions | LangSmith |

---

# Integration Pattern

All framework integrations should follow:

```text
ResearchMind
      ↓
Interface
      ↓
Provider
      ↓
Framework
```

---

# Example

---

## Parent Retrieval

```text
ParentRetrievalService
            ↓
ParentRetrievalProvider
            ↓
LangChainParentRetriever
```

---

## Context Compression

```text
ContextBuilder
      ↓
CompressionProvider
      ↓
ContextualCompressionRetriever
```

---

## Research Runtime

```text
ResearchRuntime
        ↓
RuntimeProvider
        ↓
LangGraph StateGraph
```

---

## Memory

```text
ResearchMemoryService
            ↓
MemoryProvider
            ↓
LangGraph Store
```

---

## Observability

```text
ResearchMind
      ↓
Tracing Provider
      ↓
LangSmith
```

---

# Anti-Patterns

---

# Framework-Driven Domain Models

Avoid:

```python
class ResearchSession(
    LangGraphState
):
    ...
```

Domain models should remain framework-independent.

---

# Framework APIs as Public APIs

Avoid:

```text
Expose LangChain APIs externally
Expose LangGraph state externally
```

---

# Framework Leakage

Avoid:

```text
LangChain Documents everywhere
LangGraph types everywhere
```

Framework types should remain inside providers.

---

# Evolution Strategy

ResearchMind may replace framework implementations in the future.

Examples:

```text
LangChain Parent Retrieval
            ↓
Custom Parent Retrieval
```

No platform changes should be required.

---

# Technology Roadmap

---

# Phase 3

Use:

```text
LangChain ParentDocumentRetriever
```

---

# Phase 4

Use:

```text
LangChain ContextualCompressionRetriever
```

---

# Phase 5

Use:

```text
LCEL
Output Parsers
Prompt Templates
```

---

# Phase 6+

Use:

```text
LangGraph
StateGraph
Stores
Checkpointing
Threads
```

---

# Long-Term Vision

```text
ResearchMind Platform
            ↓
Research Runtime
            ↓
Framework Runtime Layer
```

ResearchMind remains:

- framework-independent
- portable
- extensible
- domain-driven

while benefiting from mature ecosystem tooling.

---

# Summary

ResearchMind follows:

```text
Own the architecture.
Leverage mature runtimes.
Avoid unnecessary reinvention.
Prevent framework lock-in.
```

Frameworks are:

```text
Implementation Tools
```

ResearchMind is:

```text
The Product
The Platform
The Source of Truth
```
