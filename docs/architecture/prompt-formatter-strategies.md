# Prompt Formatter Strategies

**Status:** Frozen

**Last Updated:** 2026-07-14

---

# Purpose

This document defines the various prompt formatting strategies supported by ResearchMind.

Different consumers of knowledge require different context representations.

A chat assistant, research engine, and agent runtime should not receive identical context formatting.

ResearchMind therefore supports multiple formatter providers.

---

# Architectural Principle

```text
Retrieved Knowledge
            ↓
Context Platform
            ↓
Formatter Strategy
            ↓
Prompt Context
            ↓
Generation Platform
```

Prompt formatting is a Context concern.

Prompt instructions remain a Generation concern.

---

# Responsibilities

Prompt Formatters are responsible for:

- source representation
- chunk ordering
- citation formatting
- context structure
- information presentation

Prompt Formatters do NOT own:

- questions
- system prompts
- output schemas
- LLM instructions
- response styles

---

# Architecture

```text
PromptFormatterService
            ↓
PromptFormatterRegistry
            ↓
Providers
```

---

# Folder Structure

```text
context/

    formatter/

        providers/

            default.py
            notebooklm.py
            perplexity.py
            research.py
            agent.py
```

---

# Supported Strategies

---

# DEFAULT

Status:

✅ Implemented

---

# Purpose

Simple generic formatting.

Used as the baseline formatter.

---

# Structure

```text
Source
Document
Heading
Pages
Content
```

---

# Example

```text
Source: S1

Document:
climate.pdf

Content:
...
```

---

# Use Cases

- simple chat
- debugging
- evaluation
- baseline generation

---

# Future

Minimal changes expected.

---

# NOTEBOOKLM

Status:

✅ Implemented (V1)

---

# Purpose

NotebookLM-style source-centric formatting.

Emphasizes traceability and source awareness.

---

# Structure

```text
Source
Document
Heading
Pages
Parent Context
Content
```

---

# Example

```text
==================================================
SOURCE [S1]

Document:
Climate_Report.pdf

Pages:
15-16

Heading:
Global Warming

Parent Context:
...

Content:
...
==================================================
```

---

# Design Goals

- maximize source awareness
- improve citation quality
- improve grounded generation
- support source navigation

---

# Use Cases

- NotebookLM-style chat
- document Q&A
- research assistants
- source-heavy workflows

---

# Future Expansions

---

## Source Relationships

```text
S1
 ↓
Related Sources
 ↓
S2
S5
```

---

## Source Summaries

```text
Source:
Summary:
Content:
```

---

## Hierarchical Sources

```text
Document
    ↓
Section
        ↓
Chunk
```

---

## Citation Highlighting

NotebookLM-like inline citations.

---

## Source Graph

Potential future visualization.

---

---

# PERPLEXITY

Status:

✅ Implemented (V1)

---

# Purpose

Answer-oriented formatting.

Prioritizes evidence rather than raw sources.

---

# Structure

```text
Evidence
Document
Key Facts
```

---

# Example

```text
Evidence [S1]

Document:
climate.pdf

Key Evidence:

...
```

---

# Design Goals

- maximize answer quality
- reduce context noise
- improve evidence extraction

---

# Use Cases

- search assistants
- QA systems
- Perplexity-style experiences
- answer generation

---

# Future Expansions

---

## Query-Aware Formatting

```text
Question
        ↓
Relevant Evidence
```

---

## Fact Extraction

```text
Evidence
    ↓
Facts
```

---

## Evidence Ranking

```text
Most Relevant
        ↓
Least Relevant
```

---

## Evidence Grouping

```text
Topic
        ↓
Evidence
```

---

## Answer Planning

Potential future integration.

---

---

# RESEARCH

Status:

✅ Implemented (V1)

---

# Purpose

Support large-context research workflows.

Optimized for:

- multiple papers
- multiple sources
- long-form synthesis

---

# Structure

```text
TOPIC
    ↓
Sources
        ↓
Evidence
```

---

# Example

```text
TOPIC:
Climate Change

SOURCE:
S1

SOURCE:
S2
```

---

# Design Goals

- support synthesis
- cross-document reasoning
- long-context research

---

# Use Cases

- Open Deep Research
- Manus-like workflows
- literature reviews
- multi-document analysis

---

# Future Expansions

---

## Topic Clustering

```text
Embeddings
        ↓
Topic Groups
```

---

## Semantic Grouping

Group related documents.

---

## Cross Document Reasoning

```text
Paper A
Paper B
        ↓
Comparison
```

---

## Contradiction Detection

```text
Agreement
Disagreement
```

---

## Research Sessions

```text
Research Topic
        ↓
Knowledge Graph
```

---

## Hierarchical Context

```text
Research
    ↓
Topic
        ↓
Document
            ↓
Chunk
```

---

---

# AGENT

Status:

✅ Implemented (Foundation)

---

# Purpose

Provide structured context for agents.

Agents generally prefer structured observations rather than large text blocks.

---

# Structure

```text
FACTS
OBSERVATIONS
EVIDENCE
```

---

# Example

```text
FACTS

1.
2.
3.

EVIDENCE

[S1]
[S2]
```

---

# Design Goals

- support planners
- support reviewers
- support tools
- support reasoning chains

---

# Use Cases

- LangGraph runtimes
- planners
- reviewers
- summarizers
- tool-using agents

---

# Future Expansions

---

## Planner Formatter

```text
TASKS
FACTS
UNKNOWNS
```

---

## Reviewer Formatter

```text
CLAIMS
EVIDENCE
RISKS
```

---

## Researcher Formatter

```text
QUESTION
OBSERVATIONS
HYPOTHESES
```

---

## Tool Formatter

```text
FACTS
TOOL INPUTS
```

---

## Memory Formatter

```text
SESSION MEMORY
LONG TERM MEMORY
```

---

## Multi-Agent Formatting

Different agents may require different context representations.

---

# Automatic Formatter Selection

Future:

```text
Question
        ↓
Intent Detection
        ↓
Formatter Strategy
```

---

# Examples

---

## QA

```text
PERPLEXITY
```

---

## Research

```text
RESEARCH
```

---

## Notebook Chat

```text
NOTEBOOKLM
```

---

## Agents

```text
AGENT
```

---

# Future Architecture

```text
Question
        ↓
Classifier
        ↓
Formatter Strategy
        ↓
Generation
```

---

# Relationship with Prompt Templates

```text
Prompt Formatter
        ↓
Knowledge Representation

Prompt Template
        ↓
Instructions
```

These responsibilities must remain separate.

---

# Future LangChain Usage

Prompt Formatters remain:

```text
ResearchMind Owned
```

LangChain may be used later for:

- Prompt Templates
- LCEL
- Output Parsers
- Streaming

---

# Long-Term Vision

```text
Retrieved Chunks
        ↓
Context Builder
        ↓
Formatter Strategy

    DEFAULT
    NOTEBOOKLM
    PERPLEXITY
    RESEARCH
    AGENT

        ↓
Prompt Context
        ↓
Generation Platform
```

---

# Maturity Evolution

```text
NotebookLM++
        ↓
Perplexity v1
        ↓
Open Deep Research
        ↓
Manus / Glean
```

As ResearchMind evolves, formatter strategies become increasingly important for:

- context quality
- reasoning quality
- research workflows
- agent runtimes
- long-term memory
