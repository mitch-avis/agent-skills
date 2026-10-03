---
name: committing-code
description: >-
  Use before staging or committing anything, or when asked to write a commit message or split work
  into logical commits, even if the skill isn't named. Covers commit boundaries, selective (patch)
  staging, running the checks before committing, and Conventional Commits messages.
---

# Committing Code

Create commits that are easy to review, safe to bisect, and clear in intent.

## Workflow

### 1. Inspect

```bash
git status
git diff --stat
git diff            # unstaged changes
git diff --cached   # already staged changes
```

### 2. Plan Commit Boundaries

Each commit should contain one logical change. Split when changes cross these boundaries:

- Feature vs refactor
- Formatting/style vs logic
- Dependency bumps vs behavior changes

Tests ship in the same commit as the code they cover, so every commit builds and passes on its
own. A test-only commit (`test:`) is for tests added to code that already exists.

If unrelated changes exist in the same file, use patch staging in step 3.

### 3. Stage Selectively

<!-- check-examples: skip -->

```bash
# Specific files
git add path/to/file

# Interactive hunk selection (preferred for mixed changes in a terminal)
git add -p

# Unstage mistakes
git restore --staged <path>
git restore --staged -p   # unstage specific hunks
```

`git add -p` and `git restore --staged -p` need an interactive terminal. Agents and scripts stage
hunks through a patch file instead:

```bash
# Stage some hunks: write the diff, delete the unwanted hunks (keep the file headers), apply it
git diff -- path/to/file > /path/to/tmp/hunks.patch
git apply --cached --recount /path/to/tmp/hunks.patch

# Unstage some hunks: keep only the hunks to remove, then reverse-apply them to the index
git diff --cached -- path/to/file > /path/to/tmp/staged.patch
git apply --cached --reverse --recount /path/to/tmp/staged.patch
```

Write the patch outside the repo, or delete it before committing.

Never use `git add .` or `git add -A` without reviewing first.

### 4. Review Staged Changes

```bash
git diff --cached
```

Verify:

- No secrets, tokens, or credentials
- No debug logging or leftover print statements
- No unrelated formatting churn
- Only changes for the intended commit

### 5. Run the Checks

Run the repo's gate before committing: its gate script if it has one (for example
`scripts/gate.sh`), otherwise the formatter, linters, type checkers, and tests for what changed.
Fix failures, re-stage, and re-review. Commit hooks may run more checks; if one fails, fix the
cause rather than bypassing it.

### 6. Describe Before Writing

Summarize what changed and why in 1-2 sentences. If you cannot describe the change cleanly, it is
probably too broad — go back to step 2 and split further.

### 7. Write the Commit Message

Use Conventional Commits format. See
[references/conventional-commits.md](references/conventional-commits.md) for the full type table,
breaking change syntax, and examples.

```text
type(scope): short imperative summary

What changed.
Why it changed.

Refs #123
```

Rules:

- Subject line: lowercase imperative summary, at most 72 characters, no trailing period
- Type matches the change: test-only commits are `test`, not `feat(tests)`; dependency refreshes
  are `chore: update deps`
- Body: explain what and why, not how
- Footer: issue references, `BREAKING CHANGE:` if applicable
- Prefer `git commit -v` for multi-line messages in a terminal (shows diff in editor); without an
  editor, write the message to a file and use `git commit -F <file>`, or pass the subject and body
  as separate `-m` arguments

If something in the commit you just made needs fixing and it hasn't been pushed, amend it with
`git commit --amend`. Once a commit is pushed, fix forward with a new commit instead.

### 8. Repeat

Return to step 1 for the next logical commit. Continue until the working tree is clean or all
intended changes are committed.

## Safety Rules

- **Never** force-push to main/master without explicit user request
- **Never** run `git reset --hard` without explicit user request
- **Never** skip hooks (`--no-verify`) unless the user asks
- **Never** update git config
- **Never** commit secrets, tokens, private keys, or `.env` files
- If a commit hook fails, fix the issue — do not bypass the hook

## Deliverable

After committing, report briefly:

- Each commit's short hash and subject
- The gate results (passed, failed with the key error, or not run with the reason)
- Anything left uncommitted, and why

## Related Skills

- [code-review](../code-review/SKILL.md) — review the diff before committing
