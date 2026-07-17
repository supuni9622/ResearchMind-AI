# Streaming Platform PRD

Status: Approved

---

# Objective

Introduce real-time execution capabilities into ResearchMind.

Streaming must support:

1. Chat token streaming
2. Research progress updates
3. Agent execution progress
4. Tool execution events
5. Human interrupt workflows

---

# Non Goals

Streaming does NOT implement:

- agents
- research runtime
- MCP
- observability

Only the foundations.

---

# Requirements

## R1

Generation providers support:

```python
stream()
```

---

## R2

Generation service supports:

```python
stream_generate()
```

---

## R3

Streaming must expose canonical events.

---

## R4

Streaming must support SSE.

---

## R5

Streaming must support WebSocket.

---

# Architecture

```text
runtime/events/
generation/streaming/
```

---

# File Structure

## Runtime Event Platform

```text
runtime/

    events/

        models.py
        enums.py
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

            openai.py
            claude.py
            gemini.py
            groq.py
            ollama.py
```

---

## Generation Streaming Platform

```text
generation/

    streaming/

        models.py
        enums.py
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

# Event Model

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

`type` is a plain `str`, not a value drawn from one shared enum — see
"Event Types" below for why.

---

# Event Types

This platform's own Layer 2 vocabulary (`CoreEventType`) is small and fixed:

```python
START
TOKEN
THINKING
COMPLETE
ERROR
```

`PLANNER_STARTED`, `RETRIEVAL_STARTED`, `TOOL_STARTED`, `AGENT_STARTED`,
`VALIDATION_STARTED`, etc. are **not** part of this enum. An earlier draft
of this PRD listed them here directly, which contradicts this PRD's own
Non-Goals (streaming does not implement agents/research/MCP) — those
values belong to Research/Agent/Tool runtimes that don't exist yet, and a
single shared enum they'd all have to extend is exactly the coupling this
platform is meant to avoid. Each future runtime owns its own event-type
enum under `runtime/events/<domain>/models.py` (full layering in
`docs/architecture/streaming-platform.md` and `docs/adrs/ADR-028-streaming-platform.md`).
`VALIDATION_STARTED`/`VALIDATION_COMPLETED` is the one exception worth
naming here since it *is* in scope for the Generation Platform today — it
lives in `generation/streaming/enums.py` as `ValidationEventType`, not
under `runtime/events/`.

---

# Cache Integration

Streaming does not do a blanket cache bypass — a cache hit is replayed as a
simulated token stream instead, so the frontend sees the same streaming
contract regardless of whether the answer came from cache or the provider.
A cache miss streams live and stores the assembled result once the stream
completes (never mid-stream). Full reasoning in
`docs/architecture/streaming-platform.md`'s "Cache Integration" section.

```python
if cache_result.hit:
    # replay cached content as synthetic TOKEN events
    ...
else:
    # stream live, cache the assembled result after COMPLETE
    ...
```

---

# Structured Output

Initial version:

```text
Streaming
=
text only
```

Structured output streaming is deferred.

Future:

- incremental JSON
- partial pydantic parsing

---

# Observability Integration

Future metrics:

```text
TTFT
Tokens/sec
Stream duration
Chunk count
Disconnects
Cancellation rate
```

Streaming must emit sufficient metadata for future observability.

---

# Artifact Integration

Future artifact support:

```text
stream.json

events.json

timeline.json
```

---

# Future Runtime Integration

This platform becomes the foundation for:

```text
Conversation Runtime
Research Runtime
Agent Runtime
Memory Platform
MCP Platform
```

---

# Success Criteria

Chat streaming operational.

Provider-independent event protocol operational.

SSE operational.

Research Runtime can reuse the event system without modification.

Agent Runtime can reuse the event system without modification.

No provider duplication introduced.
