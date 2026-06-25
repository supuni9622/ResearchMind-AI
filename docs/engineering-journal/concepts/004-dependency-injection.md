# Dependency Injection

## Overview

FastAPI automatically provides dependencies to route handlers.

---

## Why Use It?

Instead of writing:

Create database

↓

Use database

↓

Close database

FastAPI does it automatically.

---

## ResearchMind

Database sessions

Configuration

Authentication

Current user

All will use dependency injection.

---

## Why yield?

yield allows FastAPI to clean up resources automatically after the request finishes.

---

## Benefits

- Cleaner code
- Automatic cleanup
- Easier testing
- Reusable dependencies

---

## Key Takeaways

Depends()

↓

yield

↓

Automatic cleanup