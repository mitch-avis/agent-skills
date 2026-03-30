# Condition-Based Waiting

Flaky tests often guess at timing with arbitrary delays. This creates race conditions where tests
pass on fast machines but fail under load or in CI.

**Core principle:** Wait for the actual condition you care about, not a guess about how long it
takes.

## When to Use

- Tests have arbitrary delays (`setTimeout`, `sleep`, `time.sleep()`)
- Tests are flaky (pass sometimes, fail under load)
- Tests timeout when run in parallel
- Waiting for async operations to complete

**Don't use when:**

- Testing actual timing behavior (debounce, throttle intervals)
- Always document WHY if using arbitrary timeout

## Core Pattern

```typescript
// BAD: Guessing at timing
await new Promise(r => setTimeout(r, 50));
const result = getResult();
expect(result).toBeDefined();

// GOOD: Waiting for condition
await waitFor(() => getResult() !== undefined);
const result = getResult();
expect(result).toBeDefined();
```

## Quick Patterns

| Scenario | Pattern |
| --- | --- |
| Wait for event | `waitFor(() => events.find(...))` |
| Wait for state | `waitFor(() => machine.state === 'ready')` |
| Wait for count | `waitFor(() => items.length >= 5)` |
| Wait for file | `waitFor(() => fs.existsSync(path))` |
| Complex | `waitFor(() => obj.ready && obj.value > 10)` |

## Implementation

Generic polling function:

```typescript
async function waitFor<T>(
  condition: () => T | undefined | null | false,
  description: string,
  timeoutMs = 5000,
): Promise<T> {
  const startTime = Date.now();
  while (true) {
    const result = condition();
    if (result) return result;
    if (Date.now() - startTime > timeoutMs) {
      throw new Error(
        `Timeout waiting for ${description}`
        + ` after ${timeoutMs}ms`,
      );
    }
    // Poll every 10ms
    await new Promise(r => setTimeout(r, 10));
  }
}
```

See `condition-based-waiting-example.ts` in this directory for complete implementation with
domain-specific helpers (`waitForEvent`, `waitForEventCount`, `waitForEventMatch`).

## Common Mistakes

- **Polling too fast:** `setTimeout(check, 1)` wastes CPU. Poll every 10ms.
- **No timeout:** Loop forever if condition never met. Always include timeout with clear error.
- **Stale data:** Caching state before loop. Call getter inside loop for fresh data.

## When Arbitrary Timeout IS Correct

```typescript
// Tool ticks every 100ms — need 2 ticks for partial output
await waitForEvent(manager, 'TOOL_STARTED');
// 200ms = 2 ticks at 100ms intervals — documented
await new Promise(r => setTimeout(r, 200));
```

Requirements:

1. First wait for triggering condition
2. Based on known timing (not guessing)
3. Comment explaining WHY
