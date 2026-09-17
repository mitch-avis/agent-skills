# Python Resilience — Detailed Patterns

## Input Validation and Domain Conversion

Validate inputs at the boundary, then work with typed domain values internally.

```python
from enum import Enum


class OutputFormat(str, Enum):
    JSON = "json"
    CSV = "csv"


def parse_output_format(value: str) -> OutputFormat:
    try:
        return OutputFormat(value.lower())
    except ValueError as exc:
        raise ValueError(f"Unsupported format: {value}") from exc
```

- Convert strings, raw JSON, and external payloads as soon as they cross the boundary.
- Keep downstream code operating on validated types.

## Exception Hierarchies and Chaining

Use a small hierarchy per domain when callers need to distinguish failure modes.

```python
class ServiceError(Exception):
    """Base service failure."""


class ExternalApiError(ServiceError):
    """Raised when a downstream API call fails."""


def upload_file(path: str) -> str:
    try:
        return do_upload(path)
    except FileNotFoundError as exc:
        raise ServiceError(f"Upload failed: missing file at {path}") from exc
```

- Preserve original exceptions with `from exc`.
- Translate external library exceptions at the edge of your abstraction.

## Partial Failure Handling

```python
@dataclass
class BatchResult[T]:
    succeeded: dict[int, T]
    failed: dict[int, Exception]


def process_batch(items: list[Item]) -> BatchResult[ProcessedItem]:
    succeeded: dict[int, ProcessedItem] = {}
    failed: dict[int, Exception] = {}

    for index, item in enumerate(items):
        try:
            succeeded[index] = process_single_item(item)
        except Exception as exc:
            failed[index] = exc

    return BatchResult(succeeded=succeeded, failed=failed)
```

- Capture item identity, not just counts.
- Decide explicitly whether the caller needs retry hints, compensation data, or a dead-letter path.

## Context Managers and Cleanup

```python
from contextlib import AsyncExitStack


async def fetch_many(hosts: list[str]) -> list[bytes]:
    async with AsyncExitStack() as stack:
        connections = [
            await stack.enter_async_context(connect(host))
            for host in hosts
        ]
        return [await conn.fetch() for conn in connections]
```

- Prefer context managers to manual `try/finally` when lifetime maps cleanly to scope.
- Use `ExitStack` or `AsyncExitStack` for dynamically sized resource sets.
- Suppress exceptions only when the behavior is intentional and documented.

## Retry Policy Design

- Retry in one layer only.
- Centralize retry policy in a client wrapper or decorator.
- Record each attempt in logs or spans.
- Use idempotency keys when retried operations reach external payment or mutation APIs.

## Timeout Design

- Set connect, read, and overall request timeouts where the client supports them.
- Use operation-level scopes such as `asyncio.timeout()` to bound full workflows.
- Distinguish between timeout budget exhaustion and explicit caller cancellation.

## Streaming and Accumulation

When streaming output must also be retained, accumulate chunks efficiently.

```python
def accumulate(chunks: list[str]) -> str:
    return "".join(chunks)
```

Avoid repeated string concatenation inside loops.

## Observability Fields

Useful structured fields for resilience-related logs:

- `operation`
- `attempt`
- `max_attempts`
- `timeout_seconds`
- `correlation_id`
- `resource_id`
- `failure_class`
- `is_retryable`
