# Research Runtime

# Conversation Flow After Memory Platform

You now have memory.

So Research no longer becomes:

```
Question
↓
Retrieve
↓
Answer
```

It becomes:

---

# Chat Flow

```
User Question
        ↓
Conversation Memory
        ↓
Session Memory
        ↓
Semantic Memory
        ↓
Query Rewriter
        ↓
Retrieval
        ↓
Generation
        ↓
Memory Update
```

---

Example:

User:

```
Explain LoRA.
```

Later:

```
compare it with qlora
```

ResearchMind should internally become:

```
compare LoRA with QLoRA
```

without user repeating context.

---

# Research Flow

Research becomes:

```
Goal
↓
Memory Search
↓
Research Session Context
↓
Planner
↓
Decomposition
↓
Evidence Gathering
↓
Reviewer
↓
Report
↓
Memory Update
```

---

This was the exact gap identified in your audit:

> Research has no multi-turn memory.

Now you fixed it. 

---

# 4. Research Runtime Architecture

I would build:

```
app/ai/runtime/research/

    contracts/
    models/

    planning/
    decomposition/

    state/

    workflows/

    nodes/

    subgraphs/

    checkpoints/

    interrupts/

    sessions/

    evidence/

    synthesis/

    review/

    artifacts/

    create.py
```

---

# 5. Research State

This is THE most important thing.

Design state first.

---

```
class ResearchState(TypedDict):

    research_id: UUID
    session_id: UUID
    user_id: UUID

    goal: str
    rewritten_goal: str

    complexity: ComplexityLevel

    memories: list[MemoryRecord]

    plan: ResearchPlan

    sub_questions: list[SubQuestion]

    completed_questions: list[str]

    evidence: Annotated[
        list[Evidence],
        operator.add,
    ]

    citations: Annotated[
        list[Citation],
        operator.add,
    ]

    findings: Annotated[
        list[Finding],
        operator.add,
    ]

    review: ReviewResult

    report: str

    status: ResearchStatus

    current_step: str
```

Reducers become mandatory because Send API will write concurrently. 

---

# 6. LangGraph Topology

V1:

```
START
 ↓
memory
 ↓
planner
 ↓
decompose
 ↓
research
 ↓
evidence
 ↓
review
 ↓
synthesis
 ↓
END
```

# V2

```
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
evidence
 ↓
review
 ↓
human approval
 ↓
synthesis
 ↓
END
```

---

# V3

```
START
 ↓
memory
 ↓
planner
 ↓
decompose
 ↓
parallel researchers
 ↓
critic
 ↓
review
 ↓
planner loop
 ↓
synthesis
 ↓
END
```

# 7. Planner Platform

Planner node:

Input:

```
Goal:
"Research PEFT methods"
```

Output:

```
{
  "complexity":"complex",

  "sub_questions":[
      "What is LoRA?",
      "What is QLoRA?",
      "What are adapters?",
      "Benchmarks?",
      "Recommendations?"
  ],

  "dependencies":[]
}
```

# 8. Query Decomposition

This is where LangGraph Send becomes powerful.

---

```
return [
    Send(
        "research_subquestion",
        {
            "question": q
        }
    )
]
```

Exactly like page 8 of your LangGraph guide. 

Flow:

```
decompose
      ↓
  q1 q2 q3 q4
      ↓
 parallel research
      ↓
 merge evidence
```

---

This is where LangGraph really shines.

# 9. Evidence Platform

Evidence becomes a first-class platform.

---

Model:

```
class Evidence:

    question: str

    findings: str

    citations: list[Citation]

    confidence: float

    sources: list[Source]

    metadata: dict
```

---

Evidence node:

```
retrieval
↓
rerank
↓
generation
↓
citations
↓
evidence
```


# 10. Reviewer Flow

Reviewer should reuse Evaluation Platform.

---

Checks:

### Coverage

```
Did we answer every subquestion?
```

---

### Contradictions

```
LoRA section says X

QLoRA section says Y
```

---

### Missing Evidence

```
No citation
```

### Confidence

```
overall_confidence
```

---

Reviewer output:

```
class Review:

    passed: bool

    missing_questions: list[str]

    contradictions: list[str]

    confidence: float
```

# 11. Conditional Loop

LangGraph excels here.

---

```
review
      ↓
if pass
      ↓
synthesis

else

planner_loop
```

---

This becomes:

```
graph.add_conditional_edges(
    "review",
    route_review,
    {
        "pass":"synthesis",
        "retry":"research"
    }
)
```

Exactly one of LangGraph's biggest strengths. 

# 12. Human Approval

Research is a PERFECT use case.

---

```
planner
↓
interrupt
↓
user edits plan
↓
resume
```

---

```
interrupt_before=["synthesis"]
```

or

```
interrupt_before=["planner"]
```

---

This gives:

```
Approve Plan
Approve Report
Resume Research
```

Exactly why LangGraph checkpoints and interrupts exist. 

# 13. Checkpoints

This is huge.

You no longer need to build your own session engine.

LangGraph already gives:

```
pause
resume
continue tomorrow
human approval
crash recovery
```

Use:

```
PostgresSaver
```

NOT:

```
MemorySaver
```

for production. 

---

# 14. Research Sessions

Your sessions become:

```
ResearchSession
        ↓
thread_id
        ↓
LangGraph Checkpoint
```

---

Mapping:

```
research_id
session_id
thread_id
```

---

This becomes:

```
config = {
    "configurable":{
        "thread_id": research_id
    }
}
```

# 15. Conversation Flow with Memories

I would redesign chat and research into this:

---

# Chat

```
Question
↓
Memory Search
↓
Query Rewrite
↓
Retrieval
↓
Generation
↓
Memory Extraction
↓
Memory Update
```

---

# Research

```
Goal
↓
Research Memory Search
↓
Planner
↓
Sub Questions
↓
Parallel Research
↓
Review
↓
Report
↓
Research Memory Update
```

---

# 16. What NOT To Build

Do NOT build:

❌ graph engine

❌ checkpoint engine

❌ state machine

❌ resume engine

❌ interrupt engine

❌ parallel engine

❌ event streaming engine

LangGraph already solved these extremely hard problems. 

# 17. Recommended Build Order

## Phase 6.1

Research State

---

## Phase 6.2

Research Sessions

---

## Phase 6.3

Planner Platform

---

## Phase 6.4

LangGraph Runtime

Simple linear graph.


## Phase 6.5

Parallel Decomposition

---

## Phase 6.6

Evidence Platform

---

## Phase 6.7

Reviewer Platform

---

## Phase 6.8

Human Approval

---

## Phase 6.9

Subgraphs

---

# Final Architecture

```
Research API
        ↓
Research Runtime
        ↓
Research Session
        ↓
LangGraph Runtime
                ↓
      ┌─────────┴─────────┐
      ↓                   ↓
Planner             Research Nodes
      ↓                   ↓
Decompose        Parallel Research
      ↓                   ↓
Reviewer ← Evidence Fusion
      ↓
Human Approval
      ↓
Synthesis
      ↓
Report
      ↓
Memory Update
```

This phase is where ResearchMind stops being "advanced RAG" and starts becoming an actual **Deep Research system** similar to Open Deep Research, Glean, and Manus. 

# ResearchMind + LangGraph Responsibility Matrix

| Component | Owner |
| --- | --- |
| ResearchState schema | ResearchMind |
| ResearchPlan model | ResearchMind |
| Evidence models | ResearchMind |
| ResearchSession | ResearchMind |
| Runtime APIs | ResearchMind |
| Artifacts | ResearchMind |
| State execution | LangGraph |
| Parallelism | LangGraph |
| Persistence | LangGraph |
| Human approval | LangGraph |
| Resume | LangGraph |
| Streaming | LangGraph |
| Graph orchestration | LangGraph |

# LangGraph Components We Should Use

Your uploaded guide is actually extremely aligned with ResearchMind.

---

# 1. State ⭐⭐⭐⭐⭐

This becomes the heart.

Page 3 emphasizes:

> Design state schema before nodes.

I fully agree.

---

# Research State

```
class ResearchState(TypedDict):

    # identity
    research_id: str
    thread_id: str
    user_id: str

    # input
    goal: str

    # memories
    session_memories: list[MemoryRecord]
    semantic_memories: list[MemoryRecord]
    research_memories: list[MemoryRecord]

    # planner
    complexity: Complexity
    plan: ResearchPlan

    # decomposition
    sub_questions: list[SubQuestion]

    # execution
    completed_questions: list[str]
    failed_questions: list[str]

    # evidence
    evidence: Annotated[
        list[Evidence],
        operator.add
    ]

    findings: Annotated[
        list[Finding],
        operator.add
    ]

    citations: Annotated[
        list[Citation],
        operator.add
    ]

    # review
    review: ReviewResult

    # synthesis
    report: str

    # runtime
    status: ResearchStatus
```

---

# 2. Reducers ⭐⭐⭐⭐⭐

This is one of the biggest things people forget.

Page 7 explicitly warns about silent overwrites. 

Because later we will have:

```
Question1 → evidence
Question2 → evidence
Question3 → evidence
```

Without reducers:

```
evidence = last_write
```

Disaster.

Use:

```
Annotated[
    list[Evidence],
    operator.add
]
```

for:

```
evidence
citations
findings
logs
tool_traces
```

---

# 3. Checkpoints ⭐⭐⭐⭐⭐

This is HUGE.

You already built:

```
ResearchSession
Memory Platform
Artifacts
```

LangGraph can directly power session persistence.

Page 9 explicitly recommends persistent checkpointers in production. 

---

I would do:

```
ResearchSession
      ↓
thread_id
      ↓
LangGraph Checkpoint
```

---

Session model:

```
ResearchSession

research_id
thread_id
status
current_node
created_at
updated_at
```

---

Then:

```
graph.invoke(
    state,
    config={
        "configurable": {
            "thread_id": session.thread_id
        }
    }
)
```

---

You instantly get:

✅ pause

✅ resume

✅ crash recovery

✅ long running research

✅ continue tomorrow

without writing anything.

---

# 4. Interrupts ⭐⭐⭐⭐⭐

Research is a PERFECT interrupt use case.

Page 11. 

---

Possible pauses:

---

### Planner Approval

```
Goal
 ↓
Plan
 ↓
PAUSE
 ↓
User edits
 ↓
Resume
```

---

### Research Approval

```
Research completed
 ↓
PAUSE
 ↓
Approve report
 ↓
Resume
```

---

### Human Evidence Review

```
Evidence confidence low
 ↓
Pause
 ↓
User adds sources
 ↓
Resume
```

---

This feature alone makes ResearchMind feel enterprise-grade.

---

# 5. Streaming ⭐⭐⭐⭐⭐

You already built streaming infrastructure.

LangGraph should plug into it.

Page 10 specifically calls out node-level progress updates. 

---

Research events:

```
Planning...
Searching papers...
Analyzing LoRA...
Reviewing findings...
Generating report...
```

---

Map:

```
for event in graph.astream():
```

↓

ResearchMind Event Platform

↓

SSE/WebSocket

---

No additional work.

---

# 6. Conditional Edges ⭐⭐⭐⭐⭐

This becomes your self-correction engine.

Page 6. 

---

```
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

```
graph.add_conditional_edges(
    "review",
    route_review,
    {
        "pass": "synthesis",
        "retry": "research"
    }
)
```

---

This is basically Deep Research behavior.

---

# 7. Parallel Send API ⭐⭐⭐⭐⭐

This is probably the MOST important feature.

Page 8. 

---

Planner:

```
Research PEFT
```

↓

```
What is LoRA?
What is QLoRA?
Adapters?
Benchmarks?
Recommendations?
```

↓

```
[
    Send("research", q1),
    Send("research", q2),
    Send("research", q3),
]
```

↓

parallel execution

↓

merge evidence

---

This is literally Open Deep Research.

---

# 8. Recursion Limits ⭐⭐⭐⭐

Page 13 warns about infinite loops. 

This becomes important because you'll eventually add:

```
planner
↓
research
↓
review
↓
planner
```

Without limits:

💸 💸 💸

---

Set:

```
recursion_limit=20
```

---

Research runtime config:

```
class RuntimeLimits:

    recursion_limit = 20
    max_retries = 3
    max_parallel_tasks = 10
```

---

# 9. Subgraphs ⭐⭐⭐⭐⭐

Page 14 is actually extremely important for ResearchMind. 

---

I would structure:

---

# Planner Graph

```
Goal
 ↓
Complexity
 ↓
Plan
```

---

# Research Graph

```
Question
 ↓
Retrieve
 ↓
Generate
 ↓
Evidence
```

---

# Review Graph

```
Coverage
 ↓
Faithfulness
 ↓
Gaps
```

---

Then:

```
Supervisor Graph

      ↓

planner_graph

      ↓

research_graph

      ↓

review_graph
```

---

This keeps things maintainable.

---

# 10. ToolNode ⭐⭐⭐

Not immediately.

But later:

```
Web Search
Arxiv
Crossref
Pubmed
Paper Search
```

can become tools.

Then:

```
ToolNode(tools)
```

---

I would delay this until MCP Platform.

---

# Recommended Final Runtime

---

# V1

```
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

```
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

```
START
 ↓
planner_subgraph
 ↓
research_subgraph
 ↓
review_subgraph
 ↓
synthesis
```

The three versions are **not competing architectures**. They are **maturity stages** of the same Research Runtime.

## At a glance

| Version | Main purpose | LangGraph capability added | Product maturity |
| --- | --- | --- | --- |
| **V1** | Automated deep-research workflow | StateGraph, nodes, edges, reducers, parallel `Send`, conditional review loop, checkpointing, streaming | Functional MVP |
| **V2** | Human-supervised research | V1 + interrupts, approval, state editing, resume | Enterprise-safe workflow |
| **V3** | Modular and extensible architecture | V2 capabilities reorganized into reusable subgraphs | Production architecture for future expansion |

---

# V1 — One complete research graph

```
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

V1 is a **single LangGraph **`StateGraph` containing the complete workflow.

It answers:

> Can ResearchMind perform an end-to-end multi-step research run automatically?

## What happens

1.  Load relevant memories. 
2.  Analyze the goal and produce a plan. 
3.  Break the goal into subquestions. 
4.  Research the subquestions concurrently. 
5.  Merge and review evidence. 
6.  Produce the final report. 

## LangGraph components used

```
State
Nodes
START / END
Edges
Conditional edges
Reducers
Send API
Checkpointing
Streaming
Recursion limit
```

The uploaded guide describes `Send` as fan-out/fan-in parallel execution, while reducers safely combine concurrent writes such as evidence from multiple research branches. 

## Example topology

```
                     ┌─ research(q1) ─┐
decompose ─ Send ────├─ research(q2) ─┤── evidence merge
                     ├─ research(q3) ─┤
                     └─ research(q4) ─┘
                                         ↓
                                       review
                                  ┌──────┴──────┐
                              sufficient    insufficient
                                  ↓               ↓
                              synthesis      research retry
```

## Advantages

-  Fastest version to implement. 
-  Proves the actual research workflow. 
-  Exercises the new Planner, Evidence, Reviewer, Memory and Session components. 
-  Easy to debug because the topology is visible in one graph. 
-  Enough to turn the current linear `/research` flow into genuine multi-step research. 

## Limitations

-  The system runs autonomously after starting. 
-  Users cannot approve or edit the plan before expensive research begins. 
-  A large graph will eventually become harder to maintain. 
-  Planner, researcher and reviewer logic are modules, but not independently compiled workflows yet. 

## V1 should still support resume

V1 should already use a persistent checkpointer:

```
research_id → LangGraph thread_id → checkpoint history
```

Therefore V1 can support crash recovery and operational resume. What it does not yet provide is an intentional **human approval pause**.

---

# V2 — Human-supervised research graph

```
START
 ↓
memory
 ↓
planner
 ↓
interrupt: plan approval
 ↓
parallel research
 ↓
review
 ↓
interrupt: report approval
 ↓
synthesis
 ↓
END
```

V2 is mostly **V1 plus human-in-the-loop control**.

It answers:

> Can a user inspect, approve, reject or modify important decisions before the workflow continues?

LangGraph interrupts pause a checkpointed graph and later resume it without rerunning completed nodes. 

## First interrupt: plan approval

After planning, the user sees something such as:

```
Research objective:
Compare major PEFT approaches.

Proposed questions:
1. How does LoRA work?
2. How does QLoRA differ?
3. How do adapter methods compare?
4. What benchmarks are available?
5. Which approach should be recommended?
```

The user can:

```
Approve
Edit questions
Remove a question
Add a question
Cancel the run
```

The graph then resumes from its checkpoint.

## Second interrupt: report or evidence approval

After review, the user may inspect:

-  evidence coverage; 
-  missing sources; 
-  contradictions; 
-  confidence; 
-  proposed report structure. 

The user can then approve synthesis, request more evidence, or cancel.

## Advantages

-  Prevents expensive research based on a poor plan. 
-  Gives the user control over scope and cost. 
-  Supports enterprise approval requirements. 
-  Allows users to inject domain knowledge. 
-  Makes cancellation and resume natural. 
-  Provides a clearer audit trail. 

## Limitations

-  More API and UI complexity. 
-  Requires explicit session statuses such as: 

```
PLANNING
AWAITING_PLAN_APPROVAL
RESEARCHING
REVIEWING
AWAITING_REPORT_APPROVAL
SYNTHESIZING
COMPLETED
CANCELLED
FAILED
```

-  Requires approval and resume endpoints. 
-  Adds timeout, abandonment and stale-interrupt handling. 
-  Not every research request needs human approval. 

## Approval should be policy-driven

V2 should not interrupt every run.

```
Simple request
→ automatic execution

Moderate request
→ optional plan preview

Complex, expensive or sensitive request
→ required approval
```

The Planner can produce:

```
class ApprovalPolicy(BaseModel):
    plan_approval_required: bool
    synthesis_approval_required: bool
    reason: str | None
```

---

# V3 — Composed subgraph architecture

```
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

V3 is mainly an **internal architecture evolution**, not necessarily a visibly different user experience.

It answers:

> Can each major research capability evolve, loop, stream and be tested independently?

The guide defines subgraphs as independently compiled graphs nested inside a parent graph, allowing each domain workflow to keep its own schema and internal execution logic. 

## Planner subgraph

```
planner_subgraph

START
 ↓
load planning memory
 ↓
detect intent
 ↓
score complexity
 ↓
analyze goal
 ↓
decompose
 ↓
validate dependencies
 ↓
optional approval interrupt
 ↓
END
```

## Research subgraph

```
research_subgraph

START
 ↓
dispatch subquestions with Send
 ↓
retrieve evidence
 ↓
build context
 ↓
generate findings
 ↓
score source confidence
 ↓
merge and deduplicate evidence
 ↓
END
```

## Reviewer subgraph

```
review_subgraph

START
 ↓
coverage check
 ↓
faithfulness check
 ↓
contradiction check
 ↓
gap analysis
 ↓
conditional decision
      ├─ pass → END
      └─ retry → research request
```

## Advantages

-  Each graph has a focused responsibility. 
-  Smaller state schemas can be used internally. 
-  Independent unit and integration tests become easier. 
-  Individual subgraphs can be versioned. 
-  The research subgraph can later support uploaded documents, web search, academic databases or MCP tools. 
-  The reviewer can evolve without making the parent graph unreadable. 
-  Different teams could own different subgraphs. 
-  Future agent workflows can reuse them. 

## Limitations

-  More interfaces and state mapping. 
-  More composition complexity. 
-  Easy to overengineer before the workflow is proven. 
-  Checkpoint and streaming boundaries need careful design. 
-  Parent and child state contracts must remain explicit. 

## Important clarification

The simplified V3 diagram omitted memory and interrupts, but they do not disappear.

The real V3 would look more like:

```
START
 ↓
runtime initialization
 ├─ load memory
 ├─ load session
 └─ establish execution policy
 ↓
planner_subgraph
     └─ optional plan interrupt
 ↓
research_subgraph
 ↓
review_subgraph
     ├─ pass
     └─ retry research_subgraph
 ↓
optional synthesis interrupt
 ↓
synthesis
 ↓
persist artifacts and memory
 ↓
END
```

V3 therefore **contains the V1 and V2 capabilities**, organized into independently compiled subgraphs.

---

# Concrete comparison

Suppose the user asks:

> Research PEFT methods and recommend the best option for fine-tuning a 7B model on limited hardware.

## V1 behavior

```
Start
→ plan automatically
→ research automatically
→ review automatically
→ return report
```

The user sees progress but does not intervene.

## V2 behavior

```
Start
→ generate plan
→ pause
→ user removes irrelevant benchmark scope
→ resume
→ research
→ review
→ pause before final synthesis
→ user approves
→ return report
```

The workflow is supervised.

## V3 behavior

The user experience may be identical to V2, but internally:

```
PlannerGraph
→ ResearchGraph
→ ReviewerGraph
→ SynthesisNode
```

Each major capability is independently maintainable and reusable.

---

# Relationship between the versions

```
V1 = prove the workflow
  ↓
V2 = add human governance
  ↓
V3 = modularize the proven workflow
```

They should not be implemented as three separate runtime products.

A better framing is:

```
Research Runtime 1.0
    └─ single graph, automatic workflow

Research Runtime 1.1
    └─ approval interrupts and resume APIs

Research Runtime 2.0
    └─ planner/research/reviewer subgraphs
```

---

# What ResearchMind should build now

Build **V1 with V3-compatible boundaries**.

That means:

-  one compiled top-level graph; 
-  separate Planner, Evidence, Reviewer and Synthesis domain services; 
-  small single-responsibility nodes; 
-  persistent checkpointing from the beginning; 
-  reducers and `Send` from the beginning; 
-  research event streaming from the beginning; 
-  approval fields and statuses in contracts, but interrupts can follow after the autonomous graph works; 
-  avoid compiling separate subgraphs until the workflows have enough internal complexity to justify them. 

## Recommended first topology

```
START
 ↓
initialize_session
 ↓
load_memory
 ↓
plan
 ↓
route_by_complexity
 ├─ simple → research_single
 └─ complex → decompose
                 ↓
          Send research_task × N
                 ↓
          aggregate_evidence
 ↓
review
 ├─ pass → synthesize
 ├─ retry → targeted_research
 └─ fail → terminate
 ↓
persist_result
 ↓
END
```

Then add V2 interrupts. After the planner, research and reviewer sections develop their own loops and policies, extract them into V3 subgraphs.

**The practical choice is therefore not V1 versus V2 versus V3. It is V1 first, V2 next, and V3 through controlled refactoring—not three parallel implementations.**

---


# Suggested Folder Structure

```
app/ai/runtime/research/

    state/
        models.py
        reducers.py

    graphs/
        supervisor.py
        planner.py
        research.py
        reviewer.py

    nodes/
        memory.py
        planner.py
        decompose.py
        research.py
        review.py
        synthesis.py

    checkpoints/
        postgres.py

    sessions/
        service.py

    interrupts/
        service.py

    streaming/
        adapters.py

    artifacts/

    create.py
```

---

# Components We Should Use NOW

| LangGraph Feature | Use Now? |
| --- | --- |
| State | ✅ |
| Nodes | ✅ |
| START/END | ✅ |
| Conditional Edges | ✅ |
| Reducers | ✅ |
| Send API | ✅ |
| Checkpoints | ✅ |
| Streaming | ✅ |
| Interrupts | ✅ |
| Recursion Limits | ✅ |
| Subgraphs | 🟡 Soon |
| ToolNode | ❌ Later |

---

This is probably the biggest transition in ResearchMind's evolution:

```
RAG Platform
        ↓
Research Runtime
        ↓
Deep Research System
```

After this phase, ResearchMind stops looking like NotebookLM++ and starts looking much closer to Open Deep Research / Manus architecture.
