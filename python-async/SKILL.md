---
name: python-async
description: Python asyncio patterns for high-performance concurrent applications. Covers event loops, coroutines, tasks, gather, semaphores, channels, async context managers, and testing async code. Use when building async APIs, I/O-bound services, or concurrent Python systems.
---

# Python Async Patterns

Patterns for asyncio-based concurrent programming.

## When to Use Async

- Many concurrent network or database calls → asyncio
- CPU-bound computation → `multiprocessing`
- Mixed I/O + CPU → `asyncio.to_thread()` for blocking work

**Core rule:** Stay fully sync or fully async within a call path. Mixing creates hidden blocking.

## Fundamentals

```python
import asyncio

async def fetch(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.text()

async def main() -> None:
    results = await asyncio.gather(
        fetch("https://a.example.com"),
        fetch("https://b.example.com"),
    )
```

- Always `await` coroutines — forgetting returns the coroutine object without executing
- Never block the event loop with `time.sleep()`, `requests.get()`, or synchronous I/O
- Use `await asyncio.sleep()` for delays
- Use `asyncio.to_thread()` to offload blocking work

## Concurrency Patterns

### Gather (fixed parallel)

```python
a, b, c = await asyncio.gather(task_a(), task_b(), task_c())
```

### Semaphore (rate-limited)

```python
sem = asyncio.Semaphore(10)

async def limited_fetch(url: str) -> str:
    async with sem:
        return await fetch(url)

results = await asyncio.gather(
    *(limited_fetch(u) for u in urls)
)
```

### Task groups (Python 3.11+)

```python
async with asyncio.TaskGroup() as tg:
    task1 = tg.create_task(fetch("a"))
    task2 = tg.create_task(fetch("b"))
results = [task1.result(), task2.result()]
```

### Producer-consumer

```python
queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)

async def producer() -> None:
    for item in items:
        await queue.put(item)

async def consumer() -> None:
    while True:
        item = await queue.get()
        await process(item)
        queue.task_done()
```

## Async Context Managers

```python
class AsyncPool:
    async def __aenter__(self) -> Self:
        self.pool = await create_pool()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.pool.close()
```

## Async Iterators

```python
async for chunk in stream_response(url):
    process(chunk)
```

## Timeouts

```python
try:
    result = await asyncio.wait_for(slow_op(), timeout=30.0)
except asyncio.TimeoutError:
    handle_timeout()
```

## Error Handling

- Use `asyncio.gather(return_exceptions=True)` to collect all errors without aborting
- Use `TaskGroup` (3.11+) for structured concurrency with automatic cancellation on first error
- Always cancel tasks you no longer need

## Testing Async Code

```python
import pytest

@pytest.mark.asyncio
async def test_fetch_returns_data() -> None:
    result = await fetch("https://example.com")
    assert "Example" in result
```

- Use `pytest-asyncio` with `@pytest.mark.asyncio`
- Install: `uv pip install pytest-asyncio`
- Test concurrent operations with `asyncio.gather`
- Use `asyncio.wait_for` to enforce test timeouts

## Connection Pools

Use connection pools for HTTP and database operations:

```python
async with aiohttp.ClientSession() as session:
    # session reuses TCP connections automatically
    ...
```

- Batch operations reduce per-call overhead
- Always close sessions/pools in `__aexit__` or `finally`

## Anti-Patterns

- **No `time.sleep()` in async** — use `asyncio.sleep()`
- **No `requests` library in async** — use `aiohttp` or `httpx`
- **No synchronous file I/O in async** — use `aiofiles`
- **No forgetting `await`** — returns coroutine, not result
- **No unbounded queues** — always set `maxsize`
