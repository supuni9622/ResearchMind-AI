# ADR-028: Streaming Platform Architecture

**Status:** Accepted

**Date:** 2026-07-17

---

# Context

ResearchMind currently supports synchronous generation through the Generation Platform.

Upcoming platforms require real-time execution capabilities:

- Chat Runtime
- Research Runtime
- Deep Research
- Agent Runtime
- LangGraph Workflows
- MCP Runtime
- Human Approval Workflows

Streaming is therefore a foundational runtime capability rather than merely a frontend feature.

Streaming must support:

1. Token streaming
2. Research progress updates
3. Agent execution updates
4. Tool execution events
5. Human interrupts
6. Future observability and tracing
7. Future artifact generation
8. Runtime event replay

Streaming should not be designed only for chat generation.

It must become the canonical event infrastructure for all future runtime platforms.

---

# Decision

Streaming will be implemented as two independent but related platforms.

## Runtime Event Platform

```text
app/ai/runtime/events/
```

Responsibilities:

- Canonical event protocol
- Event definitions
- Event normalization
- Provider event adapters
- Runtime-independent event architecture
- Event serialization
- Shared protocol across all runtimes

---

## Generation Streaming Platform

```text
app/ai/runtime/generation/streaming/
```

Responsibilities:

- Provider stream orchestration
- SSE support
- WebSocket support
- Stream lifecycle management
- Cancellation handling
- Event emission
- Future observability integration

---

# Rejected Alternatives

## Alternative 1

```text
generation/streaming/providers/
```

Rejected.

Example:

```text
generation/
    streaming/
        providers/
            openai.py
            claude.py
            gemini.py
            groq.py
            ollama.py
```

Reasons:

- Duplicates provider SDK integrations
- Duplicates retry logic
- Duplicates token extraction logic
- Creates maintenance burden
- Forces future refactors for agents
- Violates provider ownership boundaries

Streaming is merely another execution mode of providers.

Providers remain responsible for:

- SDK integrations
- Provider-specific chunk parsing
- Provider-specific metadata extraction
- Token extraction
- Cost extraction
- Usage extraction

Streaming platform only normalizes events.

---

## Alternative 2

Build streaming only for chat.

Rejected.

Future platforms such as Research Runtime and Agent Runtime require:

- Progress updates
- Tool execution events
- Planner events
- Human approval events
- Workflow execution events

A chat-only architecture would require significant refactoring.

---

# Architecture

```text
Provider SDK Stream
        ↓
Provider.stream()
        ↓
Provider Event Adapter
        ↓
Canonical StreamEvent
        ↓
Streaming Service
        ↓
SSE / WebSocket
        ↓
Frontend
```

---

# Platform Structure

```text
runtime/

    events/

generation/

    streaming/
```

---

# Runtime Event Platform

Purpose:

Provide a single canonical event protocol for every future runtime.

Future runtimes:

- Generation Runtime
- Conversation Runtime
- Research Runtime
- Agent Runtime
- MCP Runtime
- Tool Runtime
- Human Approval Runtime

All runtimes must communicate through this protocol.

---

# Event Hierarchy

## Layer 1 — Provider Events

Provider-specific.

Examples:

- OpenAI delta chunks
- Claude content blocks
- Gemini candidates
- Ollama chunks

These events never leave provider boundaries.

---

## Layer 2 — Canonical Stream Events

```python
class StreamEvent(BaseModel):
    event_id: UUID
    session_id: UUID | None
    request_id: UUID | None
    parent_event_id: UUID | None
    category: EventCategory
    type: str
    timestamp: datetime
    content: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

Provider independent. Used throughout the platform.

`type` is a plain `str`, not a value drawn from one shared enum. `CoreEventType`
(`START`, `TOKEN`, `THINKING`, `COMPLETE`, `ERROR`) is the only enum the
canonical model itself depends on. Every Layer 3 runtime defines and owns its
own event-type enum under `runtime/events/<domain>/models.py` and populates
`type` with its own values — the canonical model never imports them.

This is a deliberate correction from an earlier draft of this ADR, which
listed research/agent event values directly inside one shared
`StreamEventType` enum. That would mean every future runtime has to add
members to a shared enum before it can emit events through this platform —
directly contradicting this ADR's own Non-Goals (streaming does not
implement Research/Agent Runtime) and the Success Criteria elsewhere in this
document ("Agent Runtime can reuse the event system without modification").
A runtime-owned-enum-per-domain, with a stable envelope and a `str` type
field, is what actually satisfies that criterion.

---

## Layer 3 — Runtime Events

Each runtime owns its own enum, reserved ahead of the runtime existing so it
never has to modify shared platform code to add events. Examples:

Research (`runtime/events/research/models.py`, `ResearchEventType`):

```text
RESEARCH_STARTED / RESEARCH_COMPLETED
PLANNER_STARTED / PLANNER_COMPLETED
RETRIEVAL_STARTED / RETRIEVAL_COMPLETED
REPORT_STARTED / REPORT_COMPLETED
```

Agent (`runtime/events/agent/models.py`, `AgentEventType`):

```text
AGENT_STARTED / AGENT_COMPLETED
NODE_STARTED / NODE_COMPLETED
TOOL_STARTED / TOOL_COMPLETED
HUMAN_APPROVAL_REQUIRED
```

Tool (`runtime/events/tool/models.py`, `ToolEventType`):

```text
TOOL_STARTED
TOOL_COMPLETED
TOOL_FAILED
```

None of these are emitted by this change set — no Research, Agent, or Tool
runtime exists yet. They are reserved so those runtimes, once built, only
need to import their own enum, not modify this platform.

---

# Canonical Event Flow

```text
Provider Event
        ↓
Provider Adapter
        ↓
StreamEvent
        ↓
Streaming Runtime
        ↓
Frontend
```

---

# Provider Ownership

Providers continue to own:

```text
generation/providers/

    openai.py
    claude.py
    gemini.py
    groq.py
    ollama.py
```

No streaming providers will be created.

Providers expose:

```python
generate()

generate_structured()

stream()
```

Future:

```python
stream_generate()
```

No duplicated provider hierarchy will exist.

---

# LangChain Integration

LangChain streaming capabilities will be leveraged where appropriate.

### Chat Streaming

```python
astream()
```

### Runtime Event Streaming

```python
astream_events()
```

Required for:

- LangGraph
- Agents
- Research Runtime
- Tool execution
- Human interrupts

---

# Transport Protocols

## Server Sent Events (Primary)

Used for:

- Chat
- Research
- Agents
- Deep Research Progress

Advantages:

- Simple
- HTTP compatible
- Works well with FastAPI
- Easy frontend integration

---

## WebSockets (Optional)

Used for:

- Collaborative workflows
- Bidirectional communication
- Future enterprise workflows

---

# Cache Integration

Streaming does not do a blanket cache bypass.

An earlier draft of this ADR bypassed the Runtime Cache entirely whenever
`request.stream` was set, reasoning that "cached responses should return
immediately." In practice that breaks the frontend's streaming contract: a
cache hit would return as one instant, non-streamed payload while the caller
asked for a stream, forcing the frontend to special-case cached vs.
live responses. Production chat products (e.g. ChatGPT, Perplexity) instead
replay a cached answer as a simulated token stream, so the UX is identical
whether the answer came from cache or from the provider.

Decision:

- On a cache lookup **hit**: emit a `START` event carrying
  `metadata["cache"] = {"hit": true, "level": ...}`, then split the cached
  content into `TOKEN` events, then `COMPLETE`. No provider call is made.
- On a cache lookup **miss**: stream live from the provider. Partial output
  is never written to cache mid-stream (streaming metrics/partial content
  cannot be cached reliably — that reasoning from the original draft still
  holds). Once the stream reaches `COMPLETE`, the assembled full result is
  stored, exactly like a synchronous `generate()` call.

```python
cache_result = await caching_service.lookup(...)
if cache_result.hit:
    # replay cache_result content as synthetic TOKEN events
    ...
else:
    # stream live, accumulate content, store the final result on COMPLETE
    ...
```

---

# Production Considerations

Gaps identified against current production streaming practice, addressed by
the Generation Streaming Platform's transport layer:

- **SSE keep-alive**: browsers and load balancers (e.g. an idle-timeout ALB)
  will drop an SSE connection with no traffic. The SSE transport emits a
  `: ping` comment line on an interval when no real event has been sent.
- **Proxy buffering**: the SSE response sets `X-Accel-Buffering: no` and
  `Cache-Control: no-cache` so an intermediary nginx/proxy does not buffer
  the whole response before forwarding it.
- **Stream timeout ceiling**: a hard maximum duration is enforced so a hung
  provider stream cannot hold a connection (and a worker) open indefinitely.
- **Browser auth limitations**: the browser `EventSource` API cannot send a
  custom `Authorization` header, which matters here since this platform's
  auth is Bearer `id_token`. The SSE endpoint is therefore a `POST` consumed
  via `fetch` + `ReadableStream` on the frontend, not a bare `EventSource` —
  the `Authorization` header still applies normally. The WebSocket endpoint
  has the same limitation at the handshake and authenticates via a `?token=`
  query parameter instead.

---

# Structured Output Integration

Initial version:

```text
Streaming
=
Text Only
```

Structured output streaming is deferred.

Future possibilities:

- Incremental JSON
- Partial schema validation
- Progressive parsing

---

# Future Event Sources

The architecture must support:

- Generation Runtime
- Research Runtime
- Agent Runtime
- MCP Runtime
- Tool Runtime
- Human Approval Runtime

without API changes.

---

# Observability Integration

Streaming introduces new runtime metrics.

Future metrics:

- Time To First Token (TTFT)
- Tokens per second
- Stream duration
- Chunk count
- Disconnect count
- Cancellation rate
- Partial completion rate

Observability Platform will consume StreamEvents.

---

# Artifact Integration

Future artifacts:

```text
artifacts/

    stream.json
    events.json
    timeline.json
```

Streaming architecture must emit sufficient metadata to support replay and debugging.

---

# Consequences

## Benefits

- Single event protocol
- Stable frontend APIs
- Reusable by LangGraph
- Reusable by Agents
- Reusable by Observability
- Reusable by Artifacts
- Eliminates future refactors
- Supports deep research workflows

## Tradeoffs

- Additional abstraction layer
- Event normalization overhead
- Slight increase in implementation complexity

The benefits significantly outweigh the costs.

---

# Final Architecture

```text
Provider SDK Stream
            ↓
Provider.stream()
            ↓
Provider Adapter
            ↓
Canonical StreamEvent
            ↓
Streaming Service
            ↓
SSE / WebSocket
            ↓
Frontend
```

This architecture becomes the foundation for:

```text
Conversation Runtime
↓
Research Runtime
↓
Agent Runtime
↓
Memory Platform
↓
MCP Platform
```

without further architectural redesign.
