---
name: python-resilience
description: >-
  Fault-tolerant Python patterns covering validation, exception design, retries, timeouts,
  resource cleanup, partial failures, and observability. Use when building resilient services,
  handling external I/O, or protecting long-running workflows from transient failure.
---

# Python Resilience and Resource Management

Use this skill when the main question is how Python code fails, recovers, cleans up, or exposes the
right telemetry under stress.

## Core Principles

- Validate inputs and external data early.
- Distinguish permanent failures from transient ones.
- Keep cleanup unconditional.
- Make retry policy explicit and centralized.
- Preserve error context for debugging.
- Report enough state to understand degraded behavior without leaking secrets.

## Validation and Exception Design

Validate at boundaries before expensive work:

```python
def create_order(data: dict[str, object]) -> Order:
    if not data.get("items"):
        raise ValueError("'items' must be non-empty")
    quantity = data.get("quantity")
    if not isinstance(quantity, int) or quantity < 1:
        raise ValueError(f"'quantity' must be >= 1, got {quantity!r}")
    return build_order(data)
```

- Use `ValueError`, `TypeError`, `KeyError`, `TimeoutError`, and domain-specific exceptions where
  they fit.
- Raise messages that explain what failed and how to correct it.
- Chain exceptions with `raise DomainError(...) from exc` when translating low-level failures.
- Map domain errors to transport errors at the boundary, not deep inside business logic.

## Partial Failures

Batch and fan-out operations must retain both successes and failures.

```python
@dataclass
class BatchResult[T]:
    succeeded: dict[int, T]
    failed: dict[int, Exception]
```

- Do not abort an entire batch on the first bad item unless the workflow demands all-or-nothing
  semantics.
- Return enough indexing or identity information for callers to retry, inspect, or compensate.

## Retries and Timeouts

Use retries only for transient failures.

```python
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, max=30),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
)
async def fetch_data(url: str) -> dict[str, object]:
    ...
```

- Retry network errors, timeouts, and retryable 5xx failures.
- Do not retry validation errors, bad credentials, or other permanent 4xx-style failures.
- Bound retry count and total duration.
- Add jitter when many workers may retry together.
- Put a timeout on every external call.

For async code, prefer scoped timeouts on Python 3.11+:

```python
async with asyncio.timeout(30):
    await operation()
```

## Resource Management

Use context managers for anything that must be released reliably.

```python
class DatabasePool:
    async def __aenter__(self) -> Self:
        self.pool = await create_pool(self.dsn)
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.pool.close()
```

- Use `with` and `async with` for files, transactions, clients, and pools.
- Return `False` or `None` from `__exit__` unless intentional suppression is part of the contract.
- Use `AsyncExitStack` when the number of managed resources is dynamic.
- Prefer list accumulation plus `"".join(...)` when streaming content must also be retained.

## Observability

Structured telemetry turns resilience code from guesswork into debuggable behavior.

- Log retries with attempt number, operation name, and failure class.
- Propagate correlation IDs through request boundaries and worker hops.
- Track latency, traffic, errors, and saturation at every service boundary.
- Emit warnings for handled anomalies and errors for failures that still require attention.
- Avoid unbounded labels or secret-bearing values in logs and metrics.

## Detailed Patterns

Detailed validation, exception, cleanup, and `ExitStack` patterns live in `references/details.md`.

## Anti-Patterns

- No silent retries.
- No retrying permanent failures.
- No missing timeouts on external I/O.
- No `except Exception: pass`.
- No cleanup paths that depend on the happy path finishing first.
- No logging expected user behavior as `ERROR`.

## Related Skills

- [python](../python/SKILL.md) — core standards and toolchain
- [python-async](../python-async/SKILL.md) — async cancellation and timeout integration
- [python-configuration](../python-configuration/SKILL.md) — failing fast on invalid settings and
  secret handling
- [python-infrastructure](../python-infrastructure/SKILL.md) — workers, queues, and deployment-side
  resilience concerns
- [python-anti-patterns](../python-anti-patterns/SKILL.md) — final-pass checklist for cleanup and
  failure hazards
- [observability](../observability/SKILL.md) — tracing, logging, metrics, and alerting
- [systematic-debugging](../systematic-debugging/SKILL.md) — root-cause workflows for failures that
  are already happening
