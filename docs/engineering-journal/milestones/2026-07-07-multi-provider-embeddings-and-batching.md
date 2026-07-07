# Multi-Provider Embeddings and Shared Batching

**Date:** 2026-07-07

---

# Objective

Extend the Embedding Platform to support multiple embedding providers while introducing a shared batching mechanism that works consistently across both local and cloud-based embedding providers.

This milestone establishes the foundation for provider benchmarking and future provider expansion without changing the public architecture of the Embedding Platform.

---

# Motivation

The initial Embedding Platform was implemented using a single provider based on Sentence Transformers.

While this provided a solid production baseline, cloud providers such as Voyage AI introduce practical constraints including:

- Request size limits
- Rate limits
- Network latency
- Cost per request

Supporting multiple providers therefore requires a common batching strategy that is independent of individual provider implementations.

---

# Implementation

## Voyage AI Provider

A new provider was introduced.

```
VoyageAIEmbeddingProvider
```

Responsibilities:

- Generate embeddings using the Voyage AI SDK
- Convert provider responses into canonical Embedding models
- Remain completely hidden behind the provider abstraction

The remainder of the Knowledge Platform remains unaware of the underlying SDK.

---

## Shared Batching Utility

A reusable batching utility was introduced.

```
EmbeddingBatcher
```

Location:

```
app/ai/knowledge/embeddings/batching.py
```

Responsibilities:

- Split collections into configurable batches
- Stream batches lazily
- Remain provider independent

The batching utility has no knowledge of embeddings, providers, SDKs or network requests.

---

## Provider Configuration

Embedding configuration now includes provider-specific batch sizes.

Current defaults:

| Provider | Batch Size |
|-----------|-----------:|
| Sentence Transformers | 64 |
| Voyage AI | 32 |
| OpenAI | 128 |

Batch sizes remain configurable through provider configuration.

---

## Sentence Transformers Refactoring

The Sentence Transformers provider was updated to use the shared batching utility.

Previous flow:

```
All chunks

↓

SentenceTransformer.encode()
```

Current flow:

```
Chunks

↓

EmbeddingBatcher

↓

SentenceTransformer.encode()

↓

EmbeddingFactory
```

This makes batching behavior explicit and consistent with cloud providers.

---

## Voyage AI Refactoring

The Voyage AI provider follows the same batching flow.

```
Chunks

↓

EmbeddingBatcher

↓

Voyage AI SDK

↓

EmbeddingFactory
```

This keeps provider implementations structurally identical while allowing each provider to interact with its own SDK.

---

# Runtime Verification

Temporary batch-level debug logging was introduced during manual verification.

Example:

```
embedding.sentence_transformers.batch

embedding.voyage.batch
```

These logs verify:

- Batch sizes
- Number of requests
- Provider execution flow

The logs may remain as debug-level instrumentation or be removed after verification.

---

# Architectural Outcome

The Embedding Platform now supports:

- Local embedding providers
- Cloud embedding providers
- Shared batching behavior
- Configurable provider batch sizes
- Provider-independent canonical embeddings

No changes were required to:

- EmbeddingService
- EmbeddingRegistry
- EmbeddingFactory
- ProcessingService

This confirms that the provider architecture successfully accommodates additional providers without modification.

---

# Lessons Learned

Introducing batching before adding multiple cloud providers proved beneficial.

The batching abstraction now becomes shared infrastructure that future providers can immediately reuse.

This avoids duplicated batching logic across providers while keeping provider implementations simple.

---

# Next Milestone

The next planned milestone is:

- OpenAI Embedding Provider

Followed by:

- Embedding Benchmark Platform

At that point the platform will support comparative benchmarking across multiple embedding providers using identical processing pipelines.
