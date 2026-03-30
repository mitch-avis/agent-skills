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

[workspace.lints.rust]
missing_docs             = "deny"
unused                   = { level = "deny", priority = -2 }
rust-2018-idioms         = { level = "warn", priority = -1 }
rust-2024-compatibility  = { level = "deny", priority = -1 }
unreachable_pub          = "warn"
unsafe_code              = "deny"
let_underscore_drop      = "warn"

[workspace.lints.clippy]
correctness = { level = "deny",  priority = -1 }
suspicious  = { level = "warn",  priority = -1 }
complexity  = { level = "warn",  priority = -1 }
perf        = { level = "warn",  priority = -1 }
style       = { level = "warn",  priority = -1 }
pedantic    = { level = "warn",  priority = -1 }
nursery     = { level = "warn",  priority = -1 }

# Elevate individual lints above group defaults (implicit 0)
wildcard_imports = "deny"
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

| Priority | What it covers |
| --- | --- |
| `-2` | `unused` (broad deny, overridden by everything below) |
| `-1` | All group-level lints (carve exceptions from the `-2` deny) |
| `0` | Individual lint overrides (e.g. `wildcard_imports = "deny"`) |

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
```
