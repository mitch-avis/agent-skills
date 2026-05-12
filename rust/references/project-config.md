# Project Configuration

Detailed configuration for Rust projects. The canonical standards are in the parent
[SKILL.md](../SKILL.md); this file contains ready-to-copy configuration blocks and rationale.

## rust-toolchain.toml

Pin the toolchain at the workspace root so every contributor and every CI run uses identical
compiler and tool versions:

```toml
# rust-toolchain.toml (workspace root)
[toolchain]
channel = "stable"
components = ["rustfmt", "clippy", "rust-src"]
```

## Workspace Layout

Use a workspace layout even for single-crate projects — it makes future decomposition trivial and
keeps tooling configuration centralised:

```text
my-project/
├── Cargo.toml          # [workspace] manifest
├── Cargo.lock          # always commit for binaries
├── rust-toolchain.toml
├── rustfmt.toml
├── clippy.toml         # optional per-lint configuration
├── deny.toml           # cargo-deny configuration
└── crates/
    └── my-crate/
        ├── Cargo.toml
        └── src/
```

Always commit `Cargo.lock` for binaries and CLI tools. Libraries should `.gitignore` it so
downstream consumers test against the full version range.

## Workspace Cargo.toml

```toml
[workspace]
members = ["crates/*"]
resolver = "3"  # edition 2024 default; explicit is clearer

[lints]
workspace = true

[workspace.lints.rust]
# Hard ban — override per-module only with an explicit #[allow] + reason
unsafe_code = "forbid"

# Deny outright: correctness and API-stability violations
future_incompatible = { level = "deny", priority = -1 }
nonstandard_style = { level = "deny", priority = -1 }

# Warn: real problems worth fixing
let_underscore = { level = "warn", priority = -1 }
unused = { level = "warn", priority = -1 }
deprecated = "warn"
missing_docs = "warn"

[workspace.lints.clippy]
# Baseline lint groups
all = { level = "deny", priority = -1 }
pedantic = { level = "deny", priority = -1 }
nursery = { level = "deny", priority = -1 }
cargo = { level = "deny", priority = -1 }

# Restriction: meta-linting
# Prefer `#[expect(...)]` over `#[allow(...)]` — fires a warning when the suppressed lint is no
# longer triggered (dead suppression detection).
allow_attributes = "deny"
allow_attributes_without_reason = "deny"

# Restriction: unsafe hygiene
# Every unsafe block must carry a `// SAFETY:` comment explaining the invariants.
undocumented_unsafe_blocks = "deny"

# Restriction: panic / unwrap discipline
unwrap_used = "deny"
expect_used = "deny"
get_unwrap = "deny"    # `.get(i).unwrap()` should be indexing or explicit match
panic = "deny"
unimplemented = "deny"
todo = "deny"

# Restriction: cast safety
# `as` conversions catches every `as`-cast; pedantic's cast_* lints provide specific diagnostics for
# the individual failure modes (truncation, sign loss, etc.). Having both means you get targeted
# advice AND a hard catch-all.
as_conversions = "deny"

# Restriction: string / formatting hygiene
# `format!()` to grow a `String` should be `write!(&mut s, ...)` instead.
format_push_string = "deny"
# `dbg!` left in committed code is always a mistake
dbg_macro = "deny"

# Restriction: reference-counting visibility
# `Arc::clone(&x)` is more explicit than `x.clone()` for Rc/Arc — makes reference-count bumps
# visible at the call site.
clone_on_ref_ptr = "warn"

# Restriction: boolean ergonomics
# Prefer `condition.then_some(value)` over `if condition { Some(value) } else { None }`.
if_then_some_else_none = "warn"

# Cargo: unavoidable noise
# Transitive dep version conflicts come from upstream crates and cannot be resolved by this
# workspace. Allow rather than generating unavoidable noise.
multiple_crate_versions = "allow"
```

Individual crates inherit workspace lints without duplication:

```toml
# crates/my-crate/Cargo.toml
[lints]
workspace = true
```

### Priority Resolution

Priority determines which rule wins when a lint belongs to multiple groups or when a group-level
setting conflicts with a per-lint override. Lower numbers have lower priority and are overridden by
higher ones. The implicit default is `0`.

| Priority | What it covers                                               |
| -------- | ------------------------------------------------------------ |
| `-2`     | `unused` (broad deny, overridden by everything below)        |
| `-1`     | All group-level lints (carve exceptions from the `-2` deny)  |
| `0`      | Individual lint overrides (e.g. `wildcard_imports = "deny"`) |

An individual lint declared without an explicit priority sits at `0` and therefore always wins over
group lints at `-1`. Use it to escalate specific lints above their group's level, or to allow
specific lints that a group would otherwise deny.

## Profile Configuration

```toml
[profile.release]
lto            = "thin"   # "fat" for maximum optimisation
codegen-units  = 1
strip          = "symbols"
panic          = "abort"

[profile.dev]
debug          = true
opt-level      = 0

[profile.test]
# Inherits dev; override only if test compile times are painful
```

## rustfmt.toml

```toml
# rustfmt.toml (workspace root)
edition                    = "2024"
group_imports              = "StdExternalCrate"
imports_granularity        = "Crate"
max_width                  = 100
use_small_heuristics       = "Max"
wrap_comments              = true
format_code_in_doc_comments = true
```

### Key Decisions

`imports_granularity = "Crate"` collapses all imports from the same crate into a single `use` tree.
Combined with `group_imports = "StdExternalCrate"`, rustfmt enforces the three-group order
automatically:

1. `std` / `core` / `alloc`
2. External crates
3. `crate::` / `super::` / `self::`

`use_small_heuristics = "Max"` combined with `max_width = 100` gives rustfmt maximum latitude to
keep expressions on one line before wrapping, reducing visual noise on wide monitors.

`format_code_in_doc_comments = true` is essential when `missing_docs = "deny"` is in force —
documentation will be numerous, and examples inside `///` blocks should be formatted consistently.

Never override rustfmt decisions with `#[rustfmt::skip]` except in macro-generated code or alignment
tables where the formatter produces genuinely unreadable output. Every skip requires a comment
explaining why.

## clippy.toml

Use `clippy.toml` for lints that accept configuration rather than being on/off:

```toml
# clippy.toml
cognitive-complexity-threshold = 15
too-many-arguments-threshold   = 6
type-complexity-threshold      = 250

# Allow the common Rust test idiom of .unwrap() / .expect() / panic! in test functions.
allow-unwrap-in-tests = true
allow-expect-in-tests = true
allow-panic-in-tests  = true
```
