# Python Modernization — Migration Patterns

## Migrating from requirements.txt

Use `uv init --bare` in an existing repo, then move runtime and dev dependencies into
`pyproject.toml` through `uv add`.

```bash
uv init --bare
uv add requests rich
uv add --group dev ruff pyright pytest pytest-cov
uv sync
uv lock
```

- Review version pins rather than importing them blindly.
- Export `requirements.txt` afterward only if another deployment tool still requires it.

## Migrating from Poetry

- Keep the project structure intact first.
- Move dependency management to `uv`.
- Preserve package metadata in `pyproject.toml`.
- Replace Poetry-specific commands in CI with `uv sync`, `uv run`, and `uv build`.

## Collapsing Formatter Stacks

Replace Black, isort, and flake8 combinations with Ruff when the repo does not need old tool
compatibility.

```bash
uv add --group dev ruff
uv run ruff check --fix .
uv run ruff format .
```

## Typing Migration

- Start with `pyright` in standard mode.
- Fix import and optional issues first.
- Tighten diagnostics gradually.
- Run `ty` only where the repo already expects it.

## PEP 723 Scripts

Use inline metadata for standalone tools instead of creating a whole project for a single file.

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx", "rich"]
# ///
```

## Dependency Groups and Extras

- Use dependency groups for contributor tooling such as lint, test, docs, and audit.
- Use optional dependencies for runtime features installed by downstream users.

## CI Migration

- Install `uv` first.
- Pin or declare the Python version explicitly.
- Use `uv sync` for deterministic environment creation.
- Run `uv run ...` for format, lint, type-check, and test steps.
