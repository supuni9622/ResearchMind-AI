# ResearchMind — North Star (Beyond V2 / V3)

**Source:** product-philosophy conversation, 2026-08-10 — captured here verbatim
in spirit, condensed in form. **Independently confirmed** the same day by a
handwritten note ("ResearchMind Ultimate," image `IMG_7134`) breaking the
same philosophy into concrete AI/Human action lists — see §2, which now
carries both. Not a phase plan; a direction the phase plans should converge
toward. **Companion docs:** [`PHASE_2_3_ROADMAP.md`](PHASE_2_3_ROADMAP.md)
(the V2/V3 execution plan this document reconciles against),
[`PRODUCTION_READINESS_EVALUATION.md`](../PRODUCTION_READINESS_EVALUATION.md).

**The question this document answers:** if this is where ResearchMind is
ultimately going, how much of the current architecture already supports
getting there — and how much of what's already planned for V2/V3 needs to
change? Every architectural claim below was checked against the current
code, not assumed.

**For execution order, see [`PRIORITIZED_ROADMAP.md`](PRIORITIZED_ROADMAP.md)
(reconciled 2026-08-17)** — the value×ease-ranked build sequence, including one
disclosed deviation from this document's §8 sequencing (the Socratic
Challenger node is pulled forward on ease grounds, with an MVP
simplification noted there).

For memory implementation status and acceptance criteria, use
[`MEMORY_PLATFORM_PRIORITIZED_TASKS.md`](MEMORY_PLATFORM_PRIORITIZED_TASKS.md),
not this directional document. M0-M2 and M4-M11 are implemented, with M3
rollout and the documented M6-M10 staging/calibration gates still pending; a
personal-only M12/M13 management slice is live. M5's isolation foundation is
complete. Its
personal/project scope is the prerequisite boundary for Project-scoped memory and
complements the broader Project and typed-object model below.

---

## 1. The core philosophy, condensed

- ResearchMind is **not** `Human asks → AI researches → AI answers`, and
  **not** `Human asks → autonomous agents create knowledge`.
- It is: **AI navigates existing knowledge; human and AI reason about that
  knowledge together; the human creates and owns the new knowledge.**
- Sharper still: **AI prepares the intellectual terrain. The human does the
  intellectual creation.**
- The single highest-leverage capability this implies: **AI should know when
  to stop answering and start asking.** When evidence conflicts or an
  assumption looks shaky, the right move is often a provoking question back
  to the researcher — not a confident synthesis.
- A researcher's response to that question is not just more AI-generated
  text. It is a **first-class artifact** — a `HumanInsight` — kept distinct
  from anything AI extracted, inferred, or asked.
- **This is not ordinary HITL.** The human isn't approving a workflow the AI
  owns. The human is the reason the workflow exists.

**North Star statement:** *ResearchMind is a human-centered research
intelligence system that navigates the world's existing knowledge, builds
relevant intellectual context, preserves discoveries across exploratory
paths, and challenges researchers with questions and alternative
perspectives — so humans can think beyond what is already known and create
new knowledge.*

---

## 2. The product model — five AI roles, five human roles

| AI role | What it actually does |
|---|---|
| **Knowledge Navigator** | Searches large knowledge spaces, brings the right material into view |
| **Context Builder** | Builds enough background that the human can understand the problem deeply |
| **Knowledge Cartographer** | Connects concepts, evidence, disagreements, and research paths to each other |
| **Socratic Challenger** | Asks questions designed to expose assumptions and trigger new thinking — its best action is sometimes *not* an answer |
| **Research Memory** | Keeps discoveries, abandoned paths, human insights, and unresolved questions alive across a branching exploration, not just a linear transcript |

**Confirmed and clarified by the handwritten notes (2026-08-10, `IMG_7134`):**
the notes list *"reason on existing knowledge"* as its own AI action,
distinct from *"map the existing connections."* That's not a 6th role — it's
the connective tissue already spanning Context Builder (synthesizing
material into background) and Knowledge Cartographer (structural
connections), plus the `AI_EXTRACTION → AI_CONNECTION` steps in §3's
provenance chain. Worth naming explicitly since the source material calls it
out on its own, even though it doesn't need a new row — reasoning is *how*
Context Builder and Knowledge Cartographer do their jobs, not a separate job.

The human side previously lived only as prose here. The same notes give it
equal structure — five human roles, mirroring the AI table exactly:

| Human role | What it actually does |
|---|---|
| **Source Contributor** | Finds and brings knowledge into the system — prior papers, documents, outside expertise the corpus doesn't have on its own (the notes' *"find knowledge... manually & upload it to knowledgebase"* — this is already a real, shipped product action, not aspirational) |
| **Direction Setter** | Decides what's worth investigating; sets the research question AI navigates toward |
| **Verifier** | Checks, reviews, and confirms AI-produced material before building on it further — grounded in ownership of the outcome, not a workflow gate (see §1's *"not ordinary HITL"*) |
| **Interpreter** | Judges what evidence actually means, questions assumptions, decides whether a pattern matters |
| **Knowledge Creator** | Forms the novel hypothesis, makes the epistemic leap, creates and owns the actual new contribution |

**The same notes distill all of this into two lines** — the cleanest
restatement yet of *"AI prepares the intellectual terrain, the human does
the intellectual creation"*, arrived at independently from the original
philosophy conversation:

> AI → *Work & reason on existing knowledge*
> Human → *Generate new knowledge*

Two independent passes at writing this down landing on the same split is a
good signal the philosophy is stable, not just well-argued once.

---

## 3. First-class objects and the provenance chain

| Object | Created by | Meaning |
|---|---|---|
| `Knowledge` | AI (from sources) | What existing sources tell us |
| `Evidence` | AI extraction | What supports or challenges a specific claim |
| `HumanInsight` | Human | The researcher's interpretation or original thought |
| `ResearchQuestion` / `Hypothesis` | Human (AI-assisted) | What should be investigated next |

Every object carries **provenance that is never collapsed together**:

```
SOURCE_KNOWLEDGE -> AI_EXTRACTION -> AI_CONNECTION -> AI_QUESTION
                                                          |
                                                          v
                                            HUMAN_NOTE / HUMAN_INSIGHT
                                                          |
                                                          v
                                       HUMAN_HYPOTHESIS -> HUMAN_CONCLUSION
```

The thing this prevents: after an hour of AI-assisted research, neither the
researcher nor the system can tell which ideas came from literature, which
were the model's inference, and which were the human's actual contribution.
Losing that boundary is the single biggest risk in AI-assisted research —
this chain exists specifically to make it impossible to lose.

---

## 4. The Interactive Thinking Canvas

The canvas is not where AI writes research for the user — it's where the
**evolving state of the user's thinking** becomes visible. Chat stays the
conversation surface (the *thinking process*); the canvas becomes the
*thinking state*.

| Canvas object | Created by | Meaning |
|---|---|---|
| 🔵 Research Question | Human | Something being investigated |
| 📄 Source | AI/Human | Paper, webpage, dataset, document |
| 🟢 Evidence | AI extraction | Information directly supported by a source |
| 🟡 Claim | Source/Human | A proposition that may be supported or challenged |
| 🔴 Contradiction | AI/Human | Evidence or claims disagree |
| 🟣 Human Insight | Human | Researcher's interpretation |
| 💡 Hypothesis | Primarily human | Proposed new explanation |
| ❓ Thinking Question | AI | A question meant to provoke reasoning, not close it |
| 🔗 Connection | AI/Human | Relationship between concepts |
| ⚪ Unknown / Gap | AI/Human | Something current knowledge doesn't adequately answer |
| 🧭 Research Path | Human + AI | A direction currently being explored — including abandoned ones, kept with their reason for deprioritization |

Structurally, this is a `Research Project` at the center, with the current
three surfaces becoming **operations invoked from canvas objects** rather
than destinations:

```
Research Project
      |
      +-- Thinking Canvas   (intellectual workspace)
      +-- Dialogue          (human <-> AI reasoning, i.e. today's Chat)
      +-- Sources           (knowledge base, i.e. today's documents)
      +-- Research Paths    (exploration structure)
      +-- Evidence          (claims + provenance, i.e. today's citations)
      +-- Research Memory   (continuity across the whole project)
```

Right-clicking any canvas object (e.g. a `HumanInsight`) surfaces actions —
*Deep research this*, *Find contradictory evidence*, *Turn into hypothesis*
— which is exactly Linear Research and Deep Research today, just invoked
contextually instead of from a separate tab.

---

## 5. Architecture fit assessment

Checked against current code, not assumed. This is the load-bearing table —
it answers "how close are we" precisely, component by component.

| North Star component | Closest existing analog | Fit | Verdict |
|---|---|---|---|
| Research Project (top-level object) | `ResearchConversation` (`apps/api/app/models/research.py:13-44`) — a bare shell: `id`/`owner_id`/`title` only, its own docstring says it "holds no turns itself" | **Weak** — narrowly a conversation-thread grouping, no room for documents/canvas/paths without new tables | New tables needed. Additive — doesn't require touching the existing model. |
| Typed knowledge objects (`Knowledge`/`Evidence`/`HumanInsight`/`Hypothesis`) | Artifact Platform (`apps/api/app/ai/artifacts/`) — category-based typed+versioned storage | **Partial** — the storage/versioning *pattern* is reusable, but each category is bespoke (own model + builder + writer + reader + enum member), not a generic polymorphic base. Critically: the `research` and `agent` artifact categories are already scaffolded and **currently unused by anything** — zero risk to build on. | Extend by adding new categories following the existing pattern — genuinely additive, not a rewrite. |
| AI pauses to ask (Socratic Challenger) | LangGraph `interrupt()` pattern — 3 live sites in `multi_wave_research.py` (plan/report/web-search approval), all structurally identical | **Strong** — this is the single best-aligned piece of the whole direction. State is a permissive `TypedDict` (~38 fields); adding a new field is a one-line change. Adding a 4th pause-and-ask checkpoint replicates a well-understood, already-3x-proven pattern. | Directly reuse. Near-zero new infrastructure. |
| `HumanInsight` persistence | `MemoryRecord`/`MemoryType`/`MemoryService` (`apps/api/app/ai/memory/`) — the "obvious" place at first glance | **Weak — and a trap.** `MemoryService`, `MemoryContext`, and `format_memory_context()` all hard-branch explicitly on the 4 existing `MemoryType` members throughout. A new type needs a new backend service, a new `MemoryContext` field, and a new formatting branch — real special-casing, not a cheap enum addition. Also conceptually wrong fit: a `HumanInsight` is project-scoped with graph relations (`SUPPORTED_BY`, `INSPIRED_BY`), not a "retrieve by owner" record. | **Do not** extend `MemoryType`. Build `HumanInsight` as its own domain object (see row above — the artifact platform's unused `research` category is the natural home). |
| Evidence Graph / Knowledge Cartographer relations | `IndexType.KNOWLEDGE_GRAPH` enum member (`apps/api/app/ai/knowledge/indexing/enums.py:22`) | **None** — confirmed zero supporting code anywhere: no graph store client, no entity-extraction step, nothing beyond the bare enum literal marked "(future)" | Full build from scratch. The single biggest genuine gap in the whole direction. |
| Research Path (branching, with abandon/deprioritize state) | Deep Research's per-wave task/plan structure — already models structured, evaluable tasks within *one run* | **Partial** — the concept exists but is scoped to a single run's lifetime, not a persistent, cross-run, branching structure tied to a Project | Needs generalization + persistence beyond one run. Builds on an existing concept, doesn't invent one from nothing. |
| Provenance chain discipline | Citations (resolved to filename/page/chunk_ids), `EmbeddingExperiment.configuration_fingerprint` | **Partial** — the *discipline* of "always know where this came from" already exists in scattered pockets, but nothing unifies human-vs-AI authorship across object types today | New unified concept needed, though real cultural/technical precedent already exists to build on |

---

## 6. Does the base need to change?

**No.** Every component above is additive on top of what's already running:

- Generation Runtime, Routing, Guardrails, and the three existing surfaces
  (Chat/Linear Research/Deep Research as callable *services*, cleanly
  separated per `PRODUCT_FLOWS_AND_GAPS.md`) are untouched — they become
  operations invoked from the canvas, not surfaces that get rewritten.
- LangGraph stays the orchestration engine, extended with more state fields
  and one more `interrupt()`-style node, not replaced.
- The one explicit **anti-recommendation**: don't force `HumanInsight` into
  the Memory Platform's `MemoryType` enum. That would be the one change that
  actually touches the base (hard-branching special-case code in
  `MemoryService`/`format_memory_context()`), for a conceptually poor fit.
  Keep Memory's four types exactly as they are; build the new objects
  alongside them, not inside them.
- The two genuinely from-scratch pieces are a `Project` domain model and the
  knowledge-graph/evidence-graph substrate — both new construction, but
  neither requires modifying or migrating anything that exists today.

---

## 7. Relationship to the already-planned V2 / V3

| V2/V3 item (from `PHASE_2_3_ROADMAP.md`) | North Star relevance | Recommended change |
|---|---|---|
| V2 #3 — Project-based workspace | **This item *is* the seed of `Research Project`.** Originally scoped narrowly: project memory + document set + doc mentioning. M5 now supplies a minimal Project/membership and memory-isolation foundation. | **Scope expansion, not replacement.** Extend the Project schema with room for typed sub-objects and research paths, then pass its server-authorized context into the completed M5 memory boundary. |
| V2 #6 — Graph RAG setup | **Directly the substrate for Knowledge Cartographer / Evidence Graph relations** (`SUPPORTED_BY`, `RELATED_TO`, `CONTRADICTS`, `INSPIRED_BY`, `GENERATED`). | **Reframe, don't change scope.** Same engineering effort as before, but now justified by a concrete consumer instead of "better retrieval" in the abstract. Sequence it alongside #3, not independently. |
| V2 #5 — Interruption capability, traceability, cost visibility | The `interrupt()` mechanism this item hardens is **literally the foundation of the Socratic-pause mechanism.** | No scope change. Just don't let it get deprioritized as "just approval gates" — it's the load-bearing primitive for the whole human-AI dialogue loop. |
| V2 #2 — User-profile memory | Superficially adjacent to `HumanInsight`, but **a different concept** — personal/global preferences vs. per-project interpretations. Per §5/§6 above, don't merge them. | Prompt-content injection, M4 coordinated budgeting, and the M5 isolation foundation are complete. Roll out M3 safely, then continue with M6-M16; do not let USER memory absorb `HumanInsight` responsibilities. |
| Part 1 — Evaluation Platform | Unaffected structurally. A future evaluation dimension ("did the Socratic question actually provoke better thinking? was AI/human provenance kept clean?") follows naturally once these objects exist, but isn't a v1 requirement. | No change now. |
| V3 — Vision | Minor relevance uptick — a canvas with diagrams/images in evidence benefits from vision support more than a chat-only product would. | No urgency change, but worth remembering when Vision is eventually scoped. |
| V3 — Voice, NeMo Guardrails, OCR, worker-evaluator | Orthogonal — none of these are blocked by or blocking the North Star. | No change. (Voice arguably drops slightly in priority: the North Star is a fundamentally visual/written thinking experience, not voice-first.) |

---

## 8. What this adds that isn't in the plan yet

Three genuinely new items, not currently anywhere in V2/V3:

| New item | What it is | Builds on |
|---|---|---|
| Typed research-object domain model | `Knowledge`/`Evidence`/`HumanInsight`/`ResearchQuestion`/`Hypothesis` as real persisted objects with relations and the provenance chain from §3 | The artifact platform's already-scaffolded, currently-unused `research`/`agent` categories — natural home, zero blast radius |
| Socratic Challenger node | A new LangGraph node that can conclude "ask, don't answer" and pause with a provoking question, using a new prompt template version | The existing `interrupt()` pattern, proven 3x already in the live graph |
| Interactive Thinking Canvas (frontend) | The visual surface from §4 | Everything above — sequence it **last**, since it's a view over data that needs to exist first, and it's the most speculative/expensive piece to build without that data already flowing |

**Recommended sequencing:** Part 1 (Evaluation Platform) first, since it's
cheap, foundational, and de-risks everything after it → Project schema
(V2 #3, expanded) → typed research-object domain model → Socratic Challenger
node → Graph RAG (V2 #6, reframed) → Canvas UI. This keeps the North Star
additions folded into V2's existing project-workspace and Graph RAG line
items rather than bolted on as a separate, competing track — and defers the
single largest genuinely-new build (the canvas) until the domain model and
Socratic mechanism underneath it already exist to visualize.
