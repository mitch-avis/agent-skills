# Python Web APIs — Detailed Patterns

## App Layout

Keep application wiring separate from domain logic.

```text
src/myapp/
├── api/
│   ├── dependencies.py
│   ├── errors.py
│   ├── middleware.py
│   └── routes/
├── services/
├── repositories/
├── schemas/
└── settings.py
```

## Dependency Injection

Use dependency functions to construct services from settings, repositories, and shared clients.

```python
def get_user_service(request: Request) -> UserService:
    """Build the user service from shared resources created at startup."""
    return UserService(
        repository=request.app.state.user_repository,
        notifier=request.app.state.notifier,
    )
```

Override these dependencies in tests rather than mutating globals.

## Exception Handlers

Map domain exceptions to HTTP responses once.

```python
@app.exception_handler(UserNotFoundError)
async def user_not_found_handler(_: Request, exc: UserNotFoundError) -> JSONResponse:
    """Map a missing user to a 404 response."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})
```

## Pagination and Filtering

- Parse pagination and filtering inputs at the transport edge.
- Convert them into typed query objects before passing them to services.
- Keep default limits explicit and capped.

## Streaming

- Stream large exports instead of buffering them entirely in memory.
- Track cleanup and timeout behavior explicitly.
- Keep observability around time-to-first-byte and completion failures.

## Test Patterns

```python
from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient

if TYPE_CHECKING:
    from fastapi import FastAPI


@pytest.mark.asyncio
async def test_get_user_missing_id_returns_404(app: FastAPI) -> None:
    # Arrange
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Act
        response = await client.get("/users/missing")

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
```

## Background Work Boundaries

- Use background tasks only when losing the work on process restart is acceptable.
- Use queues for retries, durability, or cross-service workflows.
