# Runtime Caching Platform PRD

Version: 1.0

Status: Accepted

---

# Overview

The Runtime Caching Platform provides reusable caching capabilities
for all AI runtimes inside ResearchMind.

The platform reduces:

- latency
- provider costs
- duplicate execution

while enabling future:

- conversation sessions
- research sessions
- agent workflows

---

# Motivation

As ResearchMind evolves into:

```text
NotebookLM++
        ↓
Perplexity
        ↓
Open Deep Research
        ↓
Agent Platform
```

LLM invocations will grow exponentially.

Caching becomes essential.

---

# Objectives

---

## Objective 1

Reduce provider costs.

---

## Objective 2

Improve runtime latency.

---

## Objective 3

Provide reusable infrastructure.

---

## Objective 4

Support future platforms.

---

# Scope

The platform provides:

### L1 Exact Cache

### L2 Semantic Cache

### L3 Session Cache

---

# Non Goals

The platform does not provide:

- Retrieval Cache
- Tool Cache
- MCP Cache
- Long-Term Memory
- Planner State

---

# Architecture

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
Cache Policy
        ↓
L1 Exact Cache
        ↓
L2 Semantic Cache
        ↓
Provider
        ↓
Store Results
```

---

# Package Structure

```text
generation/

    caching/

        models.py
        enums.py
        interfaces.py
        exceptions.py
        service.py
        create.py

        exact/
        semantic/
        session/
        policies/
```

---

# Functional Requirements

---

# FR-1 Exact Cache

System shall:

- hash requests
- lookup responses
- reuse GenerationResult

---

# FR-2 Semantic Cache

System shall:

- embed prompts
- perform similarity lookup
- reuse responses

---

# FR-3 Session Cache

System shall:

- store session-scoped data
- support invalidation
- support clearing sessions

---

# FR-4 Policy Resolution

System shall support:

```text
AUTO
NEVER
EXACT_ONLY
SEMANTIC
SESSION
```

---

# FR-5 Statistics

System shall collect:

- hit ratio
- latency
- cost savings
- token savings

---

# Exact Cache Design

---

## Key

```text
provider
model
routing_strategy
prompt_hash
context_hash
schema_hash
temperature
top_p
```

---

## Storage

Valkey.

---

## TTL

Chat:

```text
2 hours
```

Research:

```text
24 hours
```

Benchmarks:

```text
infinite
```

---

# Semantic Cache Design

---

## Technology

Leverage LangChain.

Implementation:

```text
RedisSemanticCache
```

---

## Similarity Threshold

```text
0.92
```

---

## Constraints

Context hash must be included.

---

# Session Cache Design

---

## Conversation

```text
session_id
```

---

## Research

```text
research_session_id
```

---

## Agent Runtime

```text
run_id
```

---

# Default Runtime Policies

| Runtime | Policy |
|----------|---------|
| Chat | AUTO |
| Research | SEMANTIC |
| Benchmark | EXACT_ONLY |
| Planner | NEVER |
| Tool Agent | NEVER |
| Summarizer | AUTO |
| Reviewer | NEVER |
| Critic | NEVER |

---

# Observability Requirements

Metrics:

```text
cache_hit
cache_level
cache_latency_ms
tokens_saved
cost_saved
```

---

# Artifact Requirements

Generation artifacts should persist:

```json
{
  "cache": {
    "hit": true,
    "level": "semantic"
  }
}
```

---

# Streaming Requirements

Streaming bypasses cache.

Reason:

- partial responses
- progress events
- token streaming

---

# Future Roadmap

Phase 1

```text
L1 Exact Cache
```

Phase 2

```text
L2 Semantic Cache
```

Phase 3

```text
L3 Session Cache
```

Phase 4

```text
Tool Cache
MCP Cache
Distributed Cache
```

---

# Success Metrics

Target:

```text
>50% exact cache hit ratio
>25% semantic cache hit ratio
30-60% cost reduction
40-70% latency reduction
```

---

# Exit Criteria

The Runtime Caching Platform is complete when:

- Exact Cache operational
- Semantic Cache operational
- Session Cache operational
- Policies operational
- Generation integration completed
- Metrics exposed
- Artifact integration completed
