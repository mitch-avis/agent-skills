---
name: code-review
description: >-
  Comprehensive code review methodology covering correctness, security, performance,
  maintainability, tests, and design. Includes a phased workflow, severity rubric (P0–P3),
  per-dimension checklists, structured output template, feedback patterns, and PR-size guidance.
  Use when reviewing pull requests, auditing local git changes, conducting security or
  performance audits, mentoring through review, or establishing review standards for a team.
---

# Code Review

Perform thorough, constructive code reviews that catch real issues without bikeshedding. Default to
review-only output unless the user explicitly asks to implement the suggested changes.

## When to Use

- Reviewing a pull request (local branch, staged diff, or remote PR by URL/number)
- Auditing local working-tree changes before commit or merge
- Performing a security or performance audit on a specific module
- Mentoring or providing structured feedback on someone else's code
- Establishing review standards or checklists for a team
- After completing a major feature, before requesting human review

## Workflow

### Phase 1 — Determine Target and Gather Context

Identify what to review:

- **Remote PR** (URL or `#123`): `gh pr checkout <number>`, then read PR description and existing
  comments
- **Local changes**: `git status -sb`, `git diff` (working tree), `git diff --staged`
- **Commit range**: `git diff <base>..<head>` and `git log <base>..<head> --oneline`

Then orient:

- Read the PR/commit description and any linked issue
- Note PR size with `git diff --stat`
- Check CI status if available
- Identify entry points and critical paths (auth, payments, data writes, network boundaries)

**Checkpoint:** Summarize the change's intent in one sentence before proceeding. If you cannot, ask
the author to clarify rather than guessing.

**Edge cases:**

- **No changes:** Inform the user and ask whether to review staged changes, a specific commit range,
  or a different branch.
- **Large diff (>500 lines):** Summarize by file first, then review in batches grouped by module or
  feature. Recommend splitting if the changes are not tightly coupled.
- **Mixed concerns:** Group findings by logical feature, not just file order.

### Phase 2 — High-Level Review

Before line-by-line analysis, evaluate:

1. **Purpose** — Does the change actually do what it claims?
2. **Architecture & design** — Does the solution fit the problem and existing patterns? Are new
   abstractions justified, or is this premature generalization?
3. **File organization** — Are new files in the right layer (controller/service/repository)? Any
   duplication of existing utilities?
4. **Testing strategy** — Are critical paths tested? Do tests assert behavior or just structure?

### Phase 3 — Line-by-Line Analysis

Review across all dimensions in [references/checklists.md](references/checklists.md). Apply the
priority order:

1. **Correctness** — bugs, logic errors, race conditions, off-by-one, null handling
2. **Security** — input validation, auth, injection, secrets, CSRF/XSS/SSRF, deserialization
3. **Performance** — N+1 queries, O(n²) hot paths, unbounded loops, missing indexes, leaks
4. **Tests** — coverage of new behavior, edge cases, error paths; tests assert outcomes
5. **Design** — SOLID, cohesion, coupling, right abstraction level, minimal public surface
6. **Readability** — clear names, no dead code, no magic numbers, reasonable complexity
7. **Style** — automated linters should catch this; do not nitpick

Skip what tools should catch: formatting, import order, lint violations, simple typos.

### Phase 4 — Produce the Report

Use the structured template in [references/output-template.md](references/output-template.md). If
P0/critical issues are found in Phase 3, surface them immediately rather than waiting for the final
summary.

## Severity Rubric

| Level  | Name     | Examples                                                               | Action                       |
| ------ | -------- | ---------------------------------------------------------------------- | ---------------------------- |
| **P0** | Critical | Security vuln, data loss, correctness bug, breaking change             | Block merge                  |
| **P1** | High     | Logic error, significant SOLID violation, performance regression       | Fix before merge             |
| **P2** | Medium   | Code smell, maintainability issue, missing test coverage               | Fix in PR or open follow-up  |
| **P3** | Low      | Naming, minor refactor, optional improvement                           | Optional / nit               |

## Feedback Patterns

### Be Specific and Actionable

```text
# Bad
"This could be better."

# Good
"This loop iterates the full list for each lookup — consider using a dict for O(1) access
instead of O(n) per call."
```

Show concrete code in suggestions when possible. Explain the *why*, not just the *what*.

### Prefix Comments with Intent

| Prefix        | Meaning                                                |
| ------------- | ------------------------------------------------------ |
| `nit:`        | Minor style/preference — merge without fixing is fine  |
| `suggestion:` | Consider this alternative — not blocking               |
| `question:`   | Seeking understanding — not requesting a change        |
| `blocker:`    | Must fix before merge — explain why                    |

### Approve with Nits

If only minor issues remain, approve and note them as nits. Do not block on style preferences a
linter could enforce.

### Handle Disagreement Gracefully

If the author left a comment explaining a non-obvious choice, acknowledge their reasoning before
suggesting an alternative. Push back on technically wrong feedback with a concrete counter-example
or test, not authority.

## PR Size Guidelines

| Lines Changed | Reviewability                                      |
| ------------- | -------------------------------------------------- |
| < 100         | Easy to review thoroughly                          |
| 100 – 400     | Reasonable — split if logically separable          |
| 400 – 800     | Large — request splitting unless tightly coupled   |
| > 800         | Too large — almost certainly needs splitting       |

## Output Format

See [references/output-template.md](references/output-template.md) for the full report template,
including summary, findings grouped by severity, strengths, and verdict.

## Anti-Patterns

- **Rubber-stamping** — "LGTM" without reading the code is not a review
- **Style bikeshedding** — configure linters; stop debating formatting in comments
- **Rewrite requests** — suggest incremental improvements, not "I would have done it differently"
- **Drive-by reviews** — if you comment, follow through on the conversation
- **Blocking on personal preference** — distinguish must-fix from nice-to-have
- **Showing off** — review serves the code and the author, not the reviewer's ego
- **Ignoring positives** — acknowledge what was done well; reviews are also for knowledge sharing

## Reference Files

| Topic                    | File                                                          | Load When                                |
| ------------------------ | ------------------------------------------------------------- | ---------------------------------------- |
| Per-dimension checklists | [references/checklists.md](references/checklists.md)          | During Phase 3 line-by-line review       |
| Output template          | [references/output-template.md](references/output-template.md)| When writing the final review report     |
| Common issue patterns    | [references/common-issues.md](references/common-issues.md)    | When you spot N+1, magic numbers, smells |
