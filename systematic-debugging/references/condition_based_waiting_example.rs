//! Condition-based waiting utilities for Rust tests.
//!
//! Replaces arbitrary `thread::sleep` / `tokio::time::sleep` calls with polling
//! on the actual condition the test cares about. Eliminates flakiness from
//! timing assumptions.
//!
//! Pair with the Python equivalent in `condition_based_waiting_example.py`.
//!
//! Usage in a sync test:
//!
//! ```ignore
//! let event = wait_for(
//!     || events.iter().find(|e| e.kind == EventKind::ToolResult).cloned(),
//!     "TOOL_RESULT event",
//!     Duration::from_secs(5),
//! )?;
//! ```
//!
//! Usage in a Tokio test:
//!
//! ```ignore
//! let event = wait_for_async(
//!     || async { fetch_event().await },
//!     "TOOL_RESULT event",
//!     Duration::from_secs(5),
//! )
//! .await?;
//! ```

use std::time::{Duration, Instant};
use std::{fmt, thread};

/// Returned when a condition does not become available within the timeout.
#[derive(Debug)]
pub struct WaitTimeout {
    pub description: String,
    pub elapsed: Duration,
}

impl fmt::Display for WaitTimeout {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "timed out after {:?} waiting for {}",
            self.elapsed, self.description
        )
    }
}

impl std::error::Error for WaitTimeout {}

/// Poll `condition` until it returns `Some(_)` or the timeout elapses.
///
/// Returns the inner value on success. Polls every 10 ms, which is a good
/// trade-off between responsiveness and CPU use for test code.
pub fn wait_for<T, F>(
    mut condition: F,
    description: &str,
    timeout: Duration,
) -> Result<T, WaitTimeout>
where
    F: FnMut() -> Option<T>,
{
    let start = Instant::now();
    let deadline = start + timeout;
    let interval = Duration::from_millis(10);
    loop {
        if let Some(value) = condition() {
            return Ok(value);
        }
        if Instant::now() >= deadline {
            return Err(WaitTimeout {
                description: description.to_string(),
                elapsed: start.elapsed(),
            });
        }
        thread::sleep(interval);
    }
}

/// Wait until `items()` returns at least `count` elements, then return them.
pub fn wait_for_count<T, F>(
    mut items: F,
    count: usize,
    description: &str,
    timeout: Duration,
) -> Result<Vec<T>, WaitTimeout>
where
    F: FnMut() -> Vec<T>,
{
    wait_for(
        || {
            let current = items();
            (current.len() >= count).then_some(current)
        },
        description,
        timeout,
    )
}

/// Async version of [`wait_for`] for use with Tokio (or any executor that
/// provides `tokio::time::sleep`). Requires the `tokio` dependency at the
/// caller's crate.
///
/// Accepts an `FnMut` returning a future so each poll re-creates the future.
#[cfg(feature = "tokio")]
pub async fn wait_for_async<T, F, Fut>(
    mut condition: F,
    description: &str,
    timeout: Duration,
) -> Result<T, WaitTimeout>
where
    F: FnMut() -> Fut,
    Fut: std::future::Future<Output = Option<T>>,
{
    let start = Instant::now();
    let deadline = start + timeout;
    let interval = Duration::from_millis(10);
    loop {
        if let Some(value) = condition().await {
            return Ok(value);
        }
        if Instant::now() >= deadline {
            return Err(WaitTimeout {
                description: description.to_string(),
                elapsed: start.elapsed(),
            });
        }
        tokio::time::sleep(interval).await;
    }
}

// --- Anti-patterns to avoid ------------------------------------------------
//
// BAD: guessing at timing
//     std::thread::sleep(Duration::from_millis(50));
//     assert!(get_result().is_some());
//
// GOOD: wait for the actual condition
//     let result = wait_for(get_result, "result available", Duration::from_secs(5))?;
//     assert!(result.is_some());
//
// Only use a fixed sleep when you are deliberately testing timing behaviour
// (debounce, throttle, retry intervals) - and document why.

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    #[test]
    fn returns_value_when_condition_becomes_truthy() {
        let counter = AtomicUsize::new(0);
        let result = wait_for(
            || {
                let n = counter.fetch_add(1, Ordering::SeqCst);
                (n >= 3).then_some(n)
            },
            "counter >= 3",
            Duration::from_secs(1),
        );
        assert_eq!(result.unwrap(), 3);
    }

    #[test]
    fn returns_timeout_when_condition_never_truthy() {
        let result: Result<i32, _> =
            wait_for(|| None, "impossible condition", Duration::from_millis(50));
        assert!(result.is_err());
    }
}
