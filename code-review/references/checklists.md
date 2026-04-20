# Review Checklists

Per-dimension checklists for line-by-line code review. Apply the relevant section based on the
nature of the change.

## Correctness

- [ ] Logic handles edge cases (empty, null, zero, negative, boundary values)
- [ ] Error paths are handled — not silently swallowed or caught too broadly
- [ ] Async errors are awaited or surfaced
- [ ] Concurrent access is safe (locks, atomics, immutability)
- [ ] No race conditions or check-then-act (TOCTOU) patterns
- [ ] State mutations are intentional and isolated
- [ ] Numeric overflow / floating-point precision considered where relevant
- [ ] Off-by-one errors checked in loops, slices, and ranges

## Security

- [ ] User input validated at system boundaries
- [ ] Database queries parameterized — no string interpolation into SQL/NoSQL/shell
- [ ] AuthN/AuthZ checks present on new endpoints and sensitive operations
- [ ] No secrets, tokens, or PII in code, logs, error messages, or commits
- [ ] Output properly encoded for context (HTML, URL, JSON, shell)
- [ ] No path traversal in file operations
- [ ] No SSRF in outbound requests (allowlist destinations, validate URLs)
- [ ] No insecure deserialization of untrusted data
- [ ] Dependencies from trusted sources, pinned, scanned for CVEs
- [ ] CSRF protection on state-changing endpoints
- [ ] Rate limiting on auth endpoints and expensive operations

## Performance

- [ ] No N+1 queries — use prefetch/join/batch
- [ ] Loops are O(n) or better in hot paths; no nested O(n²) over large inputs
- [ ] Database queries hit appropriate indexes
- [ ] Queries and loops are bounded (LIMIT, pagination, max iterations)
- [ ] No unnecessary allocations in tight loops
- [ ] Resources released (file handles, connections, subscriptions)
- [ ] Caching used where appropriate; cache invalidation correct
- [ ] No blocking I/O in async contexts

## Tests

- [ ] New behavior has corresponding tests
- [ ] Tests assert outcomes, not implementation details
- [ ] Edge cases covered (empty input, errors, boundaries, concurrency)
- [ ] Tests would actually fail if the behavior broke (no tautological assertions)
- [ ] Test names describe what is being verified
- [ ] No test interdependence or shared mutable state
- [ ] Mocks/fakes do not hide real bugs

## Design

- [ ] Single responsibility — modules and functions do one thing
- [ ] No unnecessary abstractions or premature generalization
- [ ] Changes in the right layer (controller vs service vs repository)
- [ ] Dependencies point in the right direction (high-level does not depend on low-level)
- [ ] Public API surface minimal — nothing exposed unnecessarily
- [ ] No feature flags or config left in a stale state
- [ ] Existing patterns followed; deviations justified

## Readability and Maintainability

- [ ] Names reveal intent (variables, functions, types)
- [ ] No magic numbers or strings — extract named constants
- [ ] Functions short enough to hold in your head
- [ ] No commented-out code or dead branches
- [ ] Comments explain *why*, not *what*
- [ ] Complex logic has a brief explanation
- [ ] Public APIs documented
