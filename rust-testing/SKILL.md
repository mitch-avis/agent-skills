---
name: rust-testing
description: >-
  Use before writing or changing Rust tests (#[test], tests/, benches/, doctests) or when a Rust
  test fails. Covers unit and integration tests, async tests, rstest parameterization, proptest,
  criterion benchmarks, doctests, and test organization, following TDD.
---

# Rust Testing

TDD-driven testing patterns for Rust.

## TDD Cycle

Write a failing test first. Implement the minimum code to make it pass. Refactor under green. Never
commit code that adds functionality without a corresponding test.

1. **RED** — Write one failing test with a descriptive name
2. **Verify RED** — Run `cargo +nightly nextest run <filter>`, confirm it fails for the expected
   reason (not a compile error or typo)
3. **GREEN** — Write the minimum code to make the test pass
4. **Verify GREEN** — All tests pass, no warnings
5. **REFACTOR** — Improve code structure while keeping tests green
6. **Repeat** — Next behavior, next failing test

## Unit Tests

Every test follows Arrange-Act-Assert with `// Arrange`, `// Act`, and `// Assert` labels (`// Act
& Assert` for `#[should_panic]`); the full rule, including how to convert an existing file, is in
the [test-driven-development](../test-driven-development/SKILL.md#test-structure-arrange-act-assert)
skill.

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_valid_input_returns_value() {
        // Act
        let result = parse("42");

        // Assert
        assert_eq!(result, Ok(42));
    }

    #[test]
    fn parse_empty_string_returns_error() {
        // Act
        let result = parse("");

        // Assert
        assert!(result.is_err());
    }
}
```

### Naming Convention

Use `subject_condition_expected_outcome`, the same order as the Python skills' test names:

- `parse_valid_input_returns_value`
- `user_creation_without_email_fails`
- `cache_when_full_evicts_oldest_entry`

### Organization

- Place unit tests in `#[cfg(test)] mod tests` at the bottom of each source file
- Use `use super::*` to access the parent module — this is the one sanctioned unconditional glob
  (not subject to the `wildcard_imports = "deny"` intent)
- Group related tests in nested modules for clarity

## Assertions

Prefer specific assertions over `assert!(expr)`:

```rust
assert_eq!(result, 42);
assert!(result.is_err());
```

For `Result`-returning tests, propagate with `?` rather than `.unwrap()`:

```rust
#[test]
fn config_builder_with_host_builds_config() -> anyhow::Result<()> {
    // Arrange
    let builder = ConfigBuilder::default().host("localhost");

    // Act
    let config = builder.build()?;

    // Assert
    assert_eq!(config.host, "localhost");
    Ok(())
}
```

Use `#[should_panic(expected = "...")]` sparingly and only when `Result` cannot model the failure
naturally. Always provide the `expected` substring.

```rust
#[test]
fn transfer_negative_amount_returns_invalid_amount() {
    // Act
    let result = transfer(-100);

    // Assert
    assert!(matches!(
        result,
        Err(TransferError::InvalidAmount { .. })
    ));
}

#[test]
#[should_panic(expected = "index out of bounds")]
fn dangerous_index_out_of_bounds_panics() {
    // Act & Assert
    dangerous_index(100);
}
```

- Test `Result` returns with `is_err()`, `matches!`, or exact variant matching
- Use `#[should_panic(expected = "...")]` for panic tests
- Test error messages and error context, not just error types

## Integration Tests

- Place in `tests/` directory (each file is a separate test binary)
- Create `tests/common/mod.rs` for shared test utilities
- Integration tests can only access the public API

```rust
// tests/api_integration.rs
mod common;

use my_crate::Client;

#[test]
fn client_get_existing_resource_returns_ok() {
    // Arrange
    let server = common::FakeServer::with_resource("/resource", "ok");
    let client = Client::new(&server.url());

    // Act
    let result = client.get("/resource");

    // Assert
    assert!(result.is_ok());
}
```

## Async Tests

```rust
#[tokio::test]
async fn fetch_all_three_ids_returns_three_results() {
    // Arrange
    let ids = vec!["a", "b", "c"];

    // Act
    let results = fetch_all(ids).await;

    // Assert
    assert_eq!(results.len(), 3);
}

#[tokio::test]
async fn slow_operation_past_timeout_returns_elapsed() {
    // Arrange
    let limit = Duration::from_millis(100);

    // Act
    let result = tokio::time::timeout(limit, slow_operation()).await;

    // Assert
    assert!(result.is_err());
}
```

- Use `#[tokio::test]` attribute for async test functions
- Test timeouts explicitly with `tokio::time::timeout`

## Parameterized Tests (rstest)

```rust
use rstest::rstest;

#[rstest]
#[case("hello", 5)]
#[case("", 0)]
#[case("rust", 4)]
fn str_len_ascii_input_returns_byte_count(#[case] input: &str, #[case] expected: usize) {
    // Act
    let len = input.len();

    // Assert
    assert_eq!(len, expected);
}
```

- Use `#[rstest]` with `#[case(...)]` for parameterized inputs
- Use `#[fixture]` for reusable test setup

## Property-Based Tests (proptest)

```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn serialize_then_deserialize_returns_original(value: i64) {
        // Arrange
        let serialized = serialize(value);

        // Act
        let deserialized = deserialize(&serialized)?;

        // Assert
        prop_assert_eq!(value, deserialized);
    }
}
```

- Define properties that must hold for all generated inputs
- Use custom strategies for domain-specific types

## Benchmarks (criterion)

```rust
use std::hint::black_box;

use criterion::{criterion_group, Criterion};

fn bench_parse(c: &mut Criterion) {
    c.bench_function("parse_input", |b| {
        b.iter(|| parse(black_box("42")))
    });
}

criterion_group!(benches, bench_parse);
criterion::criterion_main!(benches);
```

- Always profile before optimizing
- Use `std::hint::black_box()` to prevent the compiler from eliding benchmarked code
- Place benchmarks in `benches/` directory

## Doctests

- Every public function should have a doctest in `# Examples`
- Use `?` in examples with a hidden `# fn main() -> Result<...>`
- Hide setup boilerplate with `#` prefix

## Test Helpers

- Create helper functions for common test setup
- Use RAII patterns — setup in constructor, cleanup in `Drop`
- Keep helpers in the test module or `tests/common/mod.rs`
- Prefer explicit setup over magic

## CI Integration

```bash
cargo +nightly fmt --all
cargo +nightly clippy --workspace --all-features --all-targets -- -D warnings
cargo +nightly build --workspace --all-features --all-targets
cargo +nightly test --doc --workspace --all-features
cargo +nightly nextest run --workspace --all-features --all-targets
```

- Run all five checks in CI for every commit; nextest skips doctests, so keep `cargo test --doc`
- Use `cargo llvm-cov` or `cargo tarpaulin` for coverage
- Target 100% coverage wherever achievable

## Related Skills

- [rust](../rust/SKILL.md) — core Rust style and project layout
- [test-driven-development](../test-driven-development/SKILL.md) — write the failing test first
- [systematic-debugging](../systematic-debugging/SKILL.md) — reproduce a bug as a failing test
  before fixing
