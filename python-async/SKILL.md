---
name: python-async
description: >-
  Use before writing or changing Python code that uses async/await, asyncio, anyio, or an ASGI app
  such as FastAPI or Starlette. Covers structured concurrency, cancellation, timeouts, queues, async
  context managers, and calling blocking code safely from async code.
---

# Python Async Patterns

Use async when the workload is dominated by waiting on network, database, file, or stream I/O.

## When to Use Async

- Many concurrent network or database calls -> `asyncio`
- Long-lived streams, queues, websockets, or ASGI request handling -> `asyncio`
- CPU-bound computation -> `multiprocessing` or native extensions, not `asyncio`
- Mixed I/O and blocking code -> `asyncio.to_thread()` or an explicit worker boundary

Core rule: stay sync end-to-end or async end-to-end within a call path. Hidden blocking inside an
async function defeats the model.

## Core Rules

- Always `await` coroutines.
- Never block the event loop with `time.sleep()`, `requests`, synchronous database clients, or
  heavy CPU loops.
- Prefer `asyncio.TaskGroup` for structured concurrency on Python 3.11+.
- Put timeouts on external I/O.
- Cancel tasks you no longer need and clean up connections deterministically.

## Concurrency Patterns

### Structured Concurrency

```python
async with asyncio.TaskGroup() as task_group:
    task_a = task_group.create_task(fetch("https://a.example.com"))
    task_b = task_group.create_task(fetch("https://b.example.com"))

results = [task_a.result(), task_b.result()]
```

Use `asyncio.gather()` when you want a fixed batch result. Use `TaskGroup` when lifecycle,
automatic cancellation, and failure propagation matter more than positional return values.

### Rate Limiting

```python
sem = asyncio.Semaphore(10)


async def limited_fetch(url: str) -> str:
    async with sem:
        return await fetch(url)
```

### Producer / Consumer

```python
queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)


async def producer(items: list[str]) -> None:
    for item in items:
        await queue.put(item)


async def consumer() -> None:
    while True:
        item = await queue.get()
        try:
            await process(item)
        finally:
            queue.task_done()
```

Set `maxsize` so backpressure is explicit.

### Blocking Bridges

```python
result = await asyncio.to_thread(blocking_library_call, payload)
```

Use this as a seam, not an excuse to keep a blocking stack inside an otherwise async service.

## Timeouts and Cancellation

Prefer modern timeout scopes on Python 3.11+:

```python
try:
    async with asyncio.timeout(30):
        result = await fetch_data()
except TimeoutError:
    handle_timeout()
```

`asyncio.wait_for()` remains valid when you need to wrap a specific awaitable.

- Treat cancellation as part of the normal control flow.
- Close clients, pools, and streams in `finally` blocks or async context managers.
- Use `gather(return_exceptions=True)` only when the caller is prepared to handle per-task failure.

## Async Context and I/O Patterns

```python
class AsyncPool:
    async def __aenter__(self) -> Self:
        self.pool = await create_pool()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.pool.close()
```

- Reuse `httpx.AsyncClient`, `aiohttp.ClientSession`, and database pools instead of recreating them
  per call.
- Prefer async iterators and chunked streaming for large responses.
- Keep connection lifetime explicit and short enough to recover cleanly from cancellation.

## ASGI and Web APIs

FastAPI, Starlette, and other ASGI services need the same async discipline as any other event-loop
application.

- Keep route handlers thin and push business rules into services.
- Use async-native database and HTTP clients.
- Use lifespan context managers for shared clients and pools.
- Return validated response models instead of raw ORM rows.
- Offload long-running work to a queue boundary, not `BackgroundTasks`, when durability matters.

Detailed FastAPI and ASGI patterns live in `references/web-apis.md`.

## Testing Async Code

```bash
uv add --group dev pytest-asyncio httpx
```

```python
import pytest


@pytest.mark.asyncio
async def test_fetch_returns_data() -> None:
    result = await fetch("https://example.com")
    assert "Example" in result
```

- Use `pytest-asyncio` for coroutine tests.
- Use `httpx.AsyncClient` for ASGI app tests.
- Assert timeout, cancellation, and partial-failure behavior, not only the happy path.
- Keep async tests deterministic by controlling concurrency fan-out and external dependencies.

## Anti-Patterns

- No `time.sleep()` in async code.
- No `requests` or other blocking clients inside async request paths.
- No synchronous file or database I/O on the event loop when an async option exists.
- No fire-and-forget tasks without ownership, cancellation, or observability.
- No unbounded queues.
- No swallowing `CancelledError` unless cleanup requires it and you re-raise afterward.

## Reference Files

- `references/web-apis.md` — FastAPI, dependencies, lifespan, response models, and API testing

## Related Skills

- [python](../python/SKILL.md) — core Python standards and toolchain
- [python-web-apis](../python-web-apis/SKILL.md) — HTTP and ASGI boundary design
- [python-testing](../python-testing/SKILL.md) — testing strategy and pytest conventions
- [python-resilience](../python-resilience/SKILL.md) — retries, timeouts, and cleanup under failure
- [observability](../observability/SKILL.md) — tracing and context propagation across async flows
