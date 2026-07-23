# Research Runtime PRD
Version: 1.0
Status: Accepted
Phase: 6
Priority: Critical

---

# 1. Overview

Research Runtime is the orchestration engine of ResearchMind.

It transforms ResearchMind from an advanced RAG platform into a true Deep Research system.

The runtime coordinates:

- planning
- decomposition
- parallel research
- evidence gathering
- review
- synthesis
- human approvals
- resumable workflows

## 1.1 Product routing addendum — 2026-07-20

The established linear APIs remain the fast path and are not silently migrated
to LangGraph:

- `POST /research` remains the linear request/response experience.
- `POST /research/stream` remains the linear streaming experience.
- Chat and linear Research may suggest **Research this** for multi-step,
  evidence-backed work, but they must not start Deep Research automatically.
- An explicit user action creates a persisted Deep Research proposal and plan.
- Only explicit approval creates a durable `research_run`, dispatches the
  asynchronous LangGraph runtime, and enables runtime progress events.

Deep Research is therefore an additive product flow, not a replacement for
ordinary question answering or the existing Research APIs.

---

# 2. Goals

Build a production-grade research orchestration engine that supports:

✅ multi-step research workflows

✅ long-running sessions

✅ resumable execution

✅ parallel execution

✅ human approval

✅ streaming progress

✅ evidence-driven synthesis

✅ future agent support

---

# 3. Non Goals

Research Runtime does NOT own:

❌ generation providers

❌ retrieval providers

❌ memory storage

❌ evaluation platform

❌ artifacts infrastructure

❌ graph execution engine

---

# 4. Architectural Principles

Research Runtime owns:

```text
states
contracts
workflows
planning
evidence
sessions
artifacts
APIs
```

LangGraph owns:

```text
execution engine
checkpointing
interrupts
streaming
parallel execution
subgraphs
```

---

# 5. Runtime Architecture

```text
Research API
       ↓
Research Runtime
       ↓
LangGraph Runtime
       ↓
Generation Platform
       ↓
Artifacts
       ↓
Memory Platform
```

---

# 6. User Flows

---

# Flow 1

Question answering over uploaded documents.

```text
Question
    ↓
Memory
    ↓
Retrieval
    ↓
Generation
```

---

# Flow 2

Deep research.

```text
Chat or linear Research question
   ↓
Normal answer plus optional “Research this” suggestion
   ↓
User requests a proposal
   ↓
Persisted plan proposal
   ↓
User approval
   ↓
Durable asynchronous research run
   ↓
Planner
   ↓
Decompose
   ↓
Research
   ↓
Review
   ↓
Synthesis
   ↓
Final report and downloadable PDF
```

---

# 7. Runtime Flow

```text
Request
    ↓
Create Session
    ↓
Load Memories
    ↓
Planner
    ↓
Decomposition
    ↓
Parallel Research
    ↓
Evidence Aggregation
    ↓
Review
    ↓
Synthesis
    ↓
Artifacts
    ↓
Memory Update
```

---

# 8. Runtime Versions

---

# V1

```text
START
 ↓
memory
 ↓
planner
 ↓
decompose
 ↓
parallel research
 ↓
review
 ↓
synthesis
 ↓
END
```

---

# V2

```text
START
 ↓
memory
 ↓
planner
 ↓
interrupt
 ↓
parallel research
 ↓
review
 ↓
interrupt
 ↓
synthesis
 ↓
END
```

---

# V3

```text
START
 ↓
planner_subgraph
 ↓
research_subgraph
 ↓
review_subgraph
 ↓
synthesis
 ↓
END
```

---

# 9. Folder Structure

```text
app/

    ai/

        research/

            contracts/

            planning/
            decomposition/

            runtime/
            sessions/

            evidence/
            review/
            synthesis/

            artifacts/

            create.py
```

---

# 10. Runtime Structure

```text
runtime/

    state.py
    reducers.py

    graph.py
    service.py

    nodes/
    routing/

    checkpoints/
    interrupts/

    streaming/

    create.py
```

---

# 11. Research State

```python
from typing import TypedDict
from typing import Annotated
import operator

class ResearchState(TypedDict):

    research_id: str

    session_id: str

    thread_id: str

    user_id: str

    goal: str

    rewritten_goal: str

    complexity: str

    session_memories: list
    semantic_memories: list
    research_memories: list

    plan: dict

    sub_questions: list

    completed_questions: list

    failed_questions: list

    evidence: Annotated[
        list,
        operator.add,
    ]

    findings: Annotated[
        list,
        operator.add,
    ]

    citations: Annotated[
        list,
        operator.add,
    ]

    review: dict

    report: str

    status: str
```

---

# 12. Reducers

Reducers are mandatory.

Fields:

```text
evidence
findings
citations
runtime_events
completed_questions
failed_questions
```

---

# 13. Research Session

Research sessions represent product-level state.

LangGraph checkpoints represent execution state.

---

# Session Model

```python
class ResearchSession:

    id: UUID

    user_id: UUID

    thread_id: str

    goal: str

    status: str

    current_node: str

    progress: float

    created_at: datetime

    updated_at: datetime
```

---

# Session Status

```python
class ResearchStatus(str, Enum):

    CREATED = "created"

    PLANNING = "planning"

    WAITING_APPROVAL = "waiting_approval"

    RESEARCHING = "researching"

    REVIEWING = "reviewing"

    SYNTHESIZING = "synthesizing"

    COMPLETED = "completed"

    FAILED = "failed"

    CANCELLED = "cancelled"
```

---

# 14. Planner Platform

Responsibilities:

```text
intent detection
goal analysis
complexity scoring
execution strategy
approval policy
```

---

# Planner Output

```python
class ResearchPlan:

    complexity: str

    reasoning: str

    execution_strategy: str

    estimated_steps: int

    approval_required: bool

    sub_questions: list
```

---

# Complexity Levels

```python
SIMPLE
MODERATE
COMPLEX
```

---

# Routing

---

# SIMPLE

```text
goal
 ↓
research_single
```

---

# MODERATE

```text
goal
 ↓
decompose
 ↓
parallel
```

---

# COMPLEX

```text
goal
 ↓
decompose
 ↓
parallel
 ↓
review loops
```

---

# 15. Query Decomposition

Responsibilities:

```text
subquestions
dependencies
execution batches
```

---

# Model

```python
class SubQuestion:

    id: str

    question: str

    dependencies: list[str]

    priority: int
```

---

# Example

```text
Research PEFT methods
```

↓

```text
What is LoRA?

What is QLoRA?

What are adapters?

Benchmarks?

Recommendations?
```

---

# 16. LangGraph Nodes

---

# initialize

Responsibilities:

```text
session initialization
checkpoint setup
```

---

# memory

Responsibilities:

```text
load memories
inject memories
```

---

# planner

Responsibilities:

```text
goal planning
complexity scoring
```

---

# decompose

Responsibilities:

```text
subquestions
dependencies
```

---

# research

Responsibilities:

```text
retrieval
generation
citations
evidence
```

---

# evidence

Responsibilities:

```text
merge
dedupe
confidence
```

---

# review

Responsibilities:

```text
coverage
faithfulness
gaps
```

---

# synthesis

Responsibilities:

```text
report generation
```

---

# persistence

Responsibilities:

```text
artifacts
memory updates
```

---

# 17. LangGraph Topology

---

# V1

```text
START
 ↓
initialize
 ↓
memory
 ↓
planner
 ↓
complexity_router
```

---

# SIMPLE

```text
research
 ↓
review
 ↓
synthesis
```

---

# MODERATE

```text
decompose
 ↓
parallel research
 ↓
review
 ↓
synthesis
```

---

# COMPLEX

```text
decompose
 ↓
parallel research
 ↓
review
 ↓
retry
 ↓
review
 ↓
synthesis
```

---

# Full Graph

```text
START
 ↓
initialize
 ↓
memory
 ↓
planner
 ↓
route
 ├── simple
 └── complex
          ↓
      decompose
          ↓
      parallel
          ↓
      evidence
          ↓
      review
      ├── retry
      └── synthesis
              ↓
          persistence
              ↓
             END
```

---

# 18. Parallel Research

Use:

```python
Send()
```

Example:

```python
[
    Send(
        "research",
        {
            "question": q
        }
    )
]
```

---

# 19. Evidence Platform

Responsibilities:

```text
merge evidence
dedupe
confidence scoring
citation aggregation
```

---

# Evidence Model

```python
class Evidence:

    question: str

    findings: str

    confidence: float

    citations: list

    metadata: dict
```

---

# 20. Reviewer Platform

Responsibilities:

```text
coverage
faithfulness
contradictions
missing evidence
```

---

# Review Result

```python
class ReviewResult:

    passed: bool

    confidence: float

    missing_questions: list

    contradictions: list

    retry_required: bool
```

---

# 21. Conditional Routing

```text
review
      ↓

pass
 ↓
synthesis

retry
 ↓
research
```

---

# 22. Human Approval

V2 Feature.

Approval points:

---

# Planner Approval

```text
plan
 ↓
pause
 ↓
approve
 ↓
resume
```

---

# Final Report Approval

```text
report
 ↓
pause
 ↓
approve
 ↓
resume
```

---

# 23. Checkpointing

Production:

```text
Postgres Checkpointer
```

Never:

```text
MemorySaver
```

---

# Thread Mapping

```text
ResearchSession
        ↓
thread_id
        ↓
LangGraph Checkpoint
```

---

# Resume Flow

```text
ResearchSession
        ↓
load checkpoint
        ↓
resume graph
```

---

# 24. Streaming

Stream events:

```text
planning.started
planning.completed

decomposition.started
decomposition.completed

research.started
research.completed

review.started
review.completed

synthesis.started
synthesis.completed
```

---

# Event Model

```python
class ResearchEvent:

    type: str

    node: str

    message: str

    timestamp: datetime
```

---

# 25. Recursion Limits

Required.

```python
recursion_limit = 20
```

---

# Retry Limits

```python
max_review_loops = 3
```

---

# 26. Artifacts

Persist:

```text
research_plan.json

sub_questions.json

evidence.json

review.json

report.md

research_metrics.json
```

---

# 27. Memory Integration

---

# Before Runtime

```text
session memories

semantic memories

research memories
```

---

# After Runtime

Extract:

```text
important findings

user preferences

research summaries
```

---

# Runtime Flow

```text
Request
 ↓
Memory Search
 ↓
Research Runtime
 ↓
Artifacts
 ↓
Memory Extraction
```

---

# 28. APIs

---

# Start Research

```http
POST /research
```

---

# Stream Research

```http
POST /research/stream
```

---

# Get Research

```http
GET /research/{id}
```

---

# Resume Research

```http
POST /research/{id}/resume
```

---

# Approve Research

```http
POST /research/{id}/approve
```

---

# Cancel Research

```http
POST /research/{id}/cancel
```

---

# Research History

```http
GET /research/history
```

---

# 29. Database Tables

Create:

```text
research_sessions
research_session_events
research_versions
```

---

# 30. Milestone 1

Build:

✅ contracts

✅ state

✅ planner

✅ decomposition

✅ V1 graph

✅ checkpoints

✅ streaming

---

# Milestone 2

Build:

✅ evidence platform

✅ reviewer platform

✅ retry loops

---

# Milestone 3

Build:

✅ human approvals

✅ resume

✅ cancel

---

# Milestone 4

Build:

✅ subgraphs

✅ advanced workflows

---

# 31. Acceptance Criteria

Research Runtime is complete when:

✅ research can pause and resume

✅ workflows survive crashes

✅ research can execute in parallel

✅ reports contain citations

✅ reviewer can request retries

✅ memories are injected

✅ streaming progress exists

✅ artifacts are persisted

✅ future agents can reuse the runtime
