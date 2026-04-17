---
name: rust-testing
description: >-
  Rust testing patterns with TDD methodology. Covers unit tests, integration tests, async
  tests, parameterized tests with rstest, property-based tests with proptest, benchmarks
  with criterion, doctests, and test organization. Use when writing or reviewing Rust tests.
---

# Rust Testing

TDD-driven testing patterns for Rust.

## TDD Cycle

Write a failing test first. Implement the minimum code to make it pass. Refactor under green. Never
commit code that adds functionality without a corresponding test.

1. **RED** — Write one failing test with a descriptive name
2. **Verify RED** — Run `cargo test`, confirm it fails for the expected reason (not a compile error
   or typo)
3. **GREEN** — Write the minimum code to make the test pass
4. **Verify GREEN** — All tests pass, no warnings
5. **REFACTOR** — Improve code structure while keeping tests green
6. **Repeat** — Next behavior, next failing test

## Unit Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_valid_input_returns_value() {
        let result = parse("42");
        assert_eq!(result, Ok(42));
    }

    #[test]
    fn parse_empty_string_returns_error() {
        let result = parse("");
        assert!(result.is_err());
    }
}
```

### Naming Convention

Use `unit__expected_behavior__condition`:

- `parse_valid_input_returns_value`
- `user_creation_fails_without_email`
- `cache_evicts_oldest_entry_when_full`

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
fn config_builds_with_valid_input() -> anyhow::Result<()> {
    let config = ConfigBuilder::default()
        .host("localhost")
        .build()?;
    assert_eq!(config.host, "localhost");
    Ok(())
}
```

Use `#[should_panic(expected = "...")]` sparingly and only when `Result` cannot model the failure
naturally. Always provide the `expected` substring.

```rust
#[test]
fn rejects_negative_amount() {
    let result = transfer(-100);
    assert!(matches!(
        result,
        Err(TransferError::InvalidAmount { .. })
    ));
}

#[test]
#[should_panic(expected = "index out of bounds")]
fn panics_on_out_of_bounds() {
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
use my_crate::Client;

#[test]
fn client_fetches_resource() {
    let client = Client::new("http://localhost:8080");
    let result = client.get("/resource");
    assert!(result.is_ok());
}
```

## Async Tests

```rust
#[tokio::test]
async fn fetches_data_concurrently() {
    let results = fetch_all(vec!["a", "b", "c"]).await;
    assert_eq!(results.len(), 3);
}

#[tokio::test]
async fn times_out_on_slow_response() {
    let result = tokio::time::timeout(
        Duration::from_millis(100),
        slow_operation(),
    )
    .await;
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
fn string_length(#[case] input: &str, #[case] expected: usize) {
    assert_eq!(input.len(), expected);
}
```

- Use `#[rstest]` with `#[case(...)]` for parameterized inputs
- Use `#[fixture]` for reusable test setup

## Property-Based Tests (proptest)

```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn roundtrip_serialization(value: i64) {
        let serialized = serialize(value);
        let deserialized = deserialize(&serialized)?;
        prop_assert_eq!(value, deserialized);
    }
}
```

- Define properties that must hold for all generated inputs
- Use custom strategies for domain-specific types

## Benchmarks (criterion)

```rust
use criterion::{black_box, criterion_group, Criterion};

fn bench_parse(c: &mut Criterion) {
    c.bench_function("parse_input", |b| {
        b.iter(|| parse(black_box("42")))
    });
}

criterion_group!(benches, bench_parse);
criterion::criterion_main!(benches);
```

- Always profile before optimizing
- Use `black_box()` to prevent the compiler from eliding benchmarked code
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
cargo test --all-targets --all-features
cargo clippy --all-targets --all-features -- -D warnings
cargo fmt --check
```

- Run all three checks in CI for every commit
- Use `cargo llvm-cov` or `cargo tarpaulin` for coverage
- Target 100% coverage wherever achievable
