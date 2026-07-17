# Runtime Caching Platform Architecture

---

# Goal

Provide reusable caching capabilities for all future AI runtimes.

Including:

- Chat Runtime
- Research Runtime
- Agent Runtime
- Evaluation Runtime

---

# Philosophy

Caching is a platform.

It is not:

- provider logic
- LangChain logic
- agent logic

Every runtime consumes the same caching platform.

---

# High Level Architecture

```text
Generation Request
        ↓
Cache Policy Resolver
        ↓

    L1 Exact Cache
            ↓ miss

    L2 Semantic Cache
            ↓ miss

    Provider
            ↓

Store Response
            ↓

L1 + L2 + Session Cache
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
            key_builder.py
            provider.py

        semantic/
            provider.py

        session/
            provider.py

        policies/
            models.py
            service.py
```

---

# Canonical Models

---

## CacheLevel

```python
EXACT
SEMANTIC
SESSION
```

---

## CachePolicy

```python
AUTO
NEVER
EXACT_ONLY
SEMANTIC
SESSION
```

---

## CacheResult

```python
class CacheResult:

    hit: bool

    level: CacheLevel | None

    generation_result: GenerationResult | None
```

---

## CacheStatistics

```python
class CacheStatistics:

    exact_hits: int

    semantic_hits: int

    session_hits: int

    misses: int

    hit_ratio: float

    tokens_saved: int

    cost_saved: float
```

---

# L1 Exact Cache

---

## Workflow

```text
Request
      ↓
Key Builder
      ↓
Valkey
      ↓
GenerationResult
```

---

## Cache Key

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

## TTL Recommendations

| Runtime | TTL |
|----------|-----|
| Chat | 2h |
| Research | 24h |
| Benchmark | Infinite |

---

# L2 Semantic Cache

---

## Workflow

```text
Prompt
      ↓
Embedding
      ↓
Similarity Search
      ↓
Threshold
      ↓
Reuse Response
```

---

## Technology

Leverage:

- LangChain RedisSemanticCache

No custom implementation.

---

## Threshold

Default:

```text
0.92
```

---

## Constraints

Semantic cache keys additionally require:

```text
context_hash
```

---

# L3 Session Cache

---

## Purpose

Provide execution state reuse.

---

## Session Types

### Conversation Session

```text
session_id
```

### Research Session

```text
research_session_id
```

### Agent Session

```text
run_id
```

---

# Policy Resolution

```text
Generation Request
            ↓
Policy Resolver
            ↓
Cache Strategy
```

---

## Examples

Planner:

```text
NEVER
```

Research:

```text
SEMANTIC
```

Chat:

```text
AUTO
```

---

# Streaming

Streaming does not bypass this platform's `lookup()`/`store()` — a
streaming request is looked up and stored exactly like a non-streaming one
(content-addressed on the same key). What can never be cached is a
*partial*, in-flight stream: `store()` is only ever called once a result
is fully assembled.

On a cache hit for a streaming request, the caller (the Generation
Streaming Platform, see `docs/architecture/streaming-platform.md`) replays
the cached content as a synthetic token stream rather than skipping the
stream contract altogether — this is a correction from an earlier draft of
this document, which had `CachingService` bypass caching entirely whenever
`request.stream` was set, forcing a cache hit to return as one instant
non-streamed payload while the caller asked for a stream.

---

# Observability Integration

Metrics:

```text
cache_hit
cache_level
cache_latency_ms
tokens_saved
cost_saved
```

---

# Artifact Integration

Generation artifacts should persist:

```json
{
  "cache": {
    "hit": true,
    "level": "exact",
    "tokens_saved": 2400,
    "cost_saved": 0.024
  }
}
```

---

# Future Evolution

Phase 1

- Exact Cache

Phase 2

- Semantic Cache

Phase 3

- Session Cache

Phase 4

- Distributed Cache

Phase 5

- Tool Cache
