"""Condition-based waiting utilities for tests.

Replaces arbitrary `time.sleep()` calls with polling on the actual condition that the test cares
about. Eliminates flakiness from timing assumptions.

Pattern adapted for Python (sync and async variants). Use these helpers in pytest suites instead of
sprinkling `time.sleep(0.05)` to "give things time to settle".
"""

import asyncio
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class WaitTimeoutError(AssertionError):
    """Raised when a condition does not become truthy within the timeout."""


def wait_for[T](
    condition: Callable[[], T | None],
    *,
    description: str = "condition",
    timeout: float = 5.0,
    interval: float = 0.01,
) -> T:
    """Poll `condition` until it returns a truthy value or `timeout` elapses.

    Returns the truthy value (useful for fetching the matched item). Raises `WaitTimeoutError` with
    `description` on timeout.

    Example:
        event = wait_for(
            lambda: next((e for e in events if e.type == "TOOL_RESULT"), None),
            description="TOOL_RESULT event",
        )
    """
    deadline = time.monotonic() + timeout
    while True:
        result = condition()
        if result:
            return result
        if time.monotonic() >= deadline:
            msg = f"Timed out after {timeout}s waiting for {description}"
            raise WaitTimeoutError(msg)
        time.sleep(interval)


async def wait_for_async[T](
    condition: Callable[[], Awaitable[T | None] | T | None],
    *,
    description: str = "condition",
    timeout: float = 5.0,  # noqa: ASYNC109  # mirrors wait_for's signature for test helpers
    interval: float = 0.01,
) -> T:
    """Async version of `wait_for`. Accepts sync or async condition callables."""
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        result = condition()
        if asyncio.iscoroutine(result):
            result = await result
        if result:
            return result  # type: ignore[return-value]
        if asyncio.get_event_loop().time() >= deadline:
            msg = f"Timed out after {timeout}s waiting for {description}"
            raise WaitTimeoutError(msg)
        await asyncio.sleep(interval)


def wait_for_count[T](
    items: Callable[[], list[T]],
    count: int,
    *,
    description: str | None = None,
    timeout: float = 5.0,
    interval: float = 0.01,
) -> list[T]:
    """Wait until `items()` returns at least `count` elements."""
    desc = description or f"at least {count} items"
    return wait_for(
        lambda: items() if len(items()) >= count else None,
        description=desc,
        timeout=timeout,
        interval=interval,
    )


# --- Anti-patterns to avoid -------------------------------------------------
#
# BAD: guessing at timing time.sleep(0.05) assert get_result() is not None
#
# GOOD: wait for the actual condition result = wait_for(get_result, description="result available")
#
# Only use a fixed sleep when you are deliberately testing timing behavior (debounce, throttle,
# retry intervals) — and document why.
