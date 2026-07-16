# 11.13 Prompt Platform

---

# Status

🟡 In Progress

Current Completion: ~90%

---

# Purpose

The Prompt Platform provides the canonical prompt management system for ResearchMind.

Responsibilities:

- Prompt versioning
- Prompt rendering
- Prompt metadata management
- Prompt examples (few-shot)
- Token estimation
- Provider-aware prompt preparation
- LangChain prompt integration
- Future semantic example retrieval

The Prompt Platform intentionally remains independent from Retrieval, Runtime, and Agent orchestration.

---

# Architectural Principles

ResearchMind owns:

- Prompt architecture
- Prompt registry
- Prompt metadata
- Prompt lifecycle
- Prompt versions
- Prompt routing hints
- Prompt evaluation hints

LangChain is leveraged only for:

- Prompt templates
- Few-shot templates
- Message rendering
- Runnable composition

---

# Goals

The platform should support:

✅ RAG

✅ Conversational AI

✅ Deep Research

✅ Agents

✅ Planner Runtime

✅ Reviewer Runtime

✅ MCP Runtime

without major architectural changes.

---

# Folder Structure

```text
generation/prompts/

├── builder.py
├── create.py
├── interfaces.py
├── models.py
├── registry.py
├── service.py
│
├── langchain/
│   └── prompt_factory.py
│
└── templates/
```

---

# Prompt Asset Structure

```text
templates/

    research/

        v1/

            prompt.md
            metadata.yaml
            examples.json

        v2/

    chat/

        v1/
        v2/
        v3/

    summary/

        v1/
        v2/
```

---

# Prompt Components

Each prompt consists of:

## prompt.md

Contains prompt instructions.

---

## metadata.yaml

Contains:

- routing hints
- evaluation configuration
- generation defaults
- memory requirements
- runtime requirements
- future capability flags

---

## examples.json

Contains optional few-shot examples.

Examples are loaded only when:

```yaml
few_shot:
  enabled: true
```

to minimize token usage.

---

# Core Models

---

## PromptTemplate

Represents a fully loaded prompt asset.

Contains:

- template
- metadata
- variables
- examples

---

## PromptMetadata

Contains:

### Routing

```yaml
routing:
```

### Evaluation

```yaml
evaluation:
```

### Generation

```yaml
generation:
```

### Context

```yaml
context:
```

### Memory

```yaml
memory:
```

### Runtime

```yaml
runtime:
```

### Future

```yaml
future:
```

---

# Prompt Registry

The registry acts as the canonical source of prompt definitions.

Responsibilities:

- registration
- version lookup
- latest version resolution
- metadata retrieval
- diagnostics

Registry intentionally remains in-memory.

Future persistence can be added without API changes.

---

# Prompt Builder

Responsibilities:

- load prompt assets
- parse metadata
- load examples
- extract variables
- apply few-shot optimization

---

# Prompt Service

Responsibilities:

- render prompts
- validate variables
- estimate tokens
- render messages
- provide future LangGraph integration

---

# Rendering Flow

```text
Prompt Template
        ↓
Prompt Builder
        ↓
Prompt Registry
        ↓
Prompt Service
        ↓
LangChain Prompt Template
        ↓
Rendered Prompt
```

---

# Few Shot Strategy

Current:

```text
Static Examples
```

Future:

```text
Semantic Example Retrieval
```

```text
Prompt
      ↓
Example Retriever
      ↓
Top Examples
      ↓
Few Shot Prompt
```

---

# Token Estimation

Prompt rendering integrates with:

```text
Observability Platform
```

through:

```text
TokenCounter
```

Provider-specific counting:

- OpenAI → tiktoken
- Groq → tiktoken
- Claude → Anthropic SDK
- Gemini → Google SDK
- Ollama → approximation

---

# Current Prompt Types

---

## Research

### v1

Optimized for:

- normal RAG
- question answering

---

### v2

Optimized for:

- deep research
- synthesis
- planner workflows
- report generation

---

## Chat

### v1

Basic conversational RAG.

### v2

Memory-aware conversations.

### v3

Agentic assistant.

---

## Summary

### v1

Simple summarization.

### v2

Structured synthesis.

---

# Future Prompt Types

Potential future prompts:

```text
planner/
reviewer/
report/
agent/
extraction/
evaluation/
memory/
```

---

# Platform Boundaries

Prompt Platform DOES NOT own:

❌ Retrieval

❌ Query Decomposition

❌ Runtime orchestration

❌ Memory retrieval

❌ Agent execution

---

These belong to:

```text
Research Runtime
Chat Runtime
Agent Runtime
```

---

# Integration Points

Prompt Platform integrates with:

### Generation Platform

```text
Prompt → Generation
```

---

### Validation Platform

```text
Prompt → Token Validation
```

---

### Routing Platform

```text
Prompt Metadata → Provider Selection
```

---

### Observability Platform

```text
Prompt → Token Metrics
```

---

# Future Runtime Flow

```text
Query
    ↓
Retrieval
    ↓
Compression
    ↓
Prompt Platform
    ↓
Generation Platform
    ↓
Validation
    ↓
Artifacts
```

---

# Completion Status

Models                       ✅
Registry                     ✅
Builder                      ✅
Service                       ✅
Prompt Versioning            ✅
Few Shot Support             ✅
Metadata System              ✅
Token Counting               ✅

Semantic Example Retrieval   ⬜
Output Parsers               ⬜
Tests                         ⬜

Current Completion: ~90%
