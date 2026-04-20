---
name: committing-code
description: >-
  Creates high-quality git commits using Conventional Commits. Reviews working tree, splits mixed
  changes into logical commits, stages selectively with patch mode, writes descriptive commit
  messages, and verifies before finalizing. Use when the user asks to commit, write a commit
  message, stage changes, or split work into multiple commits.
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
- Production code vs tests
- Formatting/style vs logic
- Backend vs frontend
- Dependency bumps vs behavior changes

If unrelated changes exist in the same file, use patch staging in step 3.

### 3. Stage Selectively

```bash
# Specific files
git add path/to/file

# Interactive hunk selection (preferred for mixed changes)
git add -p

# Unstage mistakes
git restore --staged <path>
git restore --staged -p   # unstage specific hunks
```

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

### 5. Describe Before Writing

Summarize what changed and why in 1-2 sentences. If you cannot describe the change cleanly, it is
probably too broad — go back to step 2 and split further.

### 6. Write the Commit Message

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

- Subject line: imperative mood, under 72 characters
- Body: explain what and why, not how
- Footer: issue references, `BREAKING CHANGE:` if applicable
- Prefer `git commit -v` for multi-line messages (shows diff in editor)

### 7. Verify

Run the repo's fastest meaningful check before moving on:

```bash
# Examples — use whatever the project provides
make test        # or: pytest, cargo test, npm test
make lint        # or: ruff check, eslint, clippy
```

If verification fails, amend the commit or fix and create a new commit.

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

After committing, provide:

- The commit message(s) used
- A one-line summary per commit (what/why)
- Commands used to stage and review (`git diff --cached` at minimum)
- Test or lint results if verification was run

## Related Skills

- [code-review](../code-review/SKILL.md) — review the diff before committing
