# Python Infrastructure — Detailed Patterns

## Packaging Layouts

Use `src/` layout for libraries and packages that other projects install.

```text
project/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── mypackage/
│       ├── __init__.py
│       ├── cli.py
│       └── py.typed
└── tests/
```

Applications can use a flatter layout when packaging boundaries are less important, but the public
module surface should still be explicit.

## pyproject.toml Patterns

Use `pyproject.toml` as the single source of truth for packaging and tool configuration.

```toml
[build-system]
requires = ["uv_build>=0.12,<0.13"]
build-backend = "uv_build"

[project]
name = "mypackage"
version = "0.1.0"
readme = "README.md"
requires-python = ">=3.14"
dependencies = ["httpx>=0.28"]

[project.optional-dependencies]
postgres = ["psycopg[binary]>=3.2"]

[dependency-groups]
dev = [
    "ruff", "pyright", "ty",
    "pytest", "pytest-cov", "pytest-html", "pytest-metadata", "pytest-sugar", "pytest-xdist",
]

[tool.uv]
default-groups = ["dev"]
```

- Extras are for downstream consumers.
- Dependency groups are for maintainers and contributors.

## Strict Application Example

For an application or service that wants stricter project tooling, use a fuller layout like this
and then trim the repo-specific parts.

```toml
[build-system]
requires = ["uv_build>=0.12,<0.13"]
build-backend = "uv_build"

[project]
name = "myproject"
version = "0.1.0"
description = "Application description"
readme = "README.md"
requires-python = ">=3.14"
keywords = ["domain", "service", "application"]
authors = [{ name = "Your Name", email = "you@example.com" }]
license = { text = "MIT" }
dependencies = [
    "fastapi",
    "pydantic-settings",
    "requests",
]
classifiers = [
    "Programming Language :: Python :: 3.14",
    "License :: OSI Approved :: MIT License",
    "Operating System :: POSIX :: Linux",
]

[project.urls]
Homepage = "https://github.com/yourname/myproject"

[project.optional-dependencies]
web = [
    "fastapi",
    "pydantic-settings",
    "uvicorn[standard]",
]

[dependency-groups]
dev = [
    "httpx",
    "pyright",
    "pytest",
    "pytest-cov",
    "pytest-html",
    "pytest-metadata",
    "pytest-sugar",
    "pytest-xdist",
    "ruff",
    "ty",
]

[tool.uv]
default-groups = ["dev"]
required-version = ">=0.11.21"

[tool.ruff]
line-length = 100
target-version = "py314"
src = ["src", "tests"]
extend-exclude = [
    ".venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    "build",
    "dist",
]

[tool.ruff.lint]
select = ["ALL"]
ignore = ["COM812", "CPY001", "D203", "D213"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"tests/**" = [
    "ANN", "ARG001", "ARG002", "D", "INP001", "PLC0415", "PLR2004", "S101", "S105", "S106",
    "SLF001",
]

[tool.ruff.lint.isort]
known-first-party = ["myproject"]

[tool.ruff.format]
docstring-code-format = true

[tool.ty.environment]
python = ".venv"
python-version = "3.14"

[tool.ty.src]
include = ["src", "scripts", "tests"]

[tool.pyright]
pythonVersion = "3.14"
typeCheckingMode = "strict"
venvPath = "."
venv = ".venv"
pythonPlatform = "Linux"
exclude = ["**/__pycache__", "**/.*", ".venv", "web"]
# Tests may call private helpers directly.
executionEnvironments = [
    { root = "tests", extraPaths = ["."], reportPrivateUsage = false },
    { root = "." },
]
# Some dependencies ship without stubs.
reportMissingTypeStubs = false

[tool.pytest.ini_options]
minversion = "9.0"
testpaths = ["tests"]
addopts = [
    "-ra",
    "--strict-markers",
    "--cov=myproject",
    "--cov-report=term-missing",
]
# Warnings fail tests; silence a third-party module only by name, with a reason.
filterwarnings = ["error"]
# Only when tests import shared helpers as `tests.*`.
pythonpath = ["."]

[tool.coverage.run]
branch = true
source = ["myproject"]

[tool.coverage.report]
fail_under = 90
show_missing = true
skip_empty = true
exclude_lines = ["pragma: no cover", "if __name__ == \"__main__\":"]
```

Keep the durable ideas and adapt the repo-specific pieces:

- Keep the build backend, lockfile, Ruff, Pyright, Ty, pytest, and coverage structure.
- Rename packages, groups, paths, and optional extras for the actual project.
- Add custom excludes and per-file ignores only when the repo has a real local reason.
- Trim classifiers, dependencies, and URLs that do not teach reusable structure.

## uv Workflows

Use these workflows instead of `uv pip install`-style compatibility commands when the repo is
already uv-native.

```bash
uv add httpx
uv add --group dev ruff pyright ty
uv remove httpx
uv sync
uv lock
uv lock --check
uv export --format requirements-txt > requirements.txt
.venv/bin/pyright
.venv/bin/ty check
.venv/bin/pytest
uv build
```

- Run tools as `.venv/bin/<tool>`: `uv run` re-syncs the environment first and can replace packages
  installed outside the lockfile, such as CUDA or torch builds.
- Regenerate the lock file when dependency constraints change.
- Export `requirements.txt` only when another tool or platform requires it.

## Release Discipline

- Build from a clean tree.
- Verify wheel and sdist installation.
- Run tests, lint, and type checks against the built artifact when practical.
- Publish through the repo's existing CI or release automation instead of one-off manual uploads.

## Profiling Recipes

### CPU Profiling

```bash
python -m cProfile -o output.prof script.py
python -m pstats output.prof
```

### Line Profiling

```bash
kernprof -l -v script.py
```

### Memory Profiling

```bash
python -m memory_profiler script.py
```

### Production Sampling

```bash
py-spy top --pid 12345
py-spy record -o profile.svg --pid 12345
```

## Performance Heuristics

- Fix algorithmic complexity before optimizing syntax.
- Use dicts and sets for repeated membership checks.
- Keep large pipelines lazy with iterators or generators.
- Batch commits and remote calls.
- Prefer local variables in tight loops only after profiling proves the loop matters.
- Use `functools.lru_cache` for pure computations with stable inputs.

## Background Job Design

### Job Lifecycle

Use explicit job states such as `pending`, `running`, `succeeded`, and `failed`.

```python
class JobStatus(StrEnum):
    """Lifecycle state of a background job."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
```

Persist state transitions so operators and callers can see whether a job is queued, stuck, or
failed permanently.

### Idempotency

- Check state before mutating external systems.
- Use idempotency keys for payment, email, or webhook providers.
- Design retries so replaying the same task is safe.

### Dead-Letter Handling

Send permanently failed jobs to a dead-letter queue or manual inspection table after exhausting
retries.

### Status Endpoints

Expose job lookup endpoints or webhook callbacks when external clients need completion status.

## Choosing a Queue

- Use Celery when you need mature orchestration, scheduling, or ecosystem integration.
- Use Dramatiq when you want a simpler interface with retry support.
- Use RQ for lightweight Redis-backed worker setups.
- Use cloud-managed queues when operational simplicity or cross-service integration matters more
  than Python-native ergonomics.
