---
name: rust-async
description: >-
  Async Rust programming with Tokio. Covers runtime setup, task spawning, JoinSet,
  channels, streams, select, timeouts, cancellation, and async error handling. Use when
  writing async Rust code, designing concurrent systems, or debugging async issues.
---

# Async Rust

Production patterns for async programming with Tokio.

## Runtime Setup

Commit to one async runtime per binary. Tokio is the default choice. Never mix runtimes.

```rust
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Application code here
    Ok(())
}
```

- Use `#[tokio::main]` for the entry point
- Use `Runtime::new()` only when embedding Tokio in sync code
- Configure thread count via `#[tokio::main(flavor = "multi_thread")]`
- Use `flavor = "current_thread"` for single-threaded runtimes
- Prefer specific features over `"full"` in library crates to avoid pulling in features consumers
  may not need:

```toml
tokio = { version = "1", features = [
    "rt-multi-thread", "macros", "sync", "io-util", "net", "time"
] }
```

## Core Rules

- **Never hold `Mutex` or `RwLock` across `.await` points** — use `tokio::sync::Mutex` if you must,
  but prefer message passing
- **Never block the async executor** — no `std::thread::sleep()`, no synchronous I/O, no heavy
  computation
- **Use `tokio::spawn_blocking()`** for CPU-bound or blocking work
- **Use `tokio::fs`** instead of `std::fs` for file operations
- **Clone `Arc` before moving into spawned tasks** — the clone must happen before the `move` closure

## Task Management

### Fixed parallel operations — `tokio::join!`

```rust
let (a, b, c) = tokio::join!(fetch_a(), fetch_b(), fetch_c());
```

- Use `tokio::try_join!()` when all futures return `Result`
- All branches run concurrently; returns when all complete

### Dynamic task groups — `JoinSet`

```rust
let mut set = JoinSet::new();
for url in urls {
    set.spawn(fetch(url));
}
while let Some(result) = set.join_next().await {
    let response = result??;
    process(response);
}
```

- Use `JoinSet` when the number of tasks is determined at runtime
- Tasks are cancelled when the `JoinSet` is dropped

## Channels

| Channel     | Pattern         | When to Use                |
| ----------- | --------------- | -------------------------- |
| `mpsc`      | Many-to-one     | Work queues, fan-in        |
| `broadcast` | One-to-many     | Event bus, notifications   |
| `watch`     | Latest-value    | Config updates, state sync |
| `oneshot`   | Single response | Request-reply, futures     |

- **Always use bounded channels** for backpressure — unbounded channels can cause memory exhaustion
- Prefer `mpsc` as the default choice
- Use `watch` when receivers only need the latest value

## Select and Timeouts

```rust
tokio::select! {
    result = do_work() => handle(result),
    _ = tokio::time::sleep(Duration::from_secs(30)) => {
        return Err(anyhow!("operation timed out"));
    }
    _ = cancellation_token.cancelled() => {
        return Err(anyhow!("cancelled"));
    }
}
```

- `select!` runs the first branch that completes; cancels others
- Always include a timeout or cancellation branch for long operations
- Use `tokio::time::timeout()` for simpler one-off timeouts

## Cancellation

- Use `tokio_util::sync::CancellationToken` for structured cancellation
- Pass tokens down the call tree — check with `token.cancelled().await`
- Clean up resources in drop handlers or explicit shutdown paths
- Dropping a `JoinSet` cancels all its tasks

## Streams

```rust
use tokio_stream::StreamExt;

let mut stream = tokio_stream::iter(items);
while let Some(item) = stream.next().await {
    process(item).await;
}
```

- Use `StreamExt` combinators: `map`, `filter`, `take`, `timeout`
- Use `tokio_stream::wrappers` to convert channels to streams
- Process streams lazily — avoid collecting into memory

## Error Handling in Async

- `JoinHandle::await` returns `Result<T, JoinError>` — handle both the join error and the task's own
  error
- Use `??` to unwrap both layers: `set.join_next().await??`
- Propagate errors with `?` inside async functions as normal
- Use `anyhow::Context` to add context to async errors

## Structured Concurrency Patterns

### Fan-out / Fan-in

```rust
let mut set = JoinSet::new();
for item in work_items {
    let client = client.clone();
    set.spawn(async move { client.process(item).await });
}
let mut results = Vec::with_capacity(work_items.len());
while let Some(res) = set.join_next().await {
    results.push(res??);
}
```

### Rate-limited concurrency

```rust
let semaphore = Arc::new(Semaphore::new(10));
for item in items {
    let permit = semaphore.clone().acquire_owned().await?;
    set.spawn(async move {
        let result = process(item).await;
        drop(permit);
        result
    });
}
```

## Performance

- Profile async code with `tokio-console` or `tracing` + flamegraphs
- Watch for task starvation — long-running compute blocks the executor
- Use `spawn_blocking` for anything taking > 1ms of CPU
- Batch small async operations to reduce task overhead
- Monitor channel capacity — full channels indicate backpressure problems

## Anti-Patterns

- **No `std::sync::Mutex` across `.await`** — causes deadlocks and blocks the executor
- **No `thread::sleep()` in async** — use `tokio::time::sleep()`
- **No unbounded channels** — always set a capacity limit
- **No spawning without tracking** — use `JoinSet` to collect results and handle errors
- **No ignoring `JoinError`** — a panic in a spawned task surfaces as `JoinError`
- **No mixing runtimes** — one runtime per binary
