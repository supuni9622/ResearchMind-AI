# ADR-023: Framework Integration Strategy

**Status:** Accepted
**Date:** 2026-07-14
**Authors:** ResearchMind Team

---

# Context

ResearchMind aims to become a comprehensive research platform capable of:

- Document understanding
- Knowledge retrieval
- Research workflows
- Multi-agent execution
- Long-term memory
- Evaluation and observability

Several mature frameworks already exist in the ecosystem:

- LangChain
- LangGraph
- LangSmith

A key architectural question is determining:

```text
What should be built by ResearchMind?

What should be delegated to frameworks?
```

Building every capability from scratch increases:

- development time
- maintenance burden
- complexity
- implementation risk

Conversely, allowing frameworks to dictate system architecture would:

- reduce flexibility
- increase framework coupling
- limit future evolution
- weaken platform differentiation

---

# Problem

Two undesirable extremes exist.

---

## Option A

### Build Everything Internally

```text
ResearchMind
↓
Everything Custom
```

Problems:

- reinvents mature solutions
- high maintenance cost
- slower delivery
- duplicates industry work

---

## Option B

### Framework-Driven Architecture

```text
ResearchMind
↓
LangChain Everywhere
```

Problems:

- framework lock-in
- architecture drift
- weak domain boundaries
- difficult future migration

---

# Decision

ResearchMind adopts a:

```text
Platform-Owned Architecture
+
Framework-Powered Runtime
```

strategy.

---

# Core Principle

```text
ResearchMind owns:

- Platform Architecture
- Domain Models
- Artifacts
- APIs
- Metadata
- Knowledge Services
- Evaluation Contracts

Frameworks provide:

- Runtime Primitives
- Workflow Engines
- Utility Components
- Observability Infrastructure
```

Frameworks are implementation details and must not become the source of truth.

---

# Architectural Principle

```text
ResearchMind Architecture
            ↓
Interfaces
            ↓
Providers
            ↓
LangChain / LangGraph / LangSmith
```

NOT:

```text
ResearchMind
      ↓
LangChain Architecture
```

---

# Ownership Boundaries

---

# ResearchMind-Owned Components

The following are considered core platform concerns.

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

Reason:

Artifacts represent platform lineage and are a long-term differentiator.

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

Reason:

Lifecycle management is product-specific.

---

## Metadata Model

Examples:

```text
owner_id
workspace_id
research_session_id
citations
permissions
```

Reason:

Metadata requirements evolve with platform needs.

---

## Knowledge Services

Examples:

```text
Knowledge API
Research API
Workspace APIs
```

Reason:

These define platform capabilities.

---

## Platform APIs

Examples:

```text
Upload APIs
Research APIs
Session APIs
Artifact APIs
```

Reason:

Frameworks should not dictate public interfaces.

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

Reason:

Evaluation requirements are platform-specific.

---

# Framework-Owned Runtime Capabilities

The following areas should leverage mature ecosystem components.

---

# LangChain

ResearchMind will leverage LangChain for runtime primitives.

---

## Retrieval Components

Examples:

```text
ParentDocumentRetriever
ContextualCompressionRetriever
MultiQueryRetriever
```

---

## Prompt Components

Examples:

```text
Prompt Templates
Output Parsers
LCEL
Document Transformers
```

---

## Utilities

Examples:

```text
Text Splitters
Runnable Pipelines
Document Loaders
```

---

# LangGraph

ResearchMind will leverage LangGraph for workflow execution.

---

## Runtime Execution

Examples:

```text
StateGraph
Parallel Execution
Branching
Interrupts
Human-in-the-loop
```

---

## Persistence

Examples:

```text
Threads
Checkpoints
Stores
```

---

## Memory Runtime

Examples:

```text
Short-Term Memory
State Persistence
Session Runtime State
```

---

# LangSmith

ResearchMind will leverage LangSmith for observability and experimentation.

Examples:

```text
Tracing
Experiments
Datasets
Prompt Evaluation
Runtime Debugging
Graph Visualization
```

---

# Hybrid Ownership Areas

Certain capabilities require collaboration between ResearchMind and frameworks.

---

# Research Sessions

ResearchMind owns:

```text
Session Domain
Ownership
Reports
Artifacts
Feedback
```

LangGraph provides:

```text
Threads
Checkpointing
Runtime State
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

# Memory

ResearchMind owns:

```text
Research Memory
Long-Term Knowledge
User Preferences
Research Context
```

LangGraph provides:

```text
Stores
Checkpointing
State Persistence
```

---

# Research Runtime

ResearchMind owns:

```text
Planner Contracts
Workflow Definitions
Execution Artifacts
Research Strategies
```

LangGraph provides:

```text
Execution Engine
Parallelism
State Management
```

---

# Evaluation Framework

ResearchMind owns:

```text
Research Metrics
Groundedness
Citation Quality
Evaluation Contracts
```

LangSmith provides:

```text
Tracing
Experiments
Datasets
Debugging
```

---

# Integration Pattern

Framework integrations must follow:

```text
ResearchMind Interface
            ↓
Provider
            ↓
Framework
```

---

# Good Example

---

## Parent Retrieval

```text
ParentRetrievalService
            ↓
LangChainParentProvider
            ↓
ParentDocumentRetriever
```

---

## Research Runtime

```text
ResearchRuntime
        ↓
LangGraphRuntimeProvider
        ↓
StateGraph
```

---

## Memory

```text
ResearchMemoryService
            ↓
LangGraphStoreProvider
```

---

# Bad Example

```text
ResearchMind
      ↓
LangChain Everywhere
```

Problems:

- framework lock-in
- architecture leakage
- difficult replacement
- reduced platform ownership

---

# Consequences

---

# Positive

---

## Faster Development

ResearchMind can leverage mature ecosystem capabilities.

---

## Lower Maintenance Cost

Avoids rebuilding:

```text
retrievers
workflow engines
checkpoint systems
observability platforms
```

---

## Better Reliability

Frameworks are:

- widely adopted
- production tested
- actively maintained

---

## Platform Focus

Engineering effort remains focused on:

```text
research workflows
knowledge systems
evaluation
domain innovation
```

---

# Negative

---

## Framework Dependency

ResearchMind becomes dependent on ecosystem maturity.

Mitigation:

```text
Frameworks remain behind interfaces.
```

---

## API Changes

Framework upgrades may introduce breaking changes.

Mitigation:

```text
Provider abstraction layer.
```

---

## Migration Cost

Framework replacement still requires effort.

Mitigation:

```text
Domain contracts remain framework-independent.
```

---

# Long-Term Principle

ResearchMind shall follow:

```text
Platform Ownership
+
Framework Leverage
```

Guiding philosophy:

```text
Do not rebuild mature capabilities.

Do not surrender architectural ownership.
```

---

# Decision Summary

ResearchMind adopts the following strategy:

---

## ResearchMind Owns

```text
Platform Architecture
Domain Models
Artifacts
Metadata
Knowledge Services
Platform APIs
Evaluation Contracts
```

---

## LangChain Provides

```text
Retrievers
Compression
Prompt Runtime
Utilities
```

---

## LangGraph Provides

```text
Workflow Runtime
State Management
Memory Runtime
Checkpointing
Threads
```

---

## LangSmith Provides

```text
Observability
Tracing
Experiments
Evaluation Infrastructure
```

---

ResearchMind architecture remains the source of truth.

Frameworks provide implementation capabilities and runtime infrastructure.
