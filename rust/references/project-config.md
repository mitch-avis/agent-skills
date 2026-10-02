# Project Configuration

Detailed configuration for Rust projects. The canonical standards are in the parent
[SKILL.md](../SKILL.md); this file contains ready-to-copy configuration blocks and rationale.

These templates cover strict linting, edition 2024, the nightly toolchain, and centralized policy
that is easy to copy into new applications, workspaces, and standalone libraries.

## Policy Summary

- Use the nightly Rust toolchain through `rust-toolchain.toml`, and run cargo as `cargo +nightly`.
- Do not set `rust-version` in `Cargo.toml`.
- Use edition 2024 for new projects.
- Keep lint levels in `Cargo.toml`; keep Clippy thresholds in `clippy.toml`.
- Run Clippy with `-D warnings` in CI and before merge.
- Nightly rustfmt enforces the nightly-only options in `rustfmt.toml`.

## rust-toolchain.toml

Use the `nightly` channel so `rustup update` moves projects to the newest compiler, rustfmt, and
Clippy. This intentionally prioritizes current Rust over old-MSRV compatibility. Date-pin
(`nightly-YYYY-MM-DD`) only while a nightly regression blocks the build.

```toml
# rust-toolchain.toml (project or workspace root)
[toolchain]
# Use the nightly toolchain. Run `rustup update` regularly so local development and CI pick up
# current compiler, rustfmt, and Clippy behavior.
channel = "nightly"
profile = "minimal"
components = ["rust-src", "rustfmt", "clippy"]
```

## Layouts

Use a workspace layout for multi-crate applications and services. Standalone libraries can stay as a
single crate when there is no real need for workspace indirection.

```text
workspace-project/
├── Cargo.toml          # [workspace] manifest
├── Cargo.lock          # commit for applications, services, and workspaces
├── rust-toolchain.toml
├── rustfmt.toml
├── clippy.toml
├── deny.toml           # cargo-deny configuration when used
├── apps/
│   └── api/
│       ├── Cargo.toml
│       └── src/
└── crates/
    └── domain-crate/
        ├── Cargo.toml
        └── src/
```

```text
standalone-library/
├── Cargo.toml          # [package] manifest
├── rust-toolchain.toml
├── rustfmt.toml
├── clippy.toml
├── README.md
├── examples/
└── src/
```

Commit `Cargo.lock` for applications, services, and workspaces. Standalone libraries may omit it if
the team wants downstream consumers to exercise the full dependency version range.

## Standalone Library Cargo.toml

Use this pattern for a single library crate that is not a workspace. The lint policy is declared
with `[lints.*]` directly because there are no member crates to inherit from a workspace root.

```toml
[package]
name = "my-library"
version = "0.1.0"
edition = "2024"
license = "MIT"
description = "Short, accurate package description"
readme = "README.md"
repository = "https://github.com/example/my-library"
keywords = ["domain", "library"]
categories = ["asynchronous"]
include = ["**/*.rs", "Cargo.toml", "Cargo.lock", "README.md", "LICENSE"]

[dependencies]

[dev-dependencies]

[package.metadata.docs.rs]
all-features = true
rustdoc-args = ["--cfg", "docsrs"]
```

### Standalone Profiles

```toml
# Development profile: fast iteration.
[profile.dev]
opt-level = 0

# Production release profile: maximum runtime optimization.
[profile.release]
opt-level = 3
lto = "fat"       # Full link-time optimization; slower builds, better runtime output.
codegen-units = 1 # Better optimization, slower compile.
strip = true      # Strip symbols for smaller binaries.
panic = "abort"   # Smaller binaries; no unwinding across panic boundaries.

# Fast optimized builds for local profiling and smoke testing.
[profile.release-dev]
inherits = "release"
lto = "thin"       # Faster than "fat" while preserving useful optimization.
codegen-units = 16 # Faster compilation than release.
strip = false      # Keep symbols for debugging.
debug = true       # Include debug info.

# Test profile: modest optimization without heavily slowing builds.
[profile.test]
opt-level = 1
```

### Standalone Lints

```toml
# Lint policy
#
# Keep lint levels centralized here instead of scattering crate-level attributes through source
# files. This crate is standalone, so it uses `[lints.*]` directly instead of workspace lint
# inheritance.
#
# Clippy groups and policy lints are hard errors. The few compiler lints left at `warn` keep a
# half-finished edit building; the gate (`cargo +nightly clippy ... -- -D warnings`) fails on them.
[lints.rust]
# Unsafe is forbidden by default for this library. If unsafe code ever becomes necessary, isolate it
# behind a small safe API and document the invariants before relaxing this lint locally.
unsafe_code = "forbid"

# Deny compiler lint groups that usually indicate future breakage or non-idiomatic public API
# shape. These should not be treated as optional cleanup.
future_incompatible = { level = "deny", priority = -1 }
nonstandard_style = { level = "deny", priority = -1 }

# Warn-level so in-progress code still builds; the `-D warnings` gate turns them into failures.
deprecated = "warn"
let_underscore = { level = "warn", priority = -1 }
unused = { level = "warn", priority = -1 }
unreachable_pub = "warn"

# Public library crates should document exported items so generated rustdoc is useful.
missing_docs = "deny"

[lints.rustdoc]
# Treat rustdoc as part of the public API. Broken links and bare URLs make generated docs harder to
# trust and are cheap to fix when caught early.
broken_intra_doc_links = "deny"
bare_urls = "deny"

[lints.clippy]
# Broad coverage: Clippy's default (`all`), pedantic, nursery, and Cargo groups are hard errors.
# Priority -1 lets the individual policy lints below, at the default priority 0, override a group
# cleanly when a lint needs a different level.
all = { level = "deny", priority = -1 }
pedantic = { level = "deny", priority = -1 }
nursery = { level = "deny", priority = -1 }
cargo = { level = "deny", priority = -1 }

# Prefer `#[expect(...)]` over `#[allow(...)]`: it warns when the suppression is no longer needed.
# If an allow is unavoidable, require a reason so suppressions stay auditable.
allow_attributes = "deny"
allow_attributes_without_reason = "deny"

# Every unsafe block must carry a `// SAFETY:` comment explaining the invariants.
undocumented_unsafe_blocks = "deny"

# Library code should return errors, not panic or unwrap. `clippy.toml` controls the narrower test
# exceptions so test code can still use clear `expect(...)` messages where helpful.
unwrap_used = "deny"
expect_used = "deny"
get_unwrap = "deny"    # `.get(i).unwrap()` should be indexing or explicit match.
panic = "deny"
unimplemented = "deny"
todo = "deny"

# `as` catches every unchecked cast. Prefer `From`, `TryFrom`, explicit typed literals, or a local
# lint exception with a reason when a cast is truly intentional.
as_conversions = "deny"

# `format!()` to grow a `String` should be `write!(&mut s, ...)` instead.
format_push_string = "deny"
# `dbg!` left in committed code is always a mistake.
dbg_macro = "deny"

# Avoid hidden imports in production modules. Test modules may still use `use super::*` when that is
# the clearest local pattern.
wildcard_imports = "deny"

# `Arc::clone(&x)` is more explicit than `x.clone()` for Rc/Arc and makes reference-count bumps
# visible at the call site. Warn-level for iteration; the `-D warnings` gate enforces it.
clone_on_ref_ptr = "warn"

# Prefer `condition.then_some(value)` over `if condition { Some(value) } else { None }`.
if_then_some_else_none = "warn"

# Transitive duplicate crate versions come from upstream dependency graphs. Track them during
# dependency upgrades rather than failing every Clippy run on noise this crate cannot directly fix.
multiple_crate_versions = "allow"
```

## Workspace Cargo.toml

Use this pattern for services and applications split across multiple crates. The root owns package
metadata, dependency versions, profiles, and lint policy; member crates inherit where appropriate.

```toml
[workspace]
resolver = "3"
members = ["apps/*", "crates/*"]

[workspace.package]
edition = "2024"

[workspace.dependencies]
# Keep shared dependency versions here. Member crates should use `{ workspace = true }` unless they
# need a local feature override.
anyhow = "1.0"
serde = { version = "1.0", features = ["derive"] }
tokio = { version = "1.0", features = ["macros", "rt-multi-thread", "sync", "time"] }
tracing = "0.1"
```

### Workspace Profiles

```toml
# Development profile: fast iteration.
[profile.dev]
opt-level = 0

# Production release profile: maximum runtime optimization.
[profile.release]
opt-level = 3
lto = "fat"       # Full link-time optimization; slower builds, better runtime output.
codegen-units = 1 # Better optimization, slower compile.
strip = true      # Strip symbols for smaller binaries.
panic = "abort"   # Smaller binaries; no unwinding across panic boundaries.

# Fast optimized builds for local profiling and smoke testing.
[profile.release-dev]
inherits = "release"
lto = "thin"       # Faster than "fat" while preserving useful optimization.
codegen-units = 16 # Faster compilation than release.
strip = false      # Keep symbols for debugging.
debug = true       # Include debug info.

# Test profile: modest optimization without heavily slowing builds.
[profile.test]
opt-level = 1
```

### Workspace Lints

```toml
# Workspace lint policy
#
# Keep lint levels centralized in the workspace root. Member crates opt in with:
#
# [lints]
# workspace = true
#
# Clippy groups and policy lints are hard errors. The few compiler lints left at `warn` keep a
# half-finished edit building; the gate (`cargo +nightly clippy --workspace ... -- -D warnings`)
# fails on them.
[workspace.lints.rust]
# Unsafe is forbidden by default for this workspace. If unsafe code ever becomes necessary, isolate
# it behind a small safe API and document the invariants before relaxing this lint locally.
unsafe_code = "forbid"

# Deny compiler lint groups that usually indicate future breakage or non-idiomatic public API
# shape. These should not be treated as optional cleanup.
future_incompatible = { level = "deny", priority = -1 }
nonstandard_style = { level = "deny", priority = -1 }

# Warn-level so in-progress code still builds; the `-D warnings` gate turns them into failures.
deprecated = "warn"
let_underscore = { level = "warn", priority = -1 }
unused = { level = "warn", priority = -1 }
unreachable_pub = "warn"

# Workspaces that expose library crates should document exported items so rustdoc remains useful.
missing_docs = "deny"

[workspace.lints.rustdoc]
# Treat rustdoc as part of the public API. Broken links and bare URLs make generated docs harder to
# trust and are cheap to fix when caught early.
broken_intra_doc_links = "deny"
bare_urls = "deny"

[workspace.lints.clippy]
# Broad coverage: Clippy's default (`all`), pedantic, nursery, and Cargo groups are hard errors.
# Priority -1 lets the individual policy lints below, at the default priority 0, override a group
# cleanly when a lint needs a different level.
all = { level = "deny", priority = -1 }
pedantic = { level = "deny", priority = -1 }
nursery = { level = "deny", priority = -1 }
cargo = { level = "deny", priority = -1 }

# Prefer `#[expect(...)]` over `#[allow(...)]`: it warns when the suppression is no longer needed.
# If an allow is unavoidable, require a reason so suppressions stay auditable.
allow_attributes = "deny"
allow_attributes_without_reason = "deny"

# Every unsafe block must carry a `// SAFETY:` comment explaining the invariants.
undocumented_unsafe_blocks = "deny"

# Workspace code should return errors, not panic or unwrap. `clippy.toml` controls the narrower test
# exceptions so test code can still use clear `expect(...)` messages where helpful.
unwrap_used = "deny"
expect_used = "deny"
get_unwrap = "deny"    # `.get(i).unwrap()` should be indexing or explicit match.
panic = "deny"
unimplemented = "deny"
todo = "deny"

# `as` catches every unchecked cast. Prefer `From`, `TryFrom`, explicit typed literals, or a local
# lint exception with a reason when a cast is truly intentional.
as_conversions = "deny"

# `format!()` to grow a `String` should be `write!(&mut s, ...)` instead.
format_push_string = "deny"
# `dbg!` left in committed code is always a mistake.
dbg_macro = "deny"

# Avoid hidden imports in production modules. Test modules may still use `use super::*` when that is
# the clearest local pattern.
wildcard_imports = "deny"

# `Arc::clone(&x)` is more explicit than `x.clone()` for Rc/Arc and makes reference-count bumps
# visible at the call site. Warn-level for iteration; the `-D warnings` gate enforces it.
clone_on_ref_ptr = "warn"

# Prefer `condition.then_some(value)` over `if condition { Some(value) } else { None }`.
if_then_some_else_none = "warn"

# Transitive duplicate crate versions come from upstream dependency graphs. Track them during
# dependency upgrades rather than failing every Clippy run on noise this workspace cannot directly
# fix.
multiple_crate_versions = "allow"
```

Individual crates inherit workspace settings without duplication:

```toml
[package]
name = "my-crate"
version = "0.1.0"
edition.workspace = true

[lints]
workspace = true

[dependencies]
serde = { workspace = true }
```

### Priority Resolution

Priority determines which rule wins when a lint belongs to multiple groups or when a group-level
setting conflicts with a per-lint override. Lower numbers have lower priority and are overridden by
higher ones. The implicit default is `0`.

| Priority | What it covers |
| --- | --- |
| `-1` | Lint groups: Clippy `all`, `pedantic`, `nursery`, and `cargo`; rustc `unused` and friends. |
| `0` | Individual lint policy and exceptions such as `wildcard_imports` or `multiple_crate_versions`. |

Do not put broad groups and individual overrides at the same priority. Clippy's
`lint_groups_priority` lint intentionally rejects ambiguous priority ordering.

## rustfmt.toml

```toml
# rustfmt.toml (project or workspace root)

# Rustfmt configuration for Rust projects.
#
# Stable rustfmt ignores the nightly-only options below with warnings. Keep them here and run
# `cargo +nightly fmt --all` when you want import grouping, comment wrapping, and rustdoc
# code-block formatting enforced locally.

# Parse and format code using the edition expected by the package manifests. `style_edition` keeps
# direct `rustfmt` runs aligned with `cargo fmt`.
edition = "2024"
style_edition = "2024"

# Keep line width conventional for Rust while allowing compact expressions when they still fit.
max_width = 100
newline_style = "Unix"
use_small_heuristics = "Max"

# Nightly-only formatting policy. These are warnings on stable and enforced by nightly rustfmt.
group_imports = "StdExternalCrate"
imports_granularity = "Crate"
wrap_comments = true
format_code_in_doc_comments = true
```

### Rustfmt Decisions

`imports_granularity = "Crate"` collapses imports from the same crate into a single `use` tree.
Combined with `group_imports = "StdExternalCrate"`, nightly rustfmt enforces three import groups:

1. `std` / `core` / `alloc`
2. External crates
3. `crate::` / `super::` / `self::`

`use_small_heuristics = "Max"` combined with `max_width = 100` gives rustfmt maximum latitude to
keep expressions on one line before wrapping, reducing visual noise on wide monitors.

`format_code_in_doc_comments = true` keeps rustdoc examples formatted consistently. This is useful
when `missing_docs = "deny"` makes public documentation part of normal development.

Never override rustfmt decisions with `#[rustfmt::skip]` except in macro-generated code or alignment
tables where the formatter produces genuinely unreadable output. Every skip requires a comment
explaining why.

## clippy.toml

Use `clippy.toml` for lints that accept configuration rather than being on/off. Keep lint levels in
`Cargo.toml` so the policy remains visible to Cargo, Clippy, and reviewers.

```toml
# clippy.toml (project or workspace root)

# Clippy configuration for lints that need thresholds or policy knobs.
#
# Keep lint levels in Cargo.toml. Use this file only for configurable lint behavior so the split
# between "which lints are enabled" and "how strict a lint is" stays easy to understand.

# Complexity thresholds are intentionally stricter than Clippy defaults, but still high enough to
# avoid forcing premature abstractions in normal application and library code.
cognitive-complexity-threshold = 15
too-many-arguments-threshold = 6
type-complexity-threshold = 250

# Test code may use panic-style assertions and direct unwrapping when that keeps tests focused.
# Production/library code remains governed by the deny-level lint policy in Cargo.toml.
allow-unwrap-in-tests = true
allow-expect-in-tests = true
allow-panic-in-tests = true
```

## Validation Commands

```bash
cargo +nightly fmt --all
cargo +nightly clippy --workspace --all-features --all-targets -- -D warnings
cargo +nightly build --workspace --all-features --all-targets
cargo +nightly test --doc --workspace --all-features
cargo +nightly nextest run --workspace --all-features --all-targets
```

The same commands cover standalone crates and workspaces. For crates with feature flags, also run
`cargo hack clippy --workspace --each-feature -- -D warnings`; before a release, rerun the gates
with `--release`.
