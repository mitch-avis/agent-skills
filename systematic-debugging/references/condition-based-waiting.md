# Condition-Based Waiting

Flaky tests often guess at timing with arbitrary delays. This creates race conditions where tests
pass on fast machines but fail under load or in CI.

**Core principle:** Wait for the actual condition you care about, not a guess about how long it
takes.

## When to Use

- Tests have arbitrary delays (`setTimeout`, `sleep`, `time.sleep()`)
- Tests are flaky (pass sometimes, fail under load)
- Tests timeout when run in parallel
- Waiting for async operations to complete

**Don't use when:**

- Testing actual timing behavior (debounce, throttle intervals)
- Always document WHY if using arbitrary timeout

## Core Pattern

Python:

```python
# BAD: Guessing at timing
time.sleep(0.05)
result = get_result()
assert result is not None

# GOOD: Waiting for condition
result = wait_for(get_result, description="result available")
assert result is not None
```

Rust (sync):

```rust
// BAD: guessing at timing
std::thread::sleep(Duration::from_millis(50));
let result = get_result();
assert!(result.is_some());

// GOOD: wait for the condition
let result = wait_for(|| get_result(), "result available", Duration::from_secs(5))?;
assert!(result.is_some());
```

Rust (async with Tokio):

```rust
// BAD: arbitrary tokio::time::sleep
tokio::time::sleep(Duration::from_millis(50)).await;

// GOOD: poll until ready, with a deadline
let event = wait_for_async(|| get_event(), "TOOL_RESULT", Duration::from_secs(5)).await?;
```

## Quick Patterns

| Scenario | Pattern |
| --- | --- |
| Wait for event | `wait_for(lambda: next((e for e in events if ...), None))` |
| Wait for state | `wait_for(lambda: machine.state == "ready")` |
| Wait for count | `wait_for(lambda: len(items) >= 5 or None)` |
| Wait for file | `wait_for(lambda: path.exists() or None)` |
| Complex | `wait_for(lambda: obj.ready and obj.value > 10)` |

## Implementation

Python generic polling function:

```python
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def wait_for(
    condition: Callable[[], T | None],
    *,
    description: str = "condition",
    timeout: float = 5.0,
    interval: float = 0.01,
) -> T:
    deadline = time.monotonic() + timeout
    while True:
        result = condition()
        if result:
            return result
        if time.monotonic() >= deadline:
            raise AssertionError(f"Timed out after {timeout}s waiting for {description}")
        time.sleep(interval)
```

Rust generic polling function (sync):

```rust
use std::time::{Duration, Instant};

pub fn wait_for<T, F>(mut condition: F, description: &str, timeout: Duration) -> Result<T, String>
where
    F: FnMut() -> Option<T>,
{
    let deadline = Instant::now() + timeout;
    let interval = Duration::from_millis(10);
    loop {
        if let Some(value) = condition() {
            return Ok(value);
        }
        if Instant::now() >= deadline {
            return Err(format!("Timed out after {timeout:?} waiting for {description}"));
        }
        std::thread::sleep(interval);
    }
}
```

See `condition_based_waiting_example.py` (Python, sync + async) and
`condition_based_waiting_example.rs` (Rust, sync + Tokio async) in this directory for complete
implementations.

## Common Mistakes

- **Polling too fast:** `time.sleep(0.001)` wastes CPU. Poll every 10ms.
- **No timeout:** Loop forever if condition never met. Always include timeout with clear error.
- **Stale data:** Caching state before loop. Call getter inside loop for fresh data.

## When Arbitrary Sleep IS Correct

Python:

```python
# Tool ticks every 100ms — need 2 ticks for partial output
wait_for(lambda: tool_started_event(), description="TOOL_STARTED")
# 200ms = 2 ticks at 100ms intervals — documented
time.sleep(0.2)
```

Rust:

```rust
// Tool ticks every 100ms — need 2 ticks for partial output
wait_for(|| tool_started_event(), "TOOL_STARTED", Duration::from_secs(5))?;
// 200ms = 2 ticks at 100ms intervals — documented
std::thread::sleep(Duration::from_millis(200));
```

Requirements:

1. First wait for triggering condition
2. Based on known timing (not guessing)
3. Comment explaining WHY
