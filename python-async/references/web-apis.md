# Python Async Web APIs

## FastAPI Service Structure

Keep API handlers thin and typed.

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

- Put request parsing and HTTP-specific error mapping in the route layer.
- Put business rules in service objects or pure functions.
- Use `response_model` or return annotations to keep contracts explicit.
- Do not return raw ORM models directly.

## Dependencies and Lifespan

Use FastAPI dependency injection for scoped services and `asynccontextmanager` for shared startup
resources.

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


app = FastAPI(lifespan=lifespan)
```

- Reuse shared HTTP clients and connection pools.
- Prefer dependency functions over global module state.
- Inject interfaces or services, not low-level request objects, into business logic.

## Validation and Error Handling

- Use Pydantic v2 models at the HTTP boundary.
- Raise `HTTPException` for expected client-facing failures.
- Use exception handlers for repeated translation of domain exceptions to HTTP responses.
- Keep internal exception types distinct from API response models.

## Background Work

Use `BackgroundTasks` only for quick, non-critical follow-up work in the same process. For durable,
retryable, or long-running work, hand off to a proper queue or worker boundary.

## Testing ASGI Apps

```python
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_get_user_returns_404(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/users/missing")

    assert response.status_code == 404
```

- Override dependencies to inject fakes.
- Assert both response status and payload shape.
- Cover validation failures, permission failures, and timeout behavior.
