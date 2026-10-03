# Python Modernization — Migration Patterns

## Migrating from requirements.txt

Use `uv init --bare` in an existing repo, then move runtime and dev dependencies into
`pyproject.toml` through `uv add`.

```bash
uv init --bare
uv add requests rich
uv add --group dev ruff pyright ty pytest pytest-cov
uv sync
uv lock
```

- Review version pins rather than importing them blindly.
- Export `requirements.txt` afterward only if another deployment tool still requires it.

## Migrating from Poetry

- Keep the project structure intact first.
- Move dependency management to `uv`.
- Preserve package metadata in `pyproject.toml`.
- Replace Poetry-specific commands in CI with `uv sync --locked`, `.venv/bin/<tool>`, and
  `uv build`.

## Collapsing Formatter Stacks

Replace Black, isort, and flake8 combinations with Ruff when the repo does not need old tool
compatibility.

```bash
uv add --group dev ruff
.venv/bin/ruff check --fix .
.venv/bin/ruff format .
```

## Typing Migration

- Start a legacy repo in `pyright` standard mode, fix import and optional issues first, then
  tighten package by package with `strict = ["<package>"]`.
- Add `ty` alongside `pyright` and keep both at 0 errors.

## PEP 723 Scripts

Use inline metadata for standalone tools instead of creating a whole project for a single file.

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["httpx", "rich"]
# ///
```

## Dependency Groups and Extras

- Put contributor tooling (lint, type checking, tests) in the `dev` dependency group.
- Use optional dependencies for runtime features installed by downstream users.

## CI Migration

- Install `uv` first.
- Pin or declare the Python version explicitly.
- Run `uv sync --locked` once; it fails if `uv.lock` is out of date.
- Run format, lint, type-check, and test steps as `.venv/bin/<tool>`, the same form used locally.
