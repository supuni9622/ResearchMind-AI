# Connection Pooling

## Overview

Opening a new database connection is expensive.

Instead, SQLAlchemy keeps a pool of reusable connections.

---

## Without Pooling

Request

↓

Open Connection

↓

Query

↓

Close Connection

Repeated for every request.

---

## With Pooling

Pool

↓

Reuse Connection

↓

Query

↓

Return to Pool

---

## ResearchMind

ResearchMind uses SQLAlchemy's built-in connection pool.

---

## Why pool_pre_ping?

Before using a connection, SQLAlchemy checks whether it is still alive.

If not, it automatically reconnects.

---

## Benefits

- Better performance
- Lower latency
- More reliable

---

## Common Mistakes

Creating a new engine for every request.

---

## Key Takeaways

Connection pooling improves both performance and reliability.