# Agent Skills

Personal skill collection. Each skill is a directory with a `SKILL.md` entry point plus optional
`references/`, `templates/`, and `scripts/`. Claude Code loads skills only from `~/.claude/skills/`,
so each skill is symlinked there; other agents read this directory directly. Python tooling for
the repo (the example checker and its tests) lives in `scripts/` and `tests/`.

## Setup

```bash
uv sync
```

## Gates

Run before every commit. The example checker extracts the `python` and `bash` code blocks from
every skill and runs ruff (house rules, see `scripts/examples-ruff.toml`) and ShellCheck on them.

```bash
markdownlint-cli2 "**/*.md"
.venv/bin/python scripts/check_examples.py
```

When `scripts/` or `tests/` change, also run:

```bash
.venv/bin/ruff format . && .venv/bin/ruff check .
.venv/bin/pyright && .venv/bin/ty check
.venv/bin/pytest
```

## Adding a Skill

1. Create `<name>/SKILL.md` with `name` equal to the directory name and a `description` that
   starts with when to use it (at most 1024 characters). Put triggers in the description, not in
   a "When to Use" body section, because the body loads only after the description matched.
2. Link it for Claude Code: `ln -s ~/.agents/skills/<name> ~/.claude/skills/<name>`.
3. Add a row to the matching table in `README.md`, and an attribution row under "Source
   Repositories" if it derives from an upstream skill.
4. If it should load for a file type or task, add a line to the matching
   `~/.claude/rules/skills-*.md` file (outside this repo).

## Removing a Skill

`git rm -r` the directory, then remove its README rows and attribution, its symlink in
`~/.claude/skills/`, its lines in `~/.claude/rules/`, and its bare key in the `skillOverrides` of
`~/.claude/settings.json`. Keep an `anthropic-skills:<name>` override while a claude.ai copy of the
skill exists; removing it makes that copy load. Finish with `grep -rn '<name>' . ~/.claude/rules`.

## Writing Style

- State rules at normal volume with the reason beside them; keep "never" for hard constraints.
  Avoid all-caps emphasis and instructions to delete or discard work.
- Fill prose to 100 columns.
- Code examples must pass the house gates. Mark deliberate bad-practice samples and command
  listings with `<placeholder>` arguments with `<!-- check-examples: skip -->` on the line before
  the fence.
- Pin image, action, and tool versions in examples to releases verified when you write them.
- Test examples follow Arrange-Act-Assert with labeled phases.

## Commits

Conventional Commits, with the skill name as the scope (`docs(rust): ...`). One logical change
per commit.
