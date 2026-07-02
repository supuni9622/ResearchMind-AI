# ADR-009: Queue Abstraction for Asynchronous Document Processing

## Status

Accepted

---

## Context

ResearchMind processes uploaded documents through a multi-stage AI
pipeline.

Current processing includes:

- Document parsing
- Metadata extraction
- Statistics enrichment
- Artifact generation

Future stages will include:

- Chunk generation
- Embedding generation
- Vector indexing
- OCR
- Citation extraction
- Quality evaluation

Initially the processing pipeline was implemented synchronously in order
to validate the complete business workflow before introducing
asynchronous infrastructure.

With the synchronous pipeline now verified end-to-end, the next
evolution is asynchronous document processing.

---

## Decision

ResearchMind introduces a queue abstraction that isolates application
services from queue provider implementations.

Application services depend only on the ProcessingQueue interface.

Concrete providers implement the infrastructure details.

Examples include:

- Valkey
- Amazon SQS

Queue selection is configuration-driven.

No application code changes are required when switching providers.

---

## Architecture

```
                    ProcessingQueue
                           │
          ┌────────────────┴────────────────┐
          │                                 │
          ▼                                 ▼
     ValkeyQueue                      SQSQueue
```

Application services communicate only with the abstraction.

```
UploadService
      │
      ▼
ProcessingQueue
      │
      ▼
Queue Provider
```

The queue provider is resolved through the infrastructure factory.

---

## Rationale

This approach provides several advantages.

### Infrastructure Independence

Business logic remains independent of the queue technology.

### Cloud Portability

Development can use Valkey while production uses Amazon SQS.

Only configuration changes are required.

```
QUEUE_PROVIDER=valkey
```

↓

```
QUEUE_PROVIDER=sqs
```

### Testability

Mock queue implementations can be injected during testing.

### Scalability

Additional providers can be introduced without modifying application
services.

Examples include:

- RabbitMQ
- Azure Service Bus
- Google Pub/Sub
- NATS

---

## Why Valkey for Development

Valkey provides:

- simple local setup
- high performance
- easy debugging
- zero cloud dependency
- fast iteration

Developers can inspect and replay jobs locally.

---

## Why Amazon SQS for Production

ResearchMind already uses AWS services including:

- Amazon Cognito
- Amazon S3

Amazon SQS naturally complements this architecture by providing:

- managed infrastructure
- automatic scaling
- high durability
- visibility timeout
- dead-letter queues
- operational simplicity

---

## Alternatives Considered

### Direct Valkey Dependency

Rejected.

This couples business logic to Redis/Valkey commands.

### Direct Amazon SQS Dependency

Rejected.

This tightly couples the application to AWS.

### RabbitMQ

Not selected for the MVP.

RabbitMQ provides richer messaging capabilities but introduces
additional infrastructure management that is unnecessary for the current
requirements.

---

## Consequences

Positive:

- clean separation of concerns
- provider-based architecture
- cloud portability
- easier testing
- future extensibility

Negative:

- one additional abstraction layer
- slightly more infrastructure code

---

## Implementation Plan

```
infrastructure/
    queue/

        interfaces.py

        models.py

        exceptions.py

        factory.py

        providers/

            valkey.py

            sqs.py
```

UploadService depends only on the ProcessingQueue abstraction.

Workers consume jobs through the same abstraction.

Queue provider selection is configuration driven.

---

## Future Evolution

Future processing stages will reuse the same queue abstraction.

Examples include:

- document processing
- chunk generation
- embedding generation
- vector indexing
- OCR
- evaluation
- knowledge graph construction

The abstraction therefore becomes a reusable infrastructure component
rather than an upload-specific implementation.
