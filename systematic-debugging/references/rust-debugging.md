# Rust Debugging Toolkit

Rust-specific tools and patterns for systematic debugging. Use alongside the four-phase methodology
in the main skill — these are the *instruments* you reach for during Phase 1 (investigation) and
Phase 2 (pattern analysis).

## Quick Reference

| Symptom                                    | First tool to reach for                                       |
| ------------------------------------------ | ------------------------------------------------------------- |
| `panicked at …`                            | `RUST_BACKTRACE=1 cargo test -- --nocapture`                  |
| `unreachable!()` / `unwrap()` failure      | Backtrace + replace with `Result` propagation                 |
| Wrong value, no panic                      | `dbg!(value)` macro                                           |
| Test passes alone, fails in suite          | `cargo test -- --test-threads=1` then `find-polluter.sh`      |
| Intermittent / heisenbug                   | `cargo test -- --test-threads=1` and rerun in a loop          |
| "Works on my machine"                      | `cargo test --release` (different optimisations)              |
| Suspected UB / use-after-free              | Miri: `cargo +nightly miri test`                              |
| Suspected data race                        | ThreadSanitizer: `RUSTFLAGS=-Zsanitizer=thread cargo test`    |
| Suspected leak / OOB                       | AddressSanitizer: `RUSTFLAGS=-Zsanitizer=address cargo test`  |
| Async hang                                 | `tokio-console` + `#[tokio::main(flavor = "current_thread")]` |
| Slow test / hot path                       | `cargo flamegraph` or `samply`                                |
| Regression between commits                 | `cargo bisect-rustc` (toolchain) or `git bisect` (code)       |
| Unclear which feature flag is on           | `cargo tree -e features`                                      |
| Unexpected dependency version              | `cargo tree -i <crate>` (inverted)                            |

## 1. Backtraces and Panics

Always run failing tests with backtraces enabled:

```bash
RUST_BACKTRACE=1 cargo test failing_test_name -- --nocapture
RUST_BACKTRACE=full cargo test failing_test_name -- --nocapture   # full frames
```

`--nocapture` is essential — without it, `println!` / `eprintln!` from the test are swallowed.

For ad-hoc instrumentation that must work even when `RUST_BACKTRACE` is unset:

```rust
use std::backtrace::Backtrace;

eprintln!("about to do scary thing: {}", Backtrace::force_capture());
```

`force_capture()` ignores the env var; `Backtrace::capture()` honours it.

### Convert panics into errors during investigation

A panic deep in a library tells you *what* but rarely *why*. Wrap the call site to attach context:

```rust
use anyhow::Context;

let parsed = serde_json::from_str::<Config>(&raw)
    .with_context(|| format!("parsing config from {path:?} (len={})", raw.len()))?;
```

Now the error chain (`{:#}` or `{:?}`) shows the trigger, not just the failed assertion.

## 2. The `dbg!` Macro

Faster than `println!` because it prints the file, line, expression, and pretty value:

```rust
let user = dbg!(load_user(id));
//                       ^ prints to stderr, returns the value unchanged
```

**Caveats:**

- `dbg!` consumes its argument (or borrows if you pass `&value`). Use `dbg!(&x)` for `Copy` values
  too if you want to keep the original variable name in the trace.
- Always remove `dbg!` calls before committing — clippy will fail CI on them
  (`#![deny(clippy::dbg_macro)]`).

## 3. Test Isolation

Cargo runs tests in parallel by default. This is the source of most "passes locally, fails in CI"
flakes.

```bash
# Run serially to find ordering / shared-state bugs
cargo test -- --test-threads=1

# Run a single test repeatedly to catch intermittent failures
for i in {1..50}; do cargo test my_flaky_test -- --nocapture || break; done

# Run only one test, with output, no parallelism
cargo test my_test -- --nocapture --test-threads=1
```

If a test only fails when other tests run first, it has a hidden dependency on global state. Common
culprits: env vars, `cwd`, temp files, `lazy_static!` / `OnceLock` initialisation, ports.

Use `find-polluter.sh` in this directory to bisect across `tests/*.rs` integration files:

```bash
./find-polluter.sh '/tmp/leftover-state' 'cargo test --test' 'tests/*.rs'
```

## 4. Miri — Catching Undefined Behaviour

Miri is an interpreter for Rust's MIR that detects UB the optimiser would otherwise hide:
out-of-bounds reads, use-after-free, invalid `unsafe` casts, data races on `&mut`, uninitialised
memory.

```bash
rustup +nightly component add miri
cargo +nightly miri test
cargo +nightly miri test specific_test_name
```

When to reach for Miri:

- You have any `unsafe` block.
- A test passes in debug but fails in release (classic UB symptom — optimiser assumes UB doesn't
  happen).
- Behaviour differs across platforms or pointer widths.

Miri is slow (often 50–100× the wall-clock time of native execution). Run it on the *minimal*
reproduction, not the whole suite.

## 5. Sanitizers (nightly)

When Miri is too slow or doesn't cover the case (FFI, raw syscalls, multi-threaded UB):

```bash
# Address sanitizer - heap corruption, leaks, OOB
RUSTFLAGS=-Zsanitizer=address cargo +nightly test --target x86_64-unknown-linux-gnu

# Thread sanitizer - data races
RUSTFLAGS=-Zsanitizer=thread cargo +nightly test --target x86_64-unknown-linux-gnu

# Memory sanitizer - reads of uninitialised memory
RUSTFLAGS=-Zsanitizer=memory cargo +nightly test --target x86_64-unknown-linux-gnu
```

The explicit `--target` is required because `std` itself must be rebuilt with the sanitizer.

## 6. Async Debugging (Tokio)

Async hangs and deadlocks are a category of their own. The debugging order:

1. **Pin the runtime to one thread** — eliminates scheduling non-determinism while you investigate:

   ```rust
   #[tokio::main(flavor = "current_thread")]
   async fn main() { /* ... */ }

   #[tokio::test(flavor = "current_thread")]
   async fn my_test() { /* ... */ }
   ```

2. **Add timeouts everywhere** — replace `.await` on suspect futures with
   `tokio::time::timeout(Duration::from_secs(5), fut).await??`. A timeout error tells you which
   future is stuck.

3. **Use `tokio-console`** to see live task state, blocked tasks, and resource handles:

   ```toml
   [dependencies]
   console-subscriber = "0.4"
   ```

   ```rust
   console_subscriber::init();
   ```

   Then run `tokio-console` in another terminal.

4. **Beware `block_on` inside async** — calling `Runtime::block_on` from an async context will
   deadlock instantly. The compiler doesn't catch it; only running does.

## 7. Logging with `tracing`

For anything beyond a one-shot `dbg!`, instrument with `tracing`:

```rust
use tracing::{debug, error, info, instrument, warn};

#[instrument(skip(client), fields(user_id = %req.user_id))]
async fn handle_request(client: &Client, req: Request) -> Result<Response> {
    debug!(?req, "received request");
    let user = client.fetch_user(req.user_id).await?;
    info!(name = %user.name, "loaded user");
    Ok(Response::ok(user))
}
```

`#[instrument]` automatically captures function arguments as span fields and emits enter/exit
events. Toggle verbosity at runtime:

```bash
RUST_LOG=mycrate=debug,tower_http=info cargo test -- --nocapture
```

## 8. `cargo bisect-rustc`

When the bug appeared after a Rust toolchain upgrade rather than a code change:

```bash
cargo install cargo-bisect-rustc
cargo bisect-rustc --start 1.80.0 --end 1.85.0 --script ./reproduce.sh
```

Bisects across nightly releases until it finds the regressing commit in the compiler itself. Useful
for filing upstream bugs.

## 9. Compile-Time Investigation

Some bugs are easier to understand by inspecting what the compiler produces:

```bash
# Expand all macros (great for derive / proc-macro debugging)
cargo install cargo-expand
cargo expand --test my_test

# Look at MIR or LLVM IR for the optimiser
cargo rustc --release -- --emit=mir
cargo rustc --release -- --emit=llvm-ir

# Check feature resolution
cargo tree -e features
cargo tree -i serde   # who pulls in serde?
```

## 10. Profiling Hot Paths

When the bug is "it's too slow" rather than "it's wrong":

```bash
# Flamegraph (Linux: needs perf)
cargo install flamegraph
cargo flamegraph --test my_benchmark

# samply - cross-platform sampling profiler
cargo install samply
samply record cargo test --release my_benchmark
```

Pair with `cargo bench` (or [criterion.rs](https://github.com/bheisler/criterion.rs)) for
statistically-sound before/after comparisons during a fix.

## Anti-Patterns

- **Adding `.unwrap()` to silence a compiler error** — that error was usually telling you about a
  real failure mode. Propagate with `?` or handle the case.
- **Sprinkling `eprintln!` then forgetting to remove it** — gate behind `cfg!(debug_assertions)` or
  use `tracing` so production builds stay quiet.
- **Disabling a flaky test** — the test is doing its job; the *code* is flaky. Use the test
  isolation tools above to find why.
- **`Box<dyn Error>` everywhere during debugging** — switch to `anyhow::Result` while investigating
  so you get free backtraces and context chains; tighten back to typed errors once the bug is
  understood.
- **Reaching for `unsafe` to "fix" a borrow-check error** — almost always a sign the design is
  wrong. Step back and rethink ownership before reaching for `unsafe` / raw pointers.
