---
name: python-modernization
description: >-
  Modernizes Python projects with uv, ruff, pyright, ty, lockfiles, dependency groups, and PEP
  723 scripts. Use when bootstrapping a new Python project or migrating from pip, Poetry,
  requirements files, Black, isort, or mypy to a cleaner modern workflow.
---

# Python Modernization

Use this skill when the job is not just writing Python, but upgrading the project's workflow.

## Modern Defaults

- Use `uv` for Python versions, environments, dependencies, syncing, and locking.
- Use `ruff` for formatting and linting.
- Use `pyright` and `ty` together in modern Python projects.
- Keep `pyright` as the stable baseline until `ty` is mature enough to replace it for the repo.
- Keep project configuration in `pyproject.toml`.
- Use PEP 723 metadata for standalone scripts.

## Decision Rules

- New script with dependencies -> use a PEP 723 script.
- New application or CLI -> use `uv init --build-backend uv` and commit `uv.lock`.
- New library or package -> use `src/` layout and the `uv_build` backend.
- Legacy repo using pip, Poetry, Black, isort, or mypy -> migrate incrementally, keeping behavior
  stable while the tooling changes.

## Baseline Workflow

```bash
uv init --build-backend uv --python 3.14 myproject
cd myproject
uv add httpx
uv add --group dev ruff pyright ty pytest pytest-cov pytest-xdist
uv sync
uv lock --check
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/pyright
.venv/bin/ty check
.venv/bin/pytest
```

## Migration Principles

- Change one tooling boundary at a time.
- Keep the repo executable after each migration step.
- Prefer importer-safe `src/` layouts for distributable packages.
- Preserve functional behavior while simplifying the workflow.
- Export compatibility files only when another tool still requires them.

## Common Migrations

- `requirements.txt` and ad hoc virtualenvs -> `uv add`, `uv sync`, `uv lock`
- Black + isort + flake8 -> `ruff format` and `ruff check`, tightened to `select = ["ALL"]` once
  the curated rule set passes
- mypy-heavy setups -> `pyright` and `ty`, with gradual diagnostic tightening
- `hatchling` or `setuptools` -> `uv_build` when the package layout allows it
- one-off Python utilities -> PEP 723 scripts

## CI and Release Expectations

- Run `uv sync --frozen` or the repo equivalent in CI.
- Check formatting, linting, types, and tests explicitly.
- Keep Python version selection and lockfile behavior deterministic.

## Detailed Patterns

Detailed migration sequences, script patterns, and modernization tradeoffs live in
`references/migration-patterns.md`.

## Anti-Patterns

- No `uv pip install ...` as the default project workflow when the repo is uv-native.
- No manually edited dependency lists when `uv add` or `uv remove` can do it safely.
- No mixed formatter stacks without a specific compatibility reason.
- No migration that changes project behavior and tooling semantics in one opaque step.

## Related Skills

- [python](../python/SKILL.md) — core project defaults once modernization is complete
- [python-infrastructure](../python-infrastructure/SKILL.md) — packaging, lockfiles, workers, and
  release mechanics
- [python-type-safety](../python-type-safety/SKILL.md) — tightening type safety during migration
- [python-configuration](../python-configuration/SKILL.md) — modernizing settings and env handling
