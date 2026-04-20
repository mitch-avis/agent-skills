---
name: python-resilience
description: >-
  Fault-tolerant Python patterns including retries with exponential backoff, timeouts, context
  managers, resource cleanup, error handling, partial failure handling, and observability. Use when
  building robust services, handling transient failures, or managing resources.
---

# Python Resilience and Resource Management

Patterns for building fault-tolerant Python applications.

## Error Handling

### Validate Early

Validate at API boundaries before expensive operations:

```python
def create_order(data: dict[str, Any]) -> Order:
    if not data.get("items"):
        raise ValueError("'items' must be non-empty")
    if data["quantity"] < 1:
        raise ValueError(
            f"'quantity' must be >= 1, got {data['quantity']}"
        )
```

- Meaningful messages: what failed, why, how to fix
- Use specific exceptions: `ValueError`, `TypeError`, `KeyError`, `RuntimeError`, `TimeoutError`
- Chain exceptions: `raise X from e` preserves debug trail

### Custom Exceptions

```python
from dataclasses import dataclass

@dataclass
class ApiError(Exception):
    status_code: int
    message: str
    retry_after: float | None = None
```

Use hierarchies: base exception per domain, specific subclasses for each failure mode.

### Partial Failures

Batch operations must not abort on first error:

```python
@dataclass
class BatchResult(Generic[K, V]):
    successes: dict[K, V]
    failures: dict[K, Exception]
```

Track successes AND failures. Report both.

## Retry Logic

Use `tenacity` for production retry logic:

```python
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type,
)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, max=30),
    retry=retry_if_exception_type(
        (ConnectionError, TimeoutError)
    ),
)
async def fetch_data(url: str) -> dict[str, Any]:
    ...
```

- Retry only transient errors: `ConnectionError`, `TimeoutError`, HTTP 5xx
- Never retry permanent failures: `ValueError`, bad credentials, HTTP 4xx
- Exponential backoff with jitter to prevent thundering herd
- Bound retries by count AND duration
- Always log retry attempts with attempt number and exception

## Timeouts

Set timeouts on every network call:

```python
result = await asyncio.wait_for(operation(), timeout=30.0)
```

- Every external call needs a timeout
- Use `asyncio.wait_for` for async, `signal.alarm` or `concurrent.futures` for sync

## Resource Management

### Context Managers

```python
class DatabasePool:
    async def __aenter__(self) -> Self:
        self.pool = await create_pool(self.dsn)
        return self

    async def __aexit__(
        self, exc_type: type | None, *args: object,
    ) -> None:
        await self.pool.close()
```

- Always use `with` / `async with` for resources
- `__exit__` executes regardless of exception
- Return `None`/`False` from `__exit__` to propagate exceptions
- Return `True` only to intentionally suppress (document it)

### ExitStack for Dynamic Resources

```python
from contextlib import AsyncExitStack

async with AsyncExitStack() as stack:
    connections = [
        await stack.enter_async_context(connect(host))
        for host in hosts
    ]
```

## Observability

### Structured Logging

Use `structlog` for machine-readable JSON logs:

```python
import structlog

logger = structlog.get_logger()
logger.info(
    "order_created",
    order_id=order.id,
    user_id=user.id,
    item_count=len(order.items),
)
```

### Log Levels

| Level   | Use For                             |
| ------- | ----------------------------------- |
| DEBUG   | Development diagnostics             |
| INFO    | Operational events, state changes   |
| WARNING | Handled anomalies, degraded service |
| ERROR   | Failures needing attention          |

Never log expected behavior (invalid password) as ERROR.

### Correlation IDs

Propagate a unique request ID through all logs and spans:

```python
from contextvars import ContextVar

correlation_id: ContextVar[str] = ContextVar("correlation_id")
```

Pass `X-Correlation-ID` header to downstream services.

### Metrics (Four Golden Signals)

Track at every service boundary:

- **Latency** — histogram of request duration
- **Traffic** — counter of requests
- **Errors** — counter of failures
- **Saturation** — gauge of resource utilization

Never use unbounded values (user IDs) as metric labels.

## Anti-Patterns

- **No silent retries** — always log attempts
- **No retrying permanent failures** — fail immediately
- **No unbounded retries** — cap by count and duration
- **No missing timeouts** — every external call needs one
- **No unclosed resources** — always use context managers
- **No `except Exception: pass`** — handle or propagate
- **No logging expected behavior as ERROR**

## Related Skills

- [python](../python/SKILL.md) — core Python style and project layout
- [python-async](../python-async/SKILL.md) — async retries, timeouts, cancellation
- [observability](../observability/SKILL.md) — log and trace failures so retries are debuggable
- [systematic-debugging](../systematic-debugging/SKILL.md) — diagnose root causes of transient
  failures
