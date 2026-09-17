---
name: python-anti-patterns
description: >-
  Reviews Python code for common anti-patterns across architecture, typing, async, testing,
  configuration, and operations. Use when auditing changes, polishing a patch before merge, or
  debugging behavior that may come from known Python mistakes.
---

# Python Anti-Patterns

Use this skill as a final-pass checklist. It is intentionally compact. It should point out the
mistakes most likely to survive otherwise good Python code.

## Architecture

- Avoid mixing transport parsing, business rules, and I/O in one function.
- Avoid exposing ORM models or persistence objects as API contracts.
- Avoid factories, registries, and abstractions that solve no current problem.
- Avoid generic buckets like `utils` when a real module boundary exists.

## Configuration and Secrets

- Avoid hardcoded credentials, URLs, and environment-specific values.
- Avoid scattered `os.getenv()` calls instead of a typed settings layer.
- Avoid startup behavior controlled by undocumented environment variables.

## Types and Interfaces

- Avoid untyped public functions.
- Avoid `list` and `dict` without type parameters on public boundaries.
- Avoid `Any` escaping from dynamic edges into the core domain.
- Avoid relying on conventions where a protocol or typed model would make the contract explicit.

## Async and Concurrency

- Avoid blocking the event loop with `time.sleep()`, `requests`, or sync database clients.
- Avoid fire-and-forget tasks without ownership, cancellation, or visibility.
- Avoid unbounded queues or fan-out with no concurrency cap.

## Error Handling and Cleanup

- Avoid `except Exception: pass` and other silent failure paths.
- Avoid retry logic duplicated across multiple layers.
- Avoid missing timeouts on external I/O.
- Avoid resource cleanup that depends on the happy path completing.

## Testing

- Avoid tests that only cover the happy path.
- Avoid over-mocking internal behavior instead of faking external boundaries.
- Avoid test-only hooks added to production code.
- Avoid assertions so weak that the test would pass through major regressions.

## Tooling and Operations

- Avoid `uv pip install ...` as the default workflow in uv-native repos.
- Avoid parallel formatter or linter stacks with overlapping responsibilities.
- Avoid profiling guesses without real measurements.
- Avoid unbounded log labels, leaked secrets, or noisy expected errors.

## Review Order

1. Boundary design
2. Configuration and secrets
3. Async or I/O hazards
4. Types and contracts
5. Failure handling and cleanup
6. Tests
7. Tooling drift

## Related Skills

- [python](../python/SKILL.md) — preferred baseline patterns
- [python-resilience](../python-resilience/SKILL.md) — error, retry, timeout, and cleanup guidance
- [python-type-safety](../python-type-safety/SKILL.md) — positive type-system patterns
- [python-modernization](../python-modernization/SKILL.md) — tooling cleanup and migration
