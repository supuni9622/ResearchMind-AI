# SQLAlchemy Engine

## Overview

The Engine is SQLAlchemy's connection manager.

It does **not** execute business logic.

It manages:

- Connections
- Connection pool
- Transactions
- Reconnection

---

## Real-World Analogy

Restaurant

Customer → Reception → Kitchen

Engine is the reception.

---

## ResearchMind Usage

ResearchMind has one Engine shared across the application.

---

## Best Practices

- One engine per application
- Never create one per request
- Enable connection pooling

---

## Common Mistakes

- Creating multiple engines
- Closing the engine incorrectly
- Ignoring failed connections

---

## Key Takeaways

One Engine

↓

Many Sessions

↓

Many Requests