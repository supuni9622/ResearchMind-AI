# Dependency Injection

## Overview

Dependency Injection allows FastAPI to provide required objects automatically.

ResearchMind uses Dependency Injection to provide database sessions.

---

## Without Dependency Injection

Every route would need to:

- Create a session
- Use it
- Close it

This leads to duplicated code.

---

## With Dependency Injection

```
Request

↓

Depends(get_db)

↓

Database Session

↓

Route Handler
```

FastAPI manages the session lifecycle automatically.

---

## Why yield?

```
Create Session

↓

yield

↓

Route Executes

↓

Session Closes
```

Using `yield` tells FastAPI that the resource requires cleanup after the request.

---

## Benefits

- Cleaner code
- Automatic cleanup
- Reusable dependencies
- Easier testing

---

## ResearchMind Example

Every route requiring database access will receive:

```
AsyncSession
```

through:

```
Depends(get_db)
```

without creating sessions manually.

---

## Key Takeaways

Dependency Injection separates resource creation from business logic.