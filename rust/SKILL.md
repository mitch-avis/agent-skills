---
name: rust
description: >-
  Use before writing, editing, or reviewing any Rust code (.rs files, Cargo.toml), including small
  changes in an existing codebase. Sets the house defaults for ownership and lifetimes, error
  handling, traits and generics, API design, clippy, documentation, and performance, then routes
  async and testing work to rust-async and rust-testing.
---

# Rust Development

Consolidated guide for writing idiomatic, safe, and performant Rust. Tailored for edition 2024
projects with strict linting, strict formatting, and TDD discipline.

## Standards

- **Toolchain:** nightly, pinned by `rust-toolchain.toml`; run every cargo command as
  `cargo +nightly ...`
- **Formatter:** `rustfmt` (`cargo +nightly fmt --all`; `--check` in CI)
- **Linter:** `cargo +nightly clippy --workspace --all-features --all-targets -- -D warnings` — all
  warnings are errors
- **Tests:** `cargo +nightly nextest run --workspace --all-features --all-targets`, plus
  `cargo +nightly test --doc --workspace --all-features` because nextest skips doctests
- **Line length:** 100 characters (`max_width = 100`)
- **Testing:** TDD for new features and modules — failing tests first, then implementation; small
  targeted fixes are exempt but keep the suite green
- **Coverage target:** 100% wherever achievable
- **Edition:** 2024

## Toolchain & Project Setup

Select the `nightly` channel with `rust-toolchain.toml` at the project or workspace root; date-pin
it (`nightly-YYYY-MM-DD`) only while a nightly regression blocks the build. Use
a workspace layout for multi-crate applications and services; standalone libraries can remain a
single crate when there is no real need for workspace indirection. Always commit `Cargo.lock` for
binaries and workspaces; standalone libraries may omit it when downstream version-range testing is
preferred.

See [references/project-config.md](references/project-config.md) for complete `rust-toolchain.toml`,
workspace `Cargo.toml`, `rustfmt.toml`, `clippy.toml`, and profile configuration.

### Default Crate Settings

```toml
[package]
edition = "2024"

[lints]
workspace = true
```

### rustfmt Essentials

```toml
edition                    = "2024"
group_imports              = "StdExternalCrate"
imports_granularity        = "Crate"
max_width                  = 100
use_small_heuristics       = "Max"
wrap_comments              = true
format_code_in_doc_comments = true
```

Never override rustfmt with `#[rustfmt::skip]` except in macro-generated code or alignment tables.
Every skip requires a comment explaining why.

### Workspace Lints

Declare all lint configuration in the workspace `Cargo.toml` using `[workspace.lints]` and inherit
with `lints.workspace = true` per crate. Never scatter `#![warn(...)]` / `#![deny(...)]` inner
attributes across `lib.rs` / `main.rs`.

Key settings: Clippy `all`, `pedantic`, `nursery`, and `cargo` at `deny`; restriction lints
`unwrap_used`, `expect_used`, `panic`, `as_conversions`, `allow_attributes`,
`allow_attributes_without_reason`, `undocumented_unsafe_blocks`, and `wildcard_imports` at `deny`;
`unsafe_code = "forbid"`; `missing_docs = "deny"`. The few warn-level compiler lints fail under the
`-D warnings` gate.

## Lint Governance

Suppress a lint only at the narrowest site, with `#[expect(..., reason = "...")]` instead of
`#[allow]`: the compiler warns when the exception is no longer needed, and the reason is mandatory.
Enforce this with `allow_attributes = "deny"` and `allow_attributes_without_reason = "deny"`. No
crate-level or blanket suppressions.

```rust
#[expect(
    clippy::struct_excessive_bools,
    reason = "mirrors the on-disk flag layout one field per bit"
)]
pub struct Flags {
    pub compressed: bool,
    pub encrypted: bool,
    pub signed: bool,
    pub archived: bool,
}
```

`#[expect]` must name a lint that would fire at that site. If the lint is not enabled or never
triggers, `unfulfilled_lint_expectations` warns, and `-D warnings` fails the build.

## Module & File Structure

Prefer `module.rs` over `module/mod.rs` for leaf modules. Use `module/mod.rs` only when the module
has child submodules.

```text
src/
├── lib.rs          # re-exports public API; minimal logic
├── error.rs        # crate-wide Error and Result types
├── config.rs       # leaf module: config.rs, not config/mod.rs
├── client/
│   ├── mod.rs      # justified: has submodules
│   ├── auth.rs
│   └── retry.rs
└── models/
    ├── mod.rs
    └── user.rs
```

`lib.rs` should contain only `pub use` re-exports and module declarations. Keep logic in submodules.

### Visibility Discipline

Default every item to the most restrictive visibility. Work outward only when forced:

| Visibility | When to use |
| --- | --- |
| (private) | Default — everything starts here |
| `pub(crate)` | Needed by another module in the same crate |
| `pub(super)` | Needed only by the parent module |
| `pub` | Part of the crate's public API |

`unreachable_pub = "warn"` flags any `pub` item not reachable from the crate root.

Use `#[non_exhaustive]` on all public enums and structs that may grow. It prevents downstream
`match` exhaustion failures and signals intent clearly.

## Imports

- No glob imports anywhere — `wildcard_imports = "deny"`.
- Sanctioned exceptions: `use super::*` inside `#[cfg(test)] mod tests` and generated code.
- Flatten redundant path prefixes into a single `use` tree.
- Let rustfmt own all import ordering and grouping.

```rust
// Three groups separated by blank lines
use std::collections::{BTreeMap, HashMap};
use std::fmt;

use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;

use crate::error::{Error, Result};
use crate::models::User;
```

### Prelude Pattern

For crates that define a prelude, name it explicitly:

```rust
// src/prelude.rs
pub use crate::error::{Error, Result};
pub use crate::traits::{Deserialise, Serialise};
```

`use crate::prelude::*` is the one sanctioned glob inside the crate's own modules, only when the
prelude is small and stable.

## Documentation

`missing_docs = "deny"` applies to every public item — every `pub fn`, `pub struct`, `pub enum`,
`pub trait`, `pub type`, and `pub const` requires a doc comment.

### Doc Comment Structure

```rust
/// Short one-line summary ending with a period.
///
/// Extended explanation. Describe *what* and *why*, not *how*.
///
/// # Errors
///
/// Document every error variant and its conditions. Mandatory
/// for functions returning `Result`.
///
/// # Panics
///
/// Document every reachable panic. Omit if function cannot panic.
///
/// # Examples
///
/// ```rust
/// use my_crate::parse_count;
///
/// let n = parse_count("42").unwrap();
/// assert_eq!(n, 42);
/// ```
pub fn parse_count(s: &str) -> Result<u32> {
    // ...
}
```

### Module-Level Docs

Every module requires a `//!` inner doc comment:

```rust
//! Authentication client for the Foo API.
//!
//! Handles credential management, token refresh, and retry logic.
//! See [`Client`] for the primary entry point.
```

### Rules

- `/// # Safety` is mandatory on every `unsafe fn`.
- Prefer `[`TypeName`]` intra-doc links over bare type names.
- Doc examples must compile — use `# use` lines for hidden setup.
- Omit `# Arguments` section for obvious single-argument functions.

## Error Handling

### Library Crates

Define a single `Error` enum per crate using `thiserror`. Export a `Result` type alias. Place both
in `src/error.rs` and re-export from `lib.rs`.

```rust
/// All errors that can originate from this crate.
#[derive(Debug, thiserror::Error)]
#[non_exhaustive]
pub enum Error {
    /// An I/O operation failed.
    #[error("I/O error at `{path}`: {source}")]
    Io {
        path: std::path::PathBuf,
        #[source]
        source: std::io::Error,
    },

    /// The provided configuration was invalid.
    #[error("invalid configuration: {message}")]
    Config { message: String },
}

/// Crate-wide result alias.
pub type Result<T, E = Error> = std::result::Result<T, E>;
```

### Binary / Application Entry Points

Use `anyhow` only at the binary layer — never expose it in a library's public API.

```rust
fn main() -> anyhow::Result<()> {
    run()
}
```

### Error Handling Rules

- No `.unwrap()`, `.expect()`, or `panic!` outside tests; the workspace lints deny them. In tests,
  prefer `?` with a `Result`-returning test, then `.expect("why it holds")` over `.unwrap()`.
- `main` returns `anyhow::Result<()>` and propagates with `?` or `.context(...)`.
- Use `?` for propagation. Avoid explicit `match` on `Result` unless arms require meaningfully
  different handling.
- Prefer `map_err` over `unwrap_or_else` for error transformation.
- Never use `unwrap_or_default()` silently — prefer explicit fallback values that communicate
  intent.
- Write lowercase error messages without trailing punctuation.
- Use `#[from]` in thiserror enums for automatic conversions.
- Chain errors with context: `.map_err(|e| ...)?` or `anyhow::Context::context()`.
- Document error conditions with `/// # Errors`.
- Use `Option::map()` / `Option::and_then()` chains instead of nested `if let`.

## Types & Ownership

### Prefer Owned Types in Structs

Borrowed fields infect struct lifetimes and erode maintainability. Use owned types unless the struct
is explicitly a short-lived view type and the performance difference has been measured.

```rust
// Prefer this
pub struct Config {
    pub host: String,
    pub port: u16,
}

// Over this — viral lifetime, painful to compose
pub struct Config<'a> {
    pub host: &'a str,
    pub port: u16,
}
```

### Borrowing Rules

- Accept `&str` not `&String`, `&[T]` not `&Vec<T>`, `&Path` not `&PathBuf`
- Pass `Copy` types (≤ 24 bytes) by value, not by reference
- Use `Cow<'a, T>` when a function sometimes borrows, sometimes owns
- Move large data instead of cloning — transfer ownership
- `Arc<T>` for shared ownership across threads, `Rc<T>` for single-thread

### Clone Discipline

Never `.clone()` to satisfy the borrow checker without first asking whether restructured ownership
eliminates the need. Routine clones need no comment (an `Arc` before `tokio::spawn`, a small
`String` into an owned struct); explain only clones of large data or clones on a hot path.

### `From` / `Into` over Bespoke Converters

Implement `From<A> for B` rather than `fn a_to_b(a: A) -> B`. It participates in `?` and composes
with generic bounds.

### Newtype Pattern

Wrap primitive types to enforce domain invariants at the type level:

```rust
/// A validated, non-negative count of items.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Count(u32);

impl Count {
    /// Creates a new `Count`.
    ///
    /// # Errors
    ///
    /// Returns `Error::InvalidCount` if validation fails.
    pub fn new(value: u32) -> Result<Self> {
        Ok(Self(value))
    }

    /// Returns the inner value.
    #[must_use]
    pub fn get(self) -> u32 {
        self.0
    }
}
```

### Builder Pattern

Use builders for structs with 4+ fields or optional fields. Gate validation in `build()`:

```rust
#[derive(Debug, Default)]
pub struct ConfigBuilder {
    host: Option<String>,
    port: Option<u16>,
}

impl ConfigBuilder {
    /// Sets the host.
    #[must_use]
    pub fn host(mut self, host: impl Into<String>) -> Self {
        self.host = Some(host.into());
        self
    }

    /// Builds the [`Config`].
    ///
    /// # Errors
    ///
    /// Returns `Error::Config` if required fields are absent.
    pub fn build(self) -> Result<Config> {
        Ok(Config {
            host: self.host.ok_or_else(|| Error::Config {
                message: "host is required".into(),
            })?,
            port: self.port.unwrap_or(8080),
        })
    }
}
```

### Type Safety

- Use newtypes for IDs and validated data
- Model states as enums — make illegal states unrepresentable
- Exhaustive pattern matching without catch-all `_` for business logic
- `impl Trait` in return position for opaque concrete types
- `#[must_use]` on types and functions whose results must be consumed
- `#[non_exhaustive]` on public enums and structs
- Avoid stringly-typed APIs — parse into domain types at boundaries

## API Design

- Use builder pattern for constructors with 4+ parameters
- Parse input at system boundaries — validate once, use typed data internally
- Accept `Into<T>` and `AsRef<T>` for flexible public APIs
- Prefer iterators over collections in function signatures
- Keep public API surface minimal — use `pub(crate)` for internals
- Accept generics (static dispatch) for performance-critical code
- Use `dyn Trait` only for heterogeneous collections or plugin systems
- Implement `From<T>`, not `Into<T>` — the blanket impl provides `Into` for free
- Use associated types when there is exactly one implementation per type
- Use sealed traits to prevent external implementations

## Memory & Performance

- Profile first — use `cargo flamegraph` or `samply` with `--release`
- Prefer stack allocation. Avoid `Box<T>` unless the type is large, recursive, or must be
  type-erased.
- `Vec::with_capacity()` when the final size is known
- Use iterators over index-based loops — avoids bounds checks
- Keep iterator chains lazy; collect only when needed
- Use `entry()` API for conditional map insertion
- Use `write!()` instead of `format!()` to avoid intermediate allocations
- Prefer `&str` slices for zero-copy string handling
- Use `Cow<'_, str>` when sometimes owning, sometimes borrowing
- Avoid `collect()` into intermediate `Vec` when feeding another chain
- Use `#[inline]` on small hot-path functions sparingly
- Use `#[cold]` on error-path functions
- Enable LTO and `codegen-units = 1` for release builds

```rust
// Prefer lazy iterator chains
let sum: u64 = items
    .iter()
    .filter(|i| i.is_active())
    .map(|i| i.value)
    .sum();
```

## Safety & Unsafe

`unsafe_code = "forbid"` is set workspace-wide, and `forbid` cannot be lifted with `#[allow]` or
`#[expect]`. A crate that truly needs `unsafe` (FFI, intrinsics) can't override one lint while
inheriting the rest (`lints.workspace = true` admits no other keys), so it replaces that line with
a full copy of the workspace lint tables, changes `unsafe_code` to `"deny"` with a comment saying
why, and allows it only at the specific sites with `#[expect(unsafe_code, reason = "...")]`.

When `unsafe` is genuinely required (FFI, performance-critical intrinsics), isolate it behind a safe
abstraction boundary. The `unsafe` block must be the smallest possible scope.

Every `unsafe` block requires a `// SAFETY:` comment immediately above it. Every `unsafe fn`
requires a `# Safety` doc section.

```rust
// SAFETY: `ptr` is guaranteed non-null and aligned by the
// caller contract in `Config::as_ptr`, and the memory it
// points to lives for at least `'a`.
let slice = unsafe { std::slice::from_raw_parts(ptr, len) };
```

## Naming Conventions

Follow the Rust API Guidelines without exception.

| Item | Convention | Example |
| --- | --- | --- |
| Types, traits, enums | `UpperCamelCase` | `UserConfig` |
| Functions, methods | `snake_case` | `parse_count` |
| Constants, statics | `SCREAMING_SNAKE_CASE` | `MAX_RETRIES` |
| Modules | `snake_case` | `http_client` |
| Lifetimes | short, lowercase | `'a`, `'buf` |
| Type parameters | single uppercase | `T`, `E`, `Key` |

### Method Name Conventions

| Pattern | Semantics |
| --- | --- |
| `new(...)` | Infallible constructor |
| `try_new(...)` | Fallible constructor returning `Result` |
| `from_*` / `into_*` / `as_*` | Conversions (From/Into/borrow) |
| `with_*` | Builder-style setter returning `Self` |
| `is_*` / `has_*` | Boolean predicates |
| `to_*` | Expensive conversion (allocates) |

No `get_` prefix on getters. No `-rs` / `_rs` suffix on crates.

## Testing

See the **rust-testing** skill for comprehensive TDD patterns,
unit/integration/async/parameterized/property-based tests, and benchmarks.

Key rules from this guide:

- Write a failing test first. Implement minimum code to pass. Refactor under green. Never commit
  untested functionality.
- Unit tests go in `#[cfg(test)] mod tests` at the bottom of each source file. `use super::*` is the
  sanctioned glob.
- Name tests as `subject_condition_expected_outcome`.
- Integration tests go in `tests/` — each file is a separate compilation unit.
- Use `rstest` for parameterized tests. Use `proptest` for property-based tests.

## Async

See the **rust-async** skill for comprehensive async patterns with Tokio: runtime setup, task
management, channels, select, cancellation, streams, and structured concurrency.

Key rules from this guide:

- Commit to one async runtime per binary (Tokio is default).
- Never block inside an async function — use `tokio::time::sleep`, `tokio::fs`, `tokio::io`.
- Prefer specific Tokio features over `"full"` in library crates.

## CI / Tooling Gates

See [references/ci-tooling.md](references/ci-tooling.md) for the full CI script and recommended
tools table.

Essential commands:

```bash
cargo +nightly fmt --all
cargo +nightly clippy --workspace --all-features --all-targets -- -D warnings
cargo +nightly build --workspace --all-features --all-targets
cargo +nightly test --doc --workspace --all-features
cargo +nightly nextest run --workspace --all-features --all-targets
RUSTDOCFLAGS="-D warnings" cargo +nightly doc --workspace --all-features --no-deps
cargo deny check && cargo audit
```

Set `RUSTFLAGS="-D warnings"` in CI.

## Anti-Patterns

See [references/anti-patterns.md](references/anti-patterns.md) for the full list of common mistakes
organized by category (library code, types, visibility, documentation, performance).

## Related Skills

- [rust-async](../rust-async/SKILL.md) — Tokio-based async patterns
- [rust-testing](../rust-testing/SKILL.md) — unit, integration, async, and property tests
- [observability](../observability/SKILL.md) — `tracing` and metrics for Rust services
