---
name: python-web-apis
description: >-
  Builds Python web APIs with FastAPI and other ASGI frameworks using typed request models,
  response contracts, dependency injection, lifespan resources, auth, error mapping, and API
  tests. Use when creating or refactoring HTTP APIs, handlers, middleware, or service boundaries
  in Python.
---

# Python Web APIs

Use this skill for HTTP and ASGI service design in Python. Keep transport concerns thin, type the
boundary, and push business rules into testable services.

## Service Structure

- Route or handler layer: parse requests, call services, map domain failures to HTTP responses.
- Service layer: business rules and orchestration.
- Repository or client layer: database and remote I/O.
- Shared app layer: settings, startup resources, middleware, and dependency wiring.

## Core Rules

- Use Pydantic models for request validation and response contracts.
- Keep route handlers small and explicit.
- Use FastAPI dependency injection or equivalent framework seams for services and settings.
- Reuse shared clients and pools via lifespan-managed resources.
- Return DTOs or response models, not raw ORM entities.
- Treat authorization, validation, and error translation as boundary concerns.

## FastAPI Baseline

```python
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = await service.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)
```

## Lifespan and Shared Resources

Use lifespan context managers for shared clients, pools, and caches.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    try:
        yield
    finally:
        await app.state.http_client.aclose()
```

## Error and Auth Boundaries

- Raise framework HTTP exceptions for expected client-facing failures.
- Use exception handlers to map repeated domain failures consistently.
- Keep authentication and authorization dependencies explicit.
- Log failures with request and correlation context, but do not leak internal traces in responses.

## Background and Long-Running Work

- Use in-process background tasks only for short, non-critical follow-up work.
- Hand durable or retryable work off to a queue or worker boundary.
- Return job IDs when clients need asynchronous status.

## Testing

- Test handlers with `httpx.AsyncClient` or the framework test client.
- Override dependencies with fakes.
- Assert response payload shape, not only status codes.
- Cover validation failures, auth failures, and boundary error mapping.

## Detailed Patterns

Detailed app-layout, dependency override, exception handler, streaming, and pagination patterns live
in `references/details.md`.

## Anti-Patterns

- No business logic embedded directly in handlers.
- No raw ORM models returned from endpoints.
- No per-request recreation of heavy shared clients.
- No blocking I/O inside async handlers.
- No silent conversion of domain failures into generic 500 responses.

## Related Skills

- [python](../python/SKILL.md) — core Python defaults and architecture
- [python-async](../python-async/SKILL.md) — event-loop, cancellation, and async runtime concerns
- [python-type-safety](../python-type-safety/SKILL.md) — request and response typing discipline
- [python-configuration](../python-configuration/SKILL.md) — settings injection and env-driven
  behavior
- [python-testing](../python-testing/SKILL.md) — pytest patterns for API tests
