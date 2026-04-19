# Rust Anti-Patterns

Common mistakes and bad practices to avoid in Rust code.

## Library Code

- **Panicking in library code** — `.unwrap()`, `.expect()`, `panic!()` are not acceptable in library
  code paths reachable at runtime. Use `Result`.
- **No `.unwrap()` abuse** — use `?` or handle the error.
- **No locks held across `.await`** — see the rust-async skill.

## Types & Ownership

- **Silent clones** — `.clone()` without a comment suggests a design problem. Prefer restructured
  ownership.
- **Stringly-typed APIs** — `fn process(action: &str)` invites runtime errors. Use enums or
  newtypes.
- **No `&String` / `&Vec<T>`** — use `&str` / `&[T]`.
- **No `Box<dyn Trait>` when `impl Trait` works** — prefer static dispatch.

## Visibility & Structure

- **`pub` by default** — everything starts private. Widen visibility only for concrete consumers.
- **`mod.rs` for leaf modules** — use `module.rs` unless submodules exist.
- **Glob imports outside test modules** — denied by lint.

## Documentation & Annotations

- **Skipping `#[must_use]`** — annotate all functions whose return value is meaningful and silently
  discarding it would be a bug.
- **Missing `#[non_exhaustive]`** — every public enum that may gain variants must be marked.
  Omitting it is a semver hazard.
- **Reimplementing standard traits** — derive `Debug`, `Clone`, `PartialEq`, etc. wherever the
  derived implementation is correct. Comment manual impls.

## Performance

- **Magic numbers** — inline numeric literals with non-obvious meaning must be named constants with
  doc comments.
- **No intermediate `.collect()` calls** — keep iterator chains lazy.
- **No premature optimization** — measure first.
