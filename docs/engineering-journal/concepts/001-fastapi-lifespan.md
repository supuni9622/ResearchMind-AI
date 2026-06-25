# FastAPI Lifespan

## Overview

FastAPI provides a lifecycle mechanism called **Lifespan** for managing resources that should exist for the lifetime of the application.

Examples:

- Database connections
- Redis / Valkey clients
- Qdrant client
- LangSmith
- Background workers

---

## Why It Exists

Applications have two important events:

- Startup
- Shutdown

Resources should be created during startup and cleaned up during shutdown.

---

## ResearchMind Usage

ResearchMind will initialize:

- PostgreSQL
- Valkey
- Qdrant

during startup.

---

## Benefits

- Proper cleanup
- Better testing
- Centralized initialization
- Predictable lifecycle

---

## Common Mistakes

- Creating clients during import
- Forgetting cleanup
- Opening duplicate connections

---

## Key Takeaways

- Lifespan manages application resources.
- Startup initializes services.
- Shutdown releases resources.