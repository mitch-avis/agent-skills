# CI and Tooling Gates

Every CI run must pass all of the following before merge:

```bash
# Format check (non-destructive in CI)
cargo +nightly fmt --all --check

# Lint (warnings are errors)
cargo +nightly clippy --workspace --all-features --all-targets -- -D warnings

# Build every target
cargo +nightly build --workspace --all-features --all-targets

# Test suite: nextest for unit and integration tests, cargo test for doctests
cargo +nightly nextest run --workspace --all-features --all-targets
cargo +nightly test --doc --workspace --all-features

# Documentation build (catches broken links and missing docs)
RUSTDOCFLAGS="-D warnings" cargo +nightly doc --workspace --all-features --no-deps

# Dependency audit
cargo deny check
cargo audit
```

Set `RUSTFLAGS="-D warnings"` in CI to promote all warnings to errors. This catches lint regressions
that `clippy` does not cover (e.g., dead code warnings from the compiler itself).

## Recommended Tools

| Tool | Purpose | Install |
| --- | --- | --- |
| `rustfmt` | Formatting | `rustup component add rustfmt` |
| `clippy` | Linting | `rustup component add clippy` |
| `cargo-deny` | License & vulnerability policy | `cargo install cargo-deny` |
| `cargo-audit` | CVE auditing | `cargo install cargo-audit` |
| `cargo-nextest` | Test runner (required by the gates above) | `cargo install cargo-nextest` |
| `cargo-geiger` | Unsafe surface tracking | `cargo install cargo-geiger` |
| `cargo-flamegraph` | Profiling | `cargo install flamegraph` |
| `criterion` | Benchmarking | add as `[dev-dependency]` |
| `cargo-llvm-cov` | Coverage | `cargo install cargo-llvm-cov` |
| `samply` | Sampling profiler | `cargo install samply` |
