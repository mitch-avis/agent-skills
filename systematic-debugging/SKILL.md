---
name: systematic-debugging
description: >-
  Systematic four-phase root-cause-analysis methodology for any bug, test failure, performance
  regression, build break, or unexpected behaviour. Covers reproduction, evidence gathering,
  differential debugging, hypothesis testing, git bisect, defense-in-depth validation,
  condition-based waiting, and the 3-fix architectural escape hatch. Includes language-specific
  toolkits for Python (pytest, traceback, py-spy) and Rust (RUST_BACKTRACE, dbg!, miri,
  sanitizers, tokio-console, cargo bisect-rustc, flamegraph). USE BEFORE proposing any fix —
  even for "obvious" or "simple" bugs, under time pressure, or after a previous fix failed. DO
  NOT use for greenfield design work, code review without a reported bug, refactoring without a
  failure, or general Q&A about how a library works.
---

# Systematic Debugging

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

## The Iron Law

```text
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue: test failures, production bugs, unexpected behavior, performance
problems, build failures, integration issues.

**Use ESPECIALLY when:**

- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**

- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (systematic is faster than thrashing)

## The Four Phases

Complete each phase before proceeding to the next.

### Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

1. **Read Error Messages Carefully**
   - Don't skip past errors or warnings
   - Read stack traces completely
   - Note line numbers, file paths, error codes

2. **Reproduce Consistently**
   - Can you trigger it reliably? What are the exact steps?
   - If not reproducible, gather more data — don't guess
   - Create a minimal reproduction (smallest failing example)

3. **Check Recent Changes**
   - Git diff, recent commits
   - New dependencies, config changes
   - Environmental differences

4. **Gather Evidence in Multi-Component Systems**

   When the system has multiple components, add diagnostic instrumentation BEFORE proposing fixes:

   ```bash
   # Log at each component boundary
   # Layer 1: Entry point
   echo "=== Input data: ==="
   # Layer 2: Processing
   echo "=== State after processing: ==="
   # Layer 3: Output
   echo "=== Final result: ==="
   ```

   Run once to gather evidence showing WHERE it breaks. Then analyze evidence to identify the
   failing component. Then investigate that specific component.

5. **Trace Data Flow**

   See [root-cause-tracing.md](references/root-cause-tracing.md) for the complete backward tracing
   technique.

   Quick version: Where does the bad value originate? What called this with that bad value? Keep
   tracing up until you find the source. Fix at source, not at symptom.

### Phase 2: Pattern Analysis

1. **Find Working Examples** — locate similar working code in the same codebase
2. **Compare Against References** — read reference implementations COMPLETELY, don't skim
3. **Identify Differences** — list every difference between working and broken, however small
4. **Understand Dependencies** — what components, settings, config, or environment does this need?

#### Differential Debugging

Build a comparison table:

| Aspect | Working | Broken |
| --- | --- | --- |
| Environment | Development | Production |
| Runtime version | 1.85 | 1.82 |
| Data | Empty DB | 1M records |
| User | Admin | Regular user |
| Time | During day | After midnight |

The difference often points directly to the root cause.

#### Git Bisect

When you know a regression exists but not which commit:

```bash
git bisect start
git bisect bad                 # current commit is broken
git bisect good v1.0.0         # this version was fine
# Git checks out middle commit — test it, then:
git bisect good   # if it works
git bisect bad    # if it's broken
# Continue until the culprit commit is found
git bisect reset  # when done
```

### Phase 3: Hypothesis and Testing

1. **Form Single Hypothesis** — state clearly: "I think X is the root cause because Y." Be specific,
   not vague.
2. **Test Minimally** — make the SMALLEST possible change to test the hypothesis. One variable at a
   time. Don't fix multiple things at once.
3. **Verify Before Continuing** — did it work? Yes → Phase 4. No → form a NEW hypothesis. Don't
   stack fixes.
4. **When You Don't Know** — say "I don't understand X." Don't pretend. Research more.

### Phase 4: Implementation

1. **Create Failing Test Case** — simplest possible reproduction. Automated test if possible. MUST
   exist before fixing. Use the **test-driven-development** skill.
2. **Implement Single Fix** — address the root cause. ONE change at a time. No "while I'm here"
   improvements.
3. **Verify Fix** — test passes now? No other tests broken? Issue actually resolved?
4. **If Fix Doesn't Work** — STOP. Count how many fixes you've tried. If < 3: return to Phase 1 with
   new information.
5. **If 3+ Fixes Failed: Question Architecture** — each fix revealing new problems in different
   places indicates an architectural issue, not a bug. Stop fixing symptoms and discuss fundamentals
   with your human partner.

## Debugging by Issue Type

### Intermittent / Flaky Bugs

- Add extensive logging (timing, state transitions, external interactions)
- Look for race conditions (concurrent access, async ordering, missing synchronization)
- Check timing dependencies (timeouts, promise resolution order)
- Stress test (run many times, vary timing, simulate load)
- See [condition-based-waiting.md](references/condition-based-waiting.md) for replacing arbitrary
  sleeps with condition polling

### Performance Issues

- **Profile first** — don't optimize blindly. Measure before and after.
- Common culprits: N+1 queries, unnecessary re-renders, large data processing, synchronous I/O in
  async code
- Rust: `cargo flamegraph`, `samply`, `criterion` — see
  [rust-debugging.md](references/rust-debugging.md) § "Profiling Hot Paths"
- Python: `cProfile`, `line_profiler`, `py-spy`

### Production Bugs

- Gather evidence from error tracking, logs, user reports, metrics
- Reproduce locally with production-like data
- Don't change production — use feature flags, staging
- Add monitoring/logging for future investigation

## After the Fix

Once root cause is fixed, add defense-in-depth validation. See
[defense-in-depth.md](references/defense-in-depth.md) for the four-layer pattern: entry validation,
business logic validation, environment guards, and debug instrumentation.

## Red Flags — STOP and Follow Process

If you catch yourself thinking any of these, return to Phase 1:

- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "One more fix attempt" (when already tried 2+)

## Common Rationalizations

| Excuse | Reality |
| --- | --- |
| "Issue is simple, skip process" | Simple issues have root causes too |
| "Emergency, no time" | Systematic debugging is FASTER than thrashing |
| "Just try this first" | First fix sets the pattern — do it right |
| "I'll write test after fix works" | Untested fixes don't stick |
| "Multiple fixes at once saves time" | Can't isolate what worked |
| "Reference too long, I'll adapt" | Partial understanding guarantees bugs |
| "One more attempt" (after 2+ fails) | 3+ failures = architectural problem |

## Quick Reference

| Phase | Key Activities | Done When |
| --- | --- | --- |
| 1. Root Cause | Read errors, reproduce, trace data | Understand WHAT and WHY |
| 2. Pattern | Find working examples, diff, bisect | Differences identified |
| 3. Hypothesis | Form theory, test minimally | Confirmed or new hypothesis |
| 4. Implementation | Create test, fix, verify | Bug resolved, tests pass |

## Supporting Techniques

Reference files in this directory:

| Reference | Purpose |
| --- | --- |
| [root-cause-tracing.md](references/root-cause-tracing.md) | Trace bugs backward through the call stack to the original trigger (Python + Rust examples) |
| [defense-in-depth.md](references/defense-in-depth.md) | Add validation at four layers after finding root cause (Python + Rust examples, plus Rust newtype patterns) |
| [condition-based-waiting.md](references/condition-based-waiting.md) | Replace arbitrary `sleep`/`time.sleep`/`thread::sleep` with condition polling |
| [condition_based_waiting_example.py](references/condition_based_waiting_example.py) | Python reference implementation (sync + async via asyncio) |
| [condition_based_waiting_example.rs](references/condition_based_waiting_example.rs) | Rust reference implementation (sync + async via Tokio) |
| [rust-debugging.md](references/rust-debugging.md) | Rust toolkit — backtraces, `dbg!`, test isolation, Miri, sanitizers, `tokio-console`, `cargo bisect-rustc`, flamegraph |
| [find-polluter.sh](references/find-polluter.sh) | Bisect helper for tests that pass in isolation but fail in suite (works with `pytest`, `cargo test`, `go test`, etc.) |
