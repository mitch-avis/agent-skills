# Output Template

Use this structure when producing a code review report. Adapt sections to context — omit empty
severity buckets rather than padding with "(none)".

## Full Template

```markdown
# Code Review: <PR title or scope>

## Summary

<1–2 sentence overview of the change and overall assessment>

**Files reviewed:** X files, Y lines changed
**Verdict:** Approve / Request Changes / Needs Discussion

---

## Findings

### P0 — Critical

1. **<file>:<line> — <short title>**
   - **Issue:** <what is wrong>
   - **Impact:** <why it matters>
   - **Fix:**
     ```<lang>
     <suggested code>
     ```

### P1 — High

2. **<file>:<line> — <short title>**
   - ...

### P2 — Medium

3. ...

### P3 — Low / Nits

4. ...

---

## What Looks Good

- <Specific positive observation>
- <Another>

## Suggested Follow-ups

- <Non-blocking items worth tracking as separate work>
```

## Inline Comment Format

For comments left directly on lines:

```text
[severity] [category] <message>

Example: [P1] [security] User input flows into this query without parameterization.
Use `db.execute(sql, (user_id,))` instead.
```

## Quick Summary Format

For small changes (<100 lines) where a full report is overkill:

```markdown
**Verdict:** Approve with nits

- [P3] `foo.py:42` — consider renaming `tmp` to `parsed_payload`
- [P3] `bar.py:88` — magic number `7` could be a named constant

Nice cleanup of the error handling in `service.py`.
```

## Verdict Guidelines

- **Approve** — No P0/P1 issues. Minor suggestions are fine to defer.
- **Approve with nits** — Only P3 issues; author may merge without addressing.
- **Request Changes** — One or more P0/P1 issues, or multiple P2 issues that compound.
- **Needs Discussion** — Architectural concerns or scope questions that require author input before
  a clear verdict is possible.
