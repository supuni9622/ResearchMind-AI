# ADR-027 — Runtime Caching Platform

**Status:** Accepted

**Date:** 2026-07-17

---

# Context

ResearchMind is evolving from a pure RAG platform into a full AI Runtime,
Research Runtime, and Agent Platform.

As the platform introduces:

- Chat
- Research Sessions
- Deep Research
- Multi-Agent Systems
- Evaluation Pipelines
- Benchmarking
- MCP Integrations

LLM usage and associated costs will increase significantly.

Without caching:

- identical requests repeatedly invoke providers
- similar questions regenerate identical outputs
- research sessions repeatedly regenerate intermediate results
- agent workflows repeatedly execute deterministic nodes

This creates:

- unnecessary latency
- increased provider costs
- poor user experience
- reduced throughput
- duplicated execution

A dedicated Runtime Caching Platform is required.

---

# Decision

Introduce a standalone Runtime Caching Platform under:

```text
runtime/generation/caching/
```

The platform will provide:

1. Exact Prompt Cache (L1)
2. Semantic Cache (L2)
3. Session Cache (L3)

Caching becomes a first-class runtime capability rather than provider-specific logic.

---

# Goals

The Runtime Caching Platform is responsible for:

- reducing latency
- reducing provider costs
- reducing duplicate execution
- improving benchmark execution speed
- supporting future conversation memory
- supporting future research sessions
- supporting future agent execution

---

# Non Goals

The Runtime Caching Platform is NOT responsible for:

- long-term memory
- knowledge retrieval caching
- vector search caching
- MCP caching
- tool execution caching
- planner state persistence

Those belong to future platforms.

---

# Architecture Position

```text
Prompt Context
        ↓
Validation
        ↓
Guardrails
        ↓
Prompt Templates
        ↓
Routing
        ↓
Caching Platform
        ↓
Provider
        ↓
Structured Output
        ↓
Validation
        ↓
Artifacts
```

---

# Cache Levels

---

# L1 — Exact Prompt Cache

Purpose:

Avoid repeated generation for identical requests.

---

## Cache Key

Generated from:

- provider
- model
- routing strategy
- prompt version
- temperature
- top_p
- prompt hash
- context hash
- schema hash
- validation version
- guardrail version

---

## Storage

Valkey

---

## Use Cases

Enabled for:

- chat
- research
- benchmarks

Disabled for:

- streaming
- planners
- tool execution

---

---

# L2 — Semantic Cache

Purpose:

Reuse responses for semantically similar requests.

---

## Architecture

```text
Prompt
      ↓
Embedding
      ↓
Similarity Search
      ↓
Threshold Check
      ↓
Reuse Response
```

---

## Initial Implementation

Leverage LangChain:

- RedisSemanticCache

No custom semantic search infrastructure will be built.

---

## Similarity Threshold

Default:

```text
0.92
```

Configurable.

---

## Important Constraint

Semantic cache keys must include:

```text
context_hash
```

to avoid cross-document contamination.

---

## Use Cases

Enabled:

- research
- chat

Disabled:

- agents
- tools
- benchmarks

---

---

# L3 — Session Cache

Purpose:

Support future:

- conversation sessions
- research sessions
- agent execution sessions

---

## Session Types

### Conversation Session

Caches generated responses.

### Research Session

Caches intermediate findings.

### Agent Session

Caches deterministic node outputs.

---

# Cache Policy System

A policy layer determines whether caching should be used.

---

## Policies

```python
AUTO
NEVER
EXACT_ONLY
SEMANTIC
SESSION
```

---

# Default Policies

| Runtime | Policy |
|----------|---------|
| Chat | AUTO |
| Research | SEMANTIC |
| Benchmark | EXACT_ONLY |
| Planner | NEVER |
| Tool Agent | NEVER |
| Summarizer | AUTO |

---

# Why Runtime-Level Caching?

Caching is a cross-cutting concern.

Caching inside providers would:

- duplicate implementations
- break provider independence
- make observability difficult
- complicate artifacts

---

# Observability Integration

The platform exposes metrics:

- cache hits
- cache misses
- cache latency
- hit ratio
- tokens saved
- cost saved

---

# Artifact Integration

Generation artifacts will persist:

```json
{
  "cache": {
    "hit": true,
    "level": "semantic"
  }
}
```

---

# Future Extensions

Future additions may include:

- MCP cache
- Tool cache
- Retrieval cache
- Planner cache
- Distributed cache invalidation
- Multi-region cache

---

# Consequences

Positive:

- lower costs
- lower latency
- reusable runtime capability
- agent readiness
- benchmark acceleration

Negative:

- cache invalidation complexity
- stale response risks
- semantic cache quality challenges

These risks are acceptable.
