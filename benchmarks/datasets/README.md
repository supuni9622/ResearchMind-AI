# ResearchMind Benchmark Datasets

## Overview

The Benchmark Datasets provide the canonical inputs used by the
ResearchMind Engineering Benchmark Platform.

Unlike production documents, benchmark datasets are curated,
deterministic, and version-controlled. They provide a stable foundation
for measuring AI quality over time.

Every benchmark within ResearchMind should consume benchmark datasets
rather than arbitrary user documents.

---

# Purpose

Benchmark datasets enable objective comparison of AI implementations.

Examples include:

- Chunking strategies
- Embedding providers
- Retrieval strategies
- Reranking providers
- Complete AI pipelines

Using the same dataset across multiple benchmark executions ensures that
results are reproducible and comparable over time.

---

# Design Principles

Benchmark datasets should be:

- Deterministic
- Version controlled
- Reproducible
- Provider agnostic
- Independent from production infrastructure

Benchmark datasets should never depend on:

- Amazon S3
- Background workers
- Queue processing
- Runtime evaluation
- Experimentation platform

They are local engineering assets.

---

# Canonical Artifacts

Each benchmark consumes the canonical output of the previous AI
platform.

For example:

| Benchmark | Input |
|-----------|-------|
| Processing | Original document |
| Chunking | `processed_document.json` |
| Embedding | `chunks.json` |
| Retrieval | Embeddings / Vector Index |
| Pipeline | Complete benchmark dataset |

This keeps benchmarks isolated to the platform being evaluated.

---

# Current Dataset Collection

```
datasets/

    research_papers/

        paper_001/

            processed_document.json

        paper_002/

            processed_document.json

        paper_003/

            processed_document.json

        paper_004/

            processed_document.json

        paper_005/

            processed_document.json
```

The initial benchmark corpus focuses on academic research papers because
ResearchMind is primarily designed for research and knowledge-intensive
workflows.

Future benchmark collections may include:

- Books
- Technical documentation
- API documentation
- Legal contracts
- Climate reports
- Medical literature

---

# Dataset Structure

Each benchmark document lives in its own directory.

Example:

```
paper_001/

    processed_document.json
```

This intentionally leaves room for future benchmark assets without
changing the directory structure.

Possible future additions include:

```
paper_001/

    processed_document.json

    notes.md

    questions.json

    relevance.json

    citations.json
```

---

# Adding New Benchmark Datasets

When adding a new benchmark document:

1. Create a new directory using the naming convention:

```
paper_006/
```

2. Store the canonical artifact:

```
processed_document.json
```

3. Do not modify existing benchmark datasets.

If a benchmark dataset must change, create a new version rather than
editing historical benchmark inputs.

---

# Versioning Philosophy

Benchmark datasets are long-lived engineering assets.

Changing a dataset changes every benchmark result that depends on it.

For this reason:

- Existing datasets should remain immutable.
- Improvements should be introduced as new benchmark documents or future
  dataset versions.
- Benchmark reports should always record which dataset version was used.

---

# Long-Term Vision

The Benchmark Datasets will become the shared foundation for every
engineering benchmark within ResearchMind.

As the platform evolves, these datasets will allow AI engineers to make
objective, evidence-based architectural decisions by comparing multiple
implementations against the same canonical inputs.
