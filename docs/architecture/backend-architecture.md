# Backend Architecture

## Overview

The ResearchMind AI backend is designed as a modular, production-ready FastAPI application.

The architecture emphasizes:

- Scalability
- Maintainability
- Testability
- Separation of concerns
- Dependency Injection
- Strong typing

The backend acts as the orchestration layer between the frontend, AI services, databases, vector stores, memory systems, and external MCP servers.

---

# High-Level Architecture

```
                        Frontend (Next.js)
                               │
                               ▼
                        FastAPI Backend
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
      Middleware           API Routers          Lifespan
         │                     │                     │
         └──────────────┬──────┴──────────────┬──────┘
                        ▼                     ▼
                  Service Layer        Dependency Injection
                        │
        ┌───────────────┼───────────────────┐
        ▼               ▼                   ▼
   PostgreSQL        Valkey             Qdrant
```

---

# Backend Layers

The backend is organized into logical layers.

```
Client

↓

Middleware

↓

API Layer

↓

Service Layer

↓

Infrastructure Layer

↓

Databases
```

Each layer has a single responsibility.

---

# Request Lifecycle

A request flows through the backend in the following order.

```
Client

↓

CORS Middleware

↓

Request ID Middleware

↓

Request Logging Middleware

↓

Request Timing Middleware

↓

API Router

↓

Dependency Injection

↓

Service Layer

↓

Infrastructure

↓

Response
```

Middleware executes before business logic.

---

# Application Lifecycle

The application lifecycle is managed through FastAPI Lifespan.

```
Application Startup
        │
        ▼
Load Configuration
        │
        ▼
Configure Logging
        │
        ▼
Initialize PostgreSQL
        │
        ▼
Initialize Valkey
        │
        ▼
Initialize Qdrant
        │
        ▼
Application Ready
```

Shutdown performs graceful resource cleanup.

---

# API Layer

Responsibilities

- Request validation
- Response serialization
- Routing
- Dependency Injection

Business logic is intentionally excluded from routers.

---

# Service Layer

Responsibilities

- Business logic
- AI orchestration
- External integrations
- Data processing

Services communicate with infrastructure through well-defined interfaces.

---

# Infrastructure Layer

Current infrastructure components.

## PostgreSQL

Primary relational database.

Responsibilities

- Users
- Documents
- Research Sessions
- Reports
- Metadata

---

## Valkey

In-memory data store.

Planned responsibilities

- Conversation memory
- Semantic cache
- Rate limiting
- Session management
- LangGraph checkpoints

---

## Qdrant

Vector database.

Responsibilities

- Document embeddings
- Semantic search
- Similarity retrieval
- Hybrid retrieval

---

# Dependency Injection

FastAPI dependencies provide request-scoped resources.

Current dependencies include:

- Database Session

Future dependencies will include:

- Current User
- Authentication
- Authorization
- AI Clients

---

# API Contracts

Every endpoint follows a consistent response contract.

Success

```json
{
    "success": true,
    "data": {}
}
```

Error

```json
{
    "success": false,
    "error": {
        "code": "",
        "message": "",
        "details": {}
    }
}
```

---

# Error Handling

Application exceptions are handled globally.

Benefits

- Consistent responses
- Reduced duplication
- Improved frontend integration
- Centralized logging

---

# Current Technology Stack

Backend

- FastAPI
- SQLAlchemy
- Pydantic

Infrastructure

- PostgreSQL
- Valkey
- Qdrant

Development

- Docker Compose
- uv
- Python 3.12

---

# Future Expansion

The backend is designed to support:

- Authentication
- Background workers
- AI agents
- LangGraph
- RAG
- MCP integrations
- Streaming responses
- Observability
- Horizontal scaling

The current architecture intentionally establishes these extension points without introducing unnecessary complexity.