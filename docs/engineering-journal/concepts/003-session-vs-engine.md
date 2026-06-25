# Session vs Engine

## Overview

Engine and Session have different responsibilities.

Engine

- Manages connections

Session

- Represents one unit of work

---

## Analogy

Airport

Engine → Airport

Session → Passenger

---

## ResearchMind

One Engine

↓

Session Factory

↓

One Session per Request

---

## Why Session Factory?

Instead of creating sessions manually, SQLAlchemy creates them consistently.

---

## Important Options

### expire_on_commit=False

Keeps loaded objects available after commit.

### autoflush=False

Prevents automatic database writes.

---

## Key Takeaways

- One Engine
- Many Sessions
- One Session per request