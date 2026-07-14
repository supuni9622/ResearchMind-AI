# Prompting Architecture

**Status:** Frozen

**Date:** 2026-07-14

---

# Purpose

Define the responsibilities and boundaries between:

- Context Platform
- Prompt Formatter
- Prompt Templates
- Generation Platform

This document exists to prevent mixing retrieval concerns with generation concerns.

---

# High Level Flow

```text
Retrieved Chunks
        ↓
Context Builder
        ↓
Prompt Formatter
        ↓
Formatted Context
        ↓
Prompt Template
        ↓
LLM
        ↓
Output Parser
        ↓
Final Response
```

---

# Architectural Principle

ResearchMind separates:

1. Knowledge Representation
2. LLM Instruction

These are fundamentally different concerns.

---

# Prompt Formatter

## Responsibility

Convert structured knowledge into an LLM-consumable context representation.

Input:

```python
ContextChunk[]
Citation[]
```

Output:

```text
Source: S1

Document:
Climate_Report.pdf

Pages:
15-16

Content:
Global temperatures have increased...
```

---

## Owns

- Citation formatting
- Source formatting
- Parent context formatting
- Chunk ordering representation
- Document formatting
- Research context formatting

---

## Does NOT Own

- User question
- System prompts
- LLM instructions
- Response style
- Structured outputs
- Output schemas

---

## Question Answered

> How should retrieved knowledge be represented?

---

# Prompt Templates

## Responsibility

Combine:

- System instructions
- User question
- Formatted context

into the final LLM prompt.

Input:

```python
question
formatted_context
system_prompt
```

Output:

```text
You are an expert researcher.

Use only the supplied context.

Context:
...

Question:
...
```

---

## Owns

- System instructions
- Response requirements
- Tone
- Citation requirements
- Structured output requirements
- Prompt strategies

---

## Does NOT Own

- Chunk formatting
- Citations generation
- Parent retrieval
- Context ordering

---

## Question Answered

> How should the model be instructed?

---

# Separation of Concerns

```text
Knowledge Representation
                ↓
        Prompt Formatter

LLM Instruction
                ↓
        Prompt Template
```

---

# Example

---

## Prompt Formatter Output

```text
==================================================

Source: S1

Document:
Climate_Report.pdf

Heading:
Global Warming

Pages:
15-16

Content:

Global temperatures have increased...
```

---

## Prompt Template

```text
You are an expert climate researcher.

Instructions:

- Use only supplied context.
- Cite sources.

Context:

{formatted_context}

Question:

{question}
```

---

## Final Prompt

```text
You are an expert climate researcher.

Instructions:

- Use only supplied context.
- Cite sources.

Context:

==================================================
Source: S1
...

Question:

What causes climate change?
```

---

# Ownership Boundaries

---

# Context Platform Owns

```text
Retrieval Results
Parent Expansion
Chunk Merge
Compression
Citations
Prompt Formatter
```

---

# Generation Platform Owns

```text
Prompt Templates
LLM Providers
Streaming
Output Parsers
Structured Outputs
Research Chains
```

---

# Framework Usage

---

## ResearchMind Owns

```text
Prompt Formatter
```

---

## LangChain Can Be Used For

```text
Prompt Templates
LCEL
Output Parsers
Streaming
```

---

## LangGraph Can Be Used For

Future:

```text
Planner
Research Runtime
Agents
Query Decomposition
Memory Runtime
```

---

# Future Prompt Formatting Strategies

Potential implementations:

---

## Default

Simple source formatting.

---

## NotebookLM

Rich citations.

---

## Perplexity

Answer-oriented formatting.

---

## Research

Large-context formatting.

---

## Agent

Tool-friendly context formatting.

---

# Future Prompt Template Strategies

Potential implementations:

---

## QA

Question answering.

---

## Research

Long-form research.

---

## Reviewer

Critique generated responses.

---

## Planner

Query decomposition.

---

## Summarizer

Produce concise outputs.

---

# Final Architecture

```text
Retrieved Chunks
        ↓
Context Builder
        ↓
Prompt Formatter
        ↓
Formatted Context
        ↓
Prompt Template
        ↓
LLM
        ↓
Output Parser
        ↓
Final Response
```

---

# Important Principle

Prompt Formatter is a Context concern.

Prompt Templates are a Generation concern.

These responsibilities should never be mixed.
