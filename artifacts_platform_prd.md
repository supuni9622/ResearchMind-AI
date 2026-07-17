# ResearchMind — Artifact Platform PRD

**Document Version:** 1.1
**Platform:** Artifact Platform
**Milestone:** 3.10
**Status:** Ready for Implementation
**Owner:** ResearchMind Core Platform

---

# 1. Overview

The Artifact Platform provides canonical persistence, replay, debugging, evaluation, and observability capabilities across ResearchMind.

Artifacts become the primary source of truth for important AI executions.

This platform extends the existing artifact patterns already used in:

- Processing Platform
- Chunking Platform
- Embedding Platform
- Indexing Platform
- Guardrails Platform

---

# 2. Motivation

ResearchMind already generates artifacts for knowledge ingestion.

However, AI Runtime artifacts are still missing.

This limits:

- Replay
- Debugging
- Observability
- Regression Testing
- Evaluation Dataset Generation
- Session Reconstruction
- Research Reproducibility

---

# 3. Goals

## Primary Goals

### Canonical Persistence

Persist important AI execution state.

### Replayability

Allow reconstruction of executions.

### Evaluation Foundation

Provide datasets for:

- LangSmith
- DeepEval
- Ragas
- Regression Testing

### Observability Foundation

Artifacts become the primary data source for:

- Metrics
- Cost Analytics
- Tracing
- Dashboards

### Research Reproducibility

Allow deterministic reconstruction of:

- Prompts
- Retrievals
- Citations
- Reports

---

# 4. Non Goals

The Artifact Platform DOES NOT own:

- Metrics
- Dashboards
- Tracing
- Runtime Orchestration
- Generation Logic
- Evaluation Logic

The platform only persists execution state.

---

# 5. Architectural Principles

---

## Principle 1

Artifacts are immutable.

Artifacts must never be modified after persistence.

---

## Principle 2

Artifacts are versioned.

```python
artifact_version: str = "1.0"
```

---

## Principle 3

Artifacts are append-only.

---

## Principle 4

Artifacts are provider independent.

No provider SDK models should leak into artifacts.

---

## Principle 5

Artifacts become the system source of truth.

Metrics, evaluations, replay, and observability derive from artifacts.

---

# 6. Persistence Philosophy

Not every LLM call should create permanent artifacts.

Persisting every generation would create:

- excessive storage costs
- noisy datasets
- massive artifact counts
- unnecessary S3 growth

Artifacts should only be generated for persistence-worthy executions.

---

# 7. Artifact Categories

---

## Category 1 — Canonical Artifacts

Always persisted.

Examples:

- Processing artifacts
- Chunk artifacts
- Embedding artifacts
- Indexing artifacts
- Research artifacts
- Evaluation artifacts

---

## Category 2 — Runtime Artifacts

Persist according to policies.

Examples:

- Chat sessions
- Agent executions
- Research sessions

---

## Category 3 — Internal Runtime Calls

Usually NOT persisted.

Examples:

- Compression prompts
- Internal summarization calls
- Repair calls
- Routing helper prompts
- Planner helper generations
- Citation generation prompts

These should produce:

- logs
- metrics
- traces

instead of permanent artifacts.

---

# 8. Artifact Policy Platform

Artifact persistence should be policy driven.

---

## ArtifactPolicy

```python
class ArtifactPolicy(str, Enum):

    NEVER = "never"

    SESSION = "session"

    SHORT_TERM = "short_term"

    LONG_TERM = "long_term"

    PERMANENT = "permanent"
```

---

## Example Policies

| Runtime | Policy |
|----------|---------|
| Internal Helper Calls | NEVER |
| Chat Runtime | SESSION |
| Research Runtime | PERMANENT |
| Agent Runtime | LONG_TERM |
| Benchmarks | PERMANENT |
| Evaluations | PERMANENT |

---

## Service Interface

```python
class ArtifactPolicyService:

    def should_persist(
        self,
        runtime,
        execution_type,
    ) -> bool:
        ...
```

---

# 9. Responsibilities

The Artifact Platform owns:

- Artifact Models
- Builders
- Writers
- Readers
- Replay Interfaces
- Retention Policies
- Storage Abstractions
- Artifact Policies

---

# 10. Platform Architecture

```text
Runtime
      ↓
Artifact Builder
      ↓
Artifact Policy
      ↓
Artifact Writer
      ↓
Storage
      ↓
Artifact Reader
      ↓
Replay / Evaluation / Observability
```

---

# 11. Folder Structure

```text
app/ai/artifacts/

    models.py
    enums.py
    interfaces.py
    exceptions.py

    create.py
    service.py

    policies/
        models.py
        service.py

    builders/
    writers/
    readers/
    replay/

    generation/
    streaming/
    conversation/
    research/
    agent/
    evaluation/
```

---

# 12. Storage Layout

```text
artifacts/

    generations/
    streams/
    conversations/
    sessions/
    research/
    agents/
    evaluations/
```

---

# 13. Generation Artifacts

---

## Goal

Persist important user-visible generations.

Not every generation should be persisted.

---

## Storage

```text
artifacts/

    generations/

        {generation_id}/
```

---

## Files

```text
request.json
response.json
metadata.json
validation.json
guardrails.json
routing.json
cache.json
```

---

## request.json

```json
{
  "prompt": "...",
  "provider": "...",
  "model": "...",
  "runtime": "chat"
}
```

---

## response.json

```json
{
  "content": "...",
  "parsed_output": {},
  "usage": {}
}
```

---

## metadata.json

```json
{
  "generation_id": "...",
  "session_id": "...",
  "duration_ms": 0
}
```

---

## guardrails.json

Persist:

- GuardrailReport
- Risk Scores
- Actions

---

## validation.json

Persist:

- ValidationReport
- Issues
- Scores

---

# 14. Streaming Artifacts

Streaming introduced entirely new debugging requirements.

---

## Storage

```text
artifacts/

    streams/

        {stream_id}/
```

---

## Files

```text
events.json
timeline.json
stream.json
metrics.json
```

---

## events.json

Contains every emitted StreamEvent.

---

## timeline.json

Contains:

- generation started
- first token
- completion
- disconnects

---

## metrics.json

Contains:

- first token latency
- stream duration
- tokens/sec
- disconnect count

---

# 15. Conversation Artifacts

---

## Storage

```text
artifacts/

    conversations/

        {conversation_id}/
```

---

## Files

```text
conversation.json
messages.json
summary.json
```

---

# 16. Session Artifacts

---

## Storage

```text
artifacts/

    sessions/

        {session_id}/
```

---

## Files

```text
session.json
timeline.json
statistics.json
```

---

## Purpose

Foundation for:

- Replay
- Analytics
- Debugging
- Observability

---

# 17. Research Artifacts

---

## Storage

```text
artifacts/

    research/

        {research_id}/
```

---

## Files

```text
plan.json
queries.json
retrievals.json
citations.json
report.json
evaluation.json
```

---

## retrievals.json

Persist:

- Dense Results
- Sparse Results
- Hybrid Results
- Reranked Results
- Scores

---

# 18. Agent Artifacts

Future Runtime Foundation.

---

## Storage

```text
artifacts/

    agents/

        {run_id}/
```

---

## Files

```text
state.json
tools.json
execution_graph.json
events.json
memory.json
```

---

# 19. Evaluation Artifacts

---

## Storage

```text
artifacts/

    evaluations/

        {evaluation_id}/
```

---

## Files

```text
dataset.json
results.json
metrics.json
comparison.json
```

---

# 20. Canonical Models

---

## ArtifactMetadata

```python
class ArtifactMetadata(BaseModel):

    artifact_id: UUID

    version: str

    created_at: datetime

    owner_id: UUID | None

    session_id: UUID | None
```

---

## GenerationArtifact

```python
class GenerationArtifact(BaseModel):

    metadata: ArtifactMetadata

    request: GenerationRequest

    response: GenerationResult
```

---

## StreamArtifact

```python
class StreamArtifact(BaseModel):

    metadata: ArtifactMetadata

    events: list[StreamEvent]
```

---

# 21. Replay Platform

---

## Supported Replays

### Generation Replay

```text
Stored Prompt
      ↓
Stored Context
      ↓
Stored Result
```

---

### Stream Replay

```text
Stored Events
      ↓
Re-Emit SSE Events
```

---

### Research Replay

```text
Plan
 ↓
Retrievals
 ↓
Generation
 ↓
Final Report
```

---

# 22. Storage Providers

## Initial

- Local Storage
- Amazon S3

---

## Future

- PostgreSQL Metadata Store
- Glacier Archive

---

# 23. Retention Policies

Retention should be configurable.

Default policies:

| Artifact | Retention |
|-----------|------------|
| Internal Runtime | Not Persisted |
| Chat Sessions | 30 Days |
| Generation | 90 Days |
| Streams | 30 Days |
| Agent Runs | 180 Days |
| Research | Permanent |
| Evaluations | Permanent |

---

# 24. Integration Points

---

## Generation Platform

```text
GenerationService
        ↓
GenerationArtifactBuilder
        ↓
ArtifactPolicyService
        ↓
GenerationArtifactWriter
```

---

## Streaming Platform

```text
Stream Events
      ↓
StreamingArtifactBuilder
      ↓
ArtifactPolicyService
      ↓
StreamingArtifactWriter
```

---

## Research Runtime

```text
Planner
 ↓
Research Artifacts
 ↓
Evaluation
```

---

# 25. Observability Dependency

The Observability Platform depends heavily on artifacts.

```text
Artifacts
      ↓
Metrics
      ↓
Tracing
      ↓
Dashboards
```

Artifacts should therefore be implemented before Observability.

---

# 26. Future Integrations

Artifacts become the foundation for:

- LangSmith Datasets
- DeepEval Datasets
- Ragas Datasets
- Regression Testing
- Failure Replay
- Agent Debugging
- Cost Analytics
- Production Observability

---

# 27. Implementation Phases

---

## Phase 1 — Artifact Foundation

Deliverables:

- Canonical Models
- Builders
- Writers
- Readers
- Policy Service

---

## Phase 2 — Generation Artifacts

Deliverables:

- User-visible generation persistence
- Validation artifacts
- Guardrail artifacts

---

## Phase 3 — Streaming Artifacts

Deliverables:

- Event persistence
- Timeline persistence
- Replay support

---

## Phase 4 — Session Artifacts

Deliverables:

- Session reconstruction
- Chat replay

---

## Phase 5 — Research Artifacts

Deliverables:

- Retrieval persistence
- Citation persistence
- Report persistence

---

## Phase 6 — Agent Artifacts

Deliverables:

- Execution graphs
- Tool history
- State persistence

---

# 28. Acceptance Criteria

- Artifacts are immutable
- Artifacts are versioned
- Persistence is policy-driven
- Internal helper calls are not permanently persisted
- Replay is possible
- Evaluation datasets can be generated
- Observability can consume artifacts
- Future runtimes can reconstruct executions from artifacts

---

# 29. Definition of Done

ResearchMind can reconstruct important AI executions using persisted artifacts.

```text
Execution
      ↓
Artifacts
      ↓
Replay
      ↓
Evaluation
      ↓
Observability
      ↓
Regression Testing
```

The Artifact Platform becomes the canonical execution history layer of ResearchMind.
