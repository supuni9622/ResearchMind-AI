# ResearchMind — Generation Runtime Platform PRD

**Document Version:** 1.0
**Platform:** Generation Runtime Platform
**Milestone:** Phase 3.9
**Status:** Ready For Implementation
**Owner:** ResearchMind Core Platform

---

# 1. Overview

## Purpose

The Generation Platform is now feature complete.

Implemented:

- Provider Platform
- Structured Output Platform
- Validation Platform
- Guardrails Platform
- Routing Platform
- Runtime Caching Platform
- Streaming Platform
- Metrics Platform
- Artifact Platform

However, these capabilities still execute as independent services.

ResearchMind currently lacks a canonical execution lifecycle.

This milestone introduces:

```text
Generation Runtime Platform
```

which becomes the shared execution layer for:

- Research Runtime
- Planner Runtime
- Reviewer Runtime
- Agent Runtime
- MCP Runtime

---

# 2. Problem Statement

Current execution:

```text
Request
    ↓
GenerationService.generate()
```

This creates several problems.

There is no single owner for:

- execution ordering
- runtime metadata
- artifact ordering
- metrics ordering
- tracing information
- runtime context

Future runtimes would eventually duplicate orchestration logic.

Example:

```python
validate()

guardrails()

generate()

metrics()

artifacts()
```

This duplication would appear inside:

- Research Runtime
- Planner Runtime
- Reviewer Runtime
- Agent Runtime

---

# 3. Goals

---

## Primary Goals

### 1. Canonical Execution Lifecycle

Introduce one unified entrypoint:

```python
execute_generation()
```

---

### 2. Freeze Execution Ordering

Every runtime must execute generation identically.

---

### 3. Runtime Metadata Ownership

Provide a canonical execution context.

---

### 4. Future Runtime Foundation

All future runtimes should consume this platform.

---

### 5. LangGraph Compatibility

Future LangGraph agents should execute generation through this runtime.

---

# 4. Non Goals

This milestone MUST NOT:

- implement Research Runtime
- implement Agent Runtime
- implement Query Decomposition
- implement planner workflows
- implement state machines
- implement nodes
- implement edges
- implement graphs
- implement checkpoints
- implement interrupts
- implement DAG engines
- implement execution frameworks
- implement plugin systems
- implement middleware frameworks
- duplicate LangGraph capabilities

---

# 5. Existing Platforms

Already implemented:

```text
Generation Platform
Validation Platform
Guardrails Platform
Routing Platform
Runtime Caching Platform
Streaming Platform
Metrics Platform
Artifact Platform
```

This milestone only orchestrates them.

---

# 6. Final Execution Flow

---

## Canonical Ordering

```text
GenerationRequest
        ↓
Input Validation
        ↓
Input Guardrails
        ↓
Prompt Registry
        ↓
Routing
        ↓
Cache Lookup
        ↓
Provider Execution
        ↓
Structured Outputs
        ↓
Generation Guardrails
        ↓
Output Validation
        ↓
Runtime Validation
        ↓
Metrics
        ↓
Artifacts
        ↓
GenerationResult
```

This ordering becomes frozen.

No runtime may bypass this flow.

---

# 7. Runtime Responsibilities

Generation Runtime owns:

- execution ordering
- runtime metadata
- execution context
- metrics ordering
- artifact ordering
- tracing ids
- orchestration

Generation Runtime does NOT own:

- provider execution
- planning
- workflows
- agent state
- retrieval
- reasoning loops
- checkpoints

---

# 8. Runtime Ownership

Generation Runtime never decides runtime.

Caller owns runtime.

Example:

```python
GenerationRequest(
    runtime=RuntimeType.RESEARCH
)
```

---

## Future Consumers

### Research Runtime

```python
runtime=RuntimeType.RESEARCH
```

### Planner Runtime

```python
runtime=RuntimeType.PLANNER
```

### Reviewer Runtime

```python
runtime=RuntimeType.REVIEWER
```

### Agent Runtime

```python
runtime=RuntimeType.AGENT
```

### MCP Runtime

```python
runtime=RuntimeType.MCP
```

---

# 9. Generation Execution Context

Introduce:

```python
GenerationExecutionContext
```

---

## Responsibilities

```python
request_id
runtime
session_id
trace_id
start_time
provider
routing_decision
cache_decision
validation_report
guardrail_report
artifact_metadata
```

---

## Future Fields

```python
langsmith_trace_id
langgraph_run_id
```

---

# 10. Runtime State

```python
class GenerationExecutionState(BaseModel):

    context: GenerationExecutionContext

    request: GenerationRequest

    result: GenerationResult | None = None

    failed: bool = False

    exception: Exception | None = None
```

---

# 11. Public API

Expose:

```python
async def execute_generation(
    request: GenerationRequest,
) -> GenerationResult
```

This becomes the canonical generation entrypoint.

Future runtimes should avoid calling:

```python
GenerationService.generate()
```

directly.

---

# 12. Artifact Ordering

Artifacts MUST persist last.

Ordering:

```text
Validation
        ↓
Metrics
        ↓
Artifacts
```

This guarantees artifacts contain:

- validation reports
- guardrail reports
- routing decisions
- cache decisions
- token usage
- costs
- runtime metadata
- tracing metadata

---

# 13. Metrics Events

Emit canonical events.

---

## Generation Events

```text
generation.started
generation.completed
generation.failed
```

---

## Provider Events

```text
provider.started
provider.completed
provider.failed
```

---

## Validation Events

```text
validation.started
validation.completed
validation.failed
```

---

## Cache Events

```text
cache.hit
cache.miss
```

---

## Artifact Events

```text
artifact.persisted
```

---

# 14. LangSmith Integration Foundation

LangSmith is NOT the source of truth.

Artifacts remain canonical.

Future integrations:

```text
Trace Export
Dataset Export
Experiment Runs
Regression Runs
```

No implementation required in this milestone.

Only expose identifiers:

```python
langsmith_trace_id
```

---

# 15. LangGraph Compatibility

Generation Runtime must remain compatible with future LangGraph runtimes.

---

## Future Architecture

```text
Agent Runtime
        ↓
LangGraph
        ↓
Generation Runtime
        ↓
Generation Platform
```

---

## LangGraph Responsibilities

LangGraph owns:

```text
StateGraph
Nodes
Edges
Conditional Routing
Loops
Parallel Execution
Checkpointing
Interrupts
Tool Execution
Subgraphs
Supervisor Graphs
```

ResearchMind MUST NOT duplicate these capabilities.

---

## Generation Runtime Responsibilities

Generation Runtime only owns:

```text
execution ordering
metrics ordering
artifact ordering
runtime metadata
tracing context
```

---

# 16. Folder Structure

```text
runtime/

    generation/

        models.py
        enums.py
        context.py
        state.py
        orchestrator.py
        interfaces.py
        create.py
```

---

## Suggested Structure

```text
runtime/
    generation/
```

This makes it easier for future runtimes to consume.

Example:

```text
runtime/
    generation/

    research/

    planner/

    reviewer/

    agent/

    mcp/
```

---

# 17. Composition Root

Introduce:

```python
create_generation_runtime()
```

Responsibilities:

- ValidationService
- GuardrailService
- RoutingService
- CacheService
- MetricsService
- ArtifactService
- GenerationService

---

# 18. Future Runtime Consumption

---

## Research Runtime

```text
Question
        ↓
Retrieval
        ↓
Context Building
        ↓
Generation Runtime
        ↓
Answer
```

---

## Agent Runtime

```text
Agent State
        ↓
LangGraph
        ↓
Generation Runtime
        ↓
Provider Execution
```

---

# 19. Acceptance Criteria

- execution ordering is frozen
- runtime ownership is defined
- runtime metadata exists
- execution context exists
- artifact ordering exists
- metrics ordering exists
- future runtimes can reuse execution
- LangGraph duplication is avoided
- GenerationService no longer owns orchestration

---

# 20. Definition of Done

ResearchMind execution becomes:

```text
Request
        ↓
Generation Runtime
        ↓
Generation Platform
        ↓
Metrics
        ↓
Artifacts
        ↓
Result
```

Future runtime architecture becomes:

```text
Research Runtime
Planner Runtime
Reviewer Runtime
Agent Runtime
MCP Runtime
        ↓
Generation Runtime
        ↓
Generation Platform
```

Generation Runtime becomes the canonical execution layer for all AI interactions in ResearchMind.

It intentionally remains a thin orchestration layer and MUST NOT evolve into a workflow engine.

Workflow execution remains the responsibility of future LangGraph-based runtimes.
