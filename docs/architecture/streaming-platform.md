# Streaming Platform Architecture

---

# Overview

The Streaming Platform provides production-grade real-time execution capabilities across the entire ResearchMind ecosystem.

Streaming is not limited to chat token generation.

It becomes the foundational event infrastructure for:

- Chat Runtime
- Conversation Runtime
- Research Runtime
- Deep Research
- Agent Runtime
- LangGraph Workflows
- MCP Runtime
- Human Approval Workflows
- Future Multi-Agent Systems

The platform introduces a unified event protocol that can be consumed by:

- Frontend applications
- Observability Platform
- Artifact Platform
- Evaluation Platform
- Future replay systems

---

# Goals

## Primary Goals

- Support token streaming from LLM providers
- Support runtime progress updates
- Support future agent execution streaming
- Support tool execution events
- Support long-running research workflows
- Support event replay and tracing
- Provide a provider-independent event protocol

---

# Non Goals

Streaming Platform does NOT implement:

- Agent Runtime
- Research Runtime
- MCP Runtime
- Human approval workflows
- Evaluation systems
- Observability dashboards

Only the foundational infrastructure required by these platforms.

---

# High Level Architecture

```text
Provider SDK
        ↓
Provider.stream()
        ↓
Provider Event Adapter
        ↓
Canonical StreamEvent
        ↓
Streaming Service
        ↓
Transport Layer
        ↓
Frontend
```

---

# Platform Structure

Streaming is divided into two independent layers.

---

# 1. Runtime Event Platform

Purpose:

Provide a canonical event protocol across the entire system.

Location:

```text
app/ai/runtime/events/
```

Responsibilities:

- Event definitions
- Event normalization
- Event adapters
- Serialization
- Runtime-independent protocol

---

# 2. Generation Streaming Platform

Purpose:

Provide real-time execution support for generation workloads.

Location:

```text
app/ai/runtime/generation/streaming/
```

Responsibilities:

- Provider stream orchestration
- Stream lifecycle management
- SSE support
- WebSocket support
- Cancellation support
- Event emission

---

# Folder Structure

## Runtime Event Platform

```text
runtime/

    events/

        enums.py
        models.py
        interfaces.py
        create.py

        provider/

            models.py

        research/

            models.py

        agent/

            models.py

        tool/

            models.py

        adapters/

            base.py
```

Every provider's `stream()` already normalizes its SDK-specific chunks into
the identical `StreamChunk` shape (`event`, `content`, `metadata` — see
`generation/models.py`) before anything leaves the provider. So by the time
an event reaches this platform, Layer 1 normalization has already happened;
one `GenericStreamChunkAdapter` in `adapters/base.py` converts `StreamChunk`
→ `StreamEvent` for every provider. Creating a separate near-identical
`openai.py` / `claude.py` / `gemini.py` / `groq.py` / `ollama.py` adapter
file per provider — as an earlier draft of this doc proposed — would itself
be the provider-duplication this architecture explicitly rejects (see "Why
No Streaming Providers?" below). A provider only needs its own adapter file
if its `stream()` ever needs to emit something `StreamChunk` can't
represent; none do today.

---

## Generation Streaming Platform

```text
generation/

    streaming/

        enums.py
        models.py
        interfaces.py
        service.py
        create.py

        transports/

            sse.py
            websocket.py

        serializers/

            sse.py
            json.py
```

---

# Provider Architecture

Providers remain responsible for all provider-specific logic.

Existing structure remains unchanged.

```text
generation/

    providers/

        openai.py
        claude.py
        gemini.py
        groq.py
        ollama.py
```

Providers expose:

```python
generate()

generate_structured()

stream()
```

or

```python
stream_generate()
```

---

# Why No Streaming Providers?

The following architecture is intentionally rejected:

```text
streaming/

    providers/

        openai.py
        claude.py
```

Reasons:

- Duplicated SDK integrations
- Duplicated retries
- Duplicated metadata extraction
- Duplicated token handling
- Future maintenance burden

Streaming is merely another execution mode.

Providers remain owners of provider behavior.

---

# Event Architecture

Streaming uses a three-layer event model.

---

# Layer 1 — Provider Events

Provider-specific.

Examples:

OpenAI:

```text
ChatCompletionChunk
```

Claude:

```text
MessageDeltaEvent
```

Gemini:

```text
GenerateContentResponseChunk
```

These events never leave provider boundaries.

---

# Layer 2 — Canonical Stream Events

Provider-independent.

Used across the entire platform.

```python
class StreamEvent(BaseModel):

    event_id: UUID

    session_id: UUID | None

    request_id: UUID | None

    parent_event_id: UUID | None

    category: EventCategory

    type: str

    timestamp: datetime

    content: str | None

    metadata: dict[str, Any]
```

`type` is a plain `str`, not a value drawn from one shared enum, and
`category` (`EventCategory`: GENERATION / RESEARCH / AGENT / TOOL) says which
domain it belongs to. `CoreEventType` (`START`, `TOKEN`, `THINKING`,
`COMPLETE`, `ERROR`) is the only enum the canonical model itself depends on.

An earlier draft of this section had `type: StreamEventType` pointing at one
enum that combined generation, research, agent, and validation values —
directly contradicting this document's own Non-Goals (no Research/Agent
Runtime here) and the Benefits section's claim that Agent/Research runtimes
can "reuse the event system without modification," since adding their events
would mean editing that shared enum. Each Layer 3 runtime instead owns its
own event-type enum (below), so nothing here has to change when a new
runtime is added.

---

# Layer 3 — Runtime Events

Specialized events used by future runtimes. Each runtime defines and owns
its own enum under `runtime/events/<domain>/models.py` — the canonical
model above never imports them.

Research (`ResearchEventType`):

```text
RESEARCH_STARTED / RESEARCH_COMPLETED
PLANNER_STARTED / PLANNER_COMPLETED
RETRIEVAL_STARTED / RETRIEVAL_COMPLETED
REPORT_STARTED / REPORT_COMPLETED
```

Agent (`AgentEventType`):

```text
AGENT_STARTED / AGENT_COMPLETED
NODE_STARTED / NODE_COMPLETED
TOOL_STARTED / TOOL_COMPLETED
HUMAN_APPROVAL_REQUIRED
```

Tool (`ToolEventType`):

```text
TOOL_STARTED
TOOL_COMPLETED
TOOL_FAILED
```

None of these are emitted by this change set — no Research, Agent, or Tool
runtime exists yet. They are reserved so those runtimes only need their own
enum, never a change to this platform.

---

# Event Flow

```text
Provider Event
        ↓
Provider Adapter
        ↓
StreamEvent
        ↓
Streaming Service
        ↓
Transport Layer
        ↓
Frontend
```

---

# Stream Event Types

Grouped by domain for readability only — these are separate enums (see
Layer 3 above), not members of one shared `StreamEventType`.

## Generation Events (`CoreEventType`, canonical, Layer 2)

```python
START
TOKEN
THINKING
COMPLETE
ERROR
```

---

## Research Events

```python
RESEARCH_STARTED
RESEARCH_COMPLETED

PLANNER_STARTED
PLANNER_COMPLETED

RETRIEVAL_STARTED
RETRIEVAL_COMPLETED

REPORT_STARTED
REPORT_COMPLETED
```

---

## Agent Events

```python
AGENT_STARTED
AGENT_COMPLETED

NODE_STARTED
NODE_COMPLETED

TOOL_STARTED
TOOL_COMPLETED

HUMAN_APPROVAL_REQUIRED
```

---

## Validation Events (`ValidationEventType`, generation-scoped)

```python
VALIDATION_STARTED
VALIDATION_COMPLETED
```

Validation is a Generation Platform concern (see
`generation/validation/service.py`), not a Layer 3 runtime, so this enum
lives in `generation/streaming/enums.py` rather than under
`runtime/events/<domain>/` alongside Research/Agent/Tool.

---

# Canonical Event Model

Same model as Layer 2 above — repeated here for reference:

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

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
```

---

# Stream Lifecycle

```text
START
 ↓
TOKEN*
 ↓
COMPLETE
```

Error Flow:

```text
START
 ↓
TOKEN*
 ↓
ERROR
```

Research Flow:

```text
RESEARCH_STARTED
 ↓
PLANNER_STARTED
 ↓
RETRIEVAL_STARTED
 ↓
TOKEN*
 ↓
REPORT_COMPLETED
```

Agent Flow:

```text
AGENT_STARTED
 ↓
TOOL_STARTED
 ↓
TOOL_COMPLETED
 ↓
TOKEN*
 ↓
AGENT_COMPLETED
```

---

# Streaming Service Flow

```text
GenerationService
        ↓
Provider.stream()
        ↓
Provider Adapter
        ↓
StreamEvent
        ↓
Serializer
        ↓
Transport
```

---

# LangChain Integration

---

## Token Streaming

```python
llm.astream()
```

Used for:

- Chat Runtime
- Simple generation streaming

---

## Event Streaming

```python
llm.astream_events()
```

Used for:

- Research Runtime
- LangGraph
- Agent Runtime
- Tool execution
- Human approval workflows

---

# Transport Layer

---

# Server Sent Events (Primary)

Primary transport protocol.

Used for:

- Chat
- Research
- Agents
- Deep Research

Advantages:

- Simple implementation
- Native browser support
- HTTP compatible
- Easy scaling

---

# WebSocket (Optional)

Used for:

- Collaborative workflows
- Bidirectional communication
- Future enterprise workflows

---

# Production Considerations

Gaps identified against current production streaming practice:

- **SSE keep-alive.** Browsers and load balancers with an idle-connection
  timeout (e.g. an ALB in front of this API) will drop an SSE connection
  with no traffic. The SSE transport emits a `: ping` comment line on an
  interval when no real event has been sent.
- **Proxy buffering.** The SSE response sets `X-Accel-Buffering: no` and
  `Cache-Control: no-cache` so an intermediary proxy does not buffer the
  whole response before forwarding chunks to the client.
- **Stream timeout ceiling.** A hard maximum duration is enforced so a hung
  provider stream cannot hold a connection (and a server worker) open
  indefinitely.
- **Browser auth limitations.** The browser `EventSource` API cannot attach
  a custom `Authorization` header, which matters because this platform's
  auth is Bearer `id_token` (Cognito). The SSE endpoint is a `POST`
  consumed via `fetch` + `ReadableStream` on the frontend rather than a bare
  `EventSource`, so the `Authorization` header still applies. The
  WebSocket endpoint has the same limitation at the handshake and
  authenticates via a `?token=` query parameter instead.

---

# Serialization

## SSE Example

```text
event: token
data: {
  "content": "Hello"
}
```

---

## JSON Example

```json
{
  "type": "TOKEN",
  "content": "Hello"
}
```

---

# Cancellation

Streaming must support:

- User cancellation
- Browser disconnects
- Runtime interrupts
- Human approval pauses

Future APIs:

```python
cancel_stream()
pause_stream()
resume_stream()
```

---

# Cache Integration

Streaming does not do a blanket cache bypass.

An earlier draft of this document bypassed the Runtime Cache entirely
whenever `request.stream` was set, reasoning that "cached responses should
return immediately." In practice that breaks the frontend's streaming
contract: a cache hit would return as one instant, non-streamed payload
while the caller asked for a stream, forcing the frontend to special-case
cached vs. live responses. Production chat products (e.g. ChatGPT,
Perplexity) instead replay a cached answer as a simulated token stream, so
the UX is identical whether the answer came from cache or the provider.

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

# Structured Outputs

Initial implementation:

```text
Streaming
=
Text Only
```

Deferred capabilities:

- Incremental JSON parsing
- Partial schema validation
- Progressive Pydantic parsing

---

# Observability Integration

Future metrics:

```text
Time To First Token
Tokens Per Second
Stream Duration
Chunk Count
Disconnect Count
Cancellation Rate
Partial Completion Rate
```

StreamEvents become inputs to the Observability Platform.

---

# Artifact Integration

Future artifacts:

```text
artifacts/

    stream.json
    events.json
    timeline.json
```

Streaming architecture must support replay and debugging.

---

# Future Runtime Integrations

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

without requiring architectural redesign.

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
Serializer
            ↓
SSE / WebSocket
            ↓
Frontend
```

---

# Benefits

- Provider-independent event protocol
- Stable frontend APIs
- Reusable by LangGraph
- Reusable by Agents
- Reusable by Observability
- Reusable by Artifacts
- Enables deep research workflows
- Eliminates future refactors
- Provides event replay capability

---

# Tradeoffs

- Additional abstraction layer
- Event normalization overhead
- Slight increase in implementation complexity

The long-term architectural benefits significantly outweigh these costs.
