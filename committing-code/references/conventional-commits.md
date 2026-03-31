# Conventional Commits Reference

Format: `type(scope): description`

## Types

| Type       | Purpose                                               |
| ---------- | ----------------------------------------------------- |
| `feat`     | New feature or capability                             |
| `fix`      | Bug fix                                               |
| `docs`     | Documentation only                                    |
| `style`    | Formatting, whitespace, semicolons (no logic change)  |
| `refactor` | Code restructuring (no feature, no fix)               |
| `perf`     | Performance improvement                               |
| `test`     | Add or update tests                                   |
| `build`    | Build system or dependency changes                    |
| `ci`       | CI configuration and scripts                          |
| `chore`    | Maintenance, tooling, or other non-production changes |
| `revert`   | Revert a previous commit                              |

## Subject Line

- Imperative mood: "add", not "added" or "adds"
- Under 72 characters
- No trailing period
- Lowercase after the colon

```text
feat(auth): add JWT token refresh endpoint
fix(parser): handle empty input without panic
docs: update contributing guide with commit conventions
```

## Scope

Optional parenthesized noun describing the section of the codebase:

```text
feat(api): ...
fix(auth): ...
refactor(db): ...
```

Omit the scope when the change is cross-cutting or the project has no clear modules.

## Body

Separated from the subject by a blank line. Explain what changed and why — not a line-by-line
implementation diary.

```text
fix(cache): return stale entry when upstream is unavailable

Previously the cache would propagate the upstream 503 to callers.
Now it serves the stale entry with a warning header, matching the
behavior described in RFC 5861.
```

## Breaking Changes

Two ways to signal a breaking change (use one or both):

```text
# Exclamation mark in the header
feat!: remove deprecated /v1 endpoint

# BREAKING CHANGE footer
feat(api): change pagination to cursor-based

BREAKING CHANGE: `offset` parameter removed; use `cursor` instead.
```

## Issue References

Use footers to link issues:

```text
feat(billing): add proration for mid-cycle upgrades

Closes #456
Refs #400, #412
```

## Multi-Line Commit Command

```bash
# Prefer editor mode for multi-line messages
git commit -v

# Or heredoc for scripted commits
git commit -m "$(cat <<'EOF'
type(scope): summary

Body text.

Footer
EOF
)"
```

## Specification

Full spec: <https://www.conventionalcommits.org/en/v1.0.0/>
