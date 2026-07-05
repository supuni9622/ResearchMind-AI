# Experimentation Platform

**Status:** Planned

---

# Overview

The Experimentation Platform enables ResearchMind to evaluate alternative
AI strategies without affecting the production pipeline.

It exists to answer engineering questions rather than serve end users.

The platform executes independently using asynchronous background
workers.

Experimentation may be enabled or disabled through configuration.

---

# Goals

The Experimentation Platform exists to answer questions such as:

- Which chunking strategy performs best?
- Which embedding provider should become the default?
- Which retrieval strategy improves Recall@10?
- Does a new AI provider outperform the current one?
- Did a recent implementation improve or regress quality?

The platform continuously supports engineering decision making.

---

# Design Principles

## Independent

Experimentation never affects production behaviour.

Production users always experience only the configured pipeline.

---

## Asynchronous

Experimentation executes independently using background workers.

The production pipeline never waits for experimentation to complete.

---

## Optional

Experimentation may be disabled entirely.

This allows expensive evaluations to be performed only when required.

---

## Reproducible

Every experiment is reproducible.

The same processed document should always produce identical experiment
results when using identical configurations.

---

# Architecture

```
Production Pipeline

↓

ProcessedDocument

↓

Experiment Queue

↓

Experiment Worker

↓

Chunking Experiments

↓

Embedding Experiments

↓

Retrieval Experiments

↓

Pipeline Experiments

↓

Experiment Reports
```

The Experimentation Platform consumes canonical artifacts produced by the
Knowledge Platform.

---

# Responsibilities

The Experimentation Platform is responsible for:

- Executing alternative strategies
- Comparing implementations
- Producing recommendations
- Supporting engineering decisions

It is NOT responsible for:

- Serving production requests
- User-facing latency
- Runtime monitoring

---

# Experiment Types

## Chunking

Examples

- Fixed
- Recursive
- Markdown
- Hierarchical
- Semantic
- LLM

The same ProcessedDocument is evaluated using every configured strategy.

---

## Embedding

Examples

- Voyage AI
- OpenAI
- BGE
- Sentence Transformers

The same ChunkArtifact is evaluated using multiple providers.

---

## Retrieval

Examples

- Dense Retrieval
- Hybrid Retrieval
- Sparse Retrieval

---

## Complete Pipeline

Entire AI pipelines may be compared.

Example

Pipeline A

Recursive

↓

Voyage

↓

Qdrant

↓

GPT

versus

Pipeline B

Markdown

↓

OpenAI

↓

pgvector

↓

Claude

The platform compares complete pipeline performance.

---

# Recommendations

Experimentation reports should provide engineering recommendations.

Examples

```
Recommended Chunking Strategy

Recursive

Reason

- Better paragraph preservation
- Improved retrieval quality
- Acceptable latency
```

Future reports may recommend:

- Embedding providers
- Retrieval strategies
- Pipeline configurations

---

# Storage

Experiment reports are stored separately from production runtime reports.

```
documents/

    {owner_id}/

        {document_id}/

            experimentation/

                chunking/

                    report.json

                embedding/

                    report.json

                retrieval/

                    report.json

                pipeline/

                    report.json
```

These reports are intended for internal engineering use.

---

# Configuration

Example

```yaml
experimentation:

  enabled: true

  chunking: true

  embedding: true

  retrieval: false

  pipeline: false
```

Experimentation should typically be enabled only during:

- Platform development
- Major migrations
- New provider evaluation
- Performance investigations

---

# Consumers

Experiment reports may be consumed by:

- Engineering dashboards
- Internal administration tools
- AI platform analytics
- Provider comparison tools

---

# Relationship to Runtime Evaluation

Runtime Evaluation observes the configured production pipeline.

Experimentation evaluates alternative strategies.

These platforms are intentionally independent.

Runtime Evaluation answers:

> "How well did the production pipeline perform?"

Experimentation answers:

> "Could another strategy perform better?"

---

# Long-Term Vision

The Experimentation Platform enables ResearchMind to continuously improve
its AI pipeline through evidence rather than intuition.

Engineering decisions should be supported by measurable comparisons,
repeatable experiments, and objective reports rather than subjective
judgement.
