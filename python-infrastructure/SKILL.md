---
name: python-infrastructure
description: >-
  Use before changing Python project tooling: pyproject.toml, dependency groups, uv lockfiles,
  packaging and builds, release steps, profiling, or background job and queue workers. Covers uv
  workflows, strict project configuration, and performance profiling.
---

# Python Infrastructure

Use this skill for the mechanics around Python projects after the language basics are settled:
environments, packaging, performance, workers, release flows, and reproducibility.

## Core Responsibilities

- Manage Python versions, virtual environments, dependencies, and lock files with `uv`.
- Define packaging metadata and build configuration in `pyproject.toml`.
- Profile before optimizing.
- Design job queues and worker processes for long-running or unreliable work.
- Keep CI and release flows reproducible.

## Environment and Dependency Management

Use `uv` as the control plane for Python project tooling.

```bash
uv python install 3.14
uv init --build-backend uv --python 3.14 mypackage
uv add fastapi
uv add --group dev ruff pyright ty pytest pytest-cov pytest-html pytest-metadata pytest-sugar pytest-xdist
uv sync
uv lock --check
.venv/bin/pytest
.venv/bin/ty check
uv build
```

- Prefer `uv add` and `uv remove` over manual dependency edits.
- Put dev tooling in a single `dev` dependency group with `default-groups = ["dev"]`.
- Use `[project.optional-dependencies]` only for optional runtime extras that downstream consumers
  install.
- Commit `uv.lock` for applications, services, and CLIs where reproducible deploys matter.
- For libraries, follow repo policy on whether contributor reproducibility outweighs the extra file.

## Packaging and Distribution

Prefer `src/` layout for packages and libraries.

```toml
[build-system]
requires = ["uv_build>=0.12,<0.13"]
build-backend = "uv_build"

[project]
name = "mypackage"
version = "0.1.0"
description = "What it does"
readme = "README.md"
requires-python = ">=3.14"
dependencies = []

[project.optional-dependencies]
postgres = ["psycopg[binary]>=3.2"]

[project.scripts]
mycli = "mypackage.cli:main"

[dependency-groups]
dev = [
    "ruff", "pyright", "ty",
    "pytest", "pytest-cov", "pytest-html", "pytest-metadata", "pytest-sugar", "pytest-xdist",
]

[tool.uv]
default-groups = ["dev"]
required-version = ">=0.11.21"

[tool.ruff]
line-length = 100
target-version = "py314"

[tool.ruff.lint]
select = ["ALL"]
ignore = ["COM812", "CPY001", "D203", "D213"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.pyright]
pythonVersion = "3.14"
typeCheckingMode = "strict"
venvPath = "."
venv = ".venv"

[tool.ty.environment]
python = ".venv"
[tool.ty.src]
include = ["src", "tests"]
```

`uv_build` finds `src/mypackage` from the project name; set `[tool.uv.build-backend]`
`module-name` or `module-root` only when the layout differs.

- Include `py.typed` in typed packages.
- Define CLI entry points in `[project.scripts]`.
- Build with `uv build` and publish using the repo's existing release process.
- Test installation from built artifacts before cutting releases.

## Performance Work

Profile first, then optimize the verified hot path.

```bash
.venv/bin/python -m cProfile -o output.prof script.py
.venv/bin/kernprof -l -v script.py
.venv/bin/python -m memory_profiler script.py
py-spy record -o profile.svg -- .venv/bin/python script.py
```

Guidance:

- Improve algorithms and data structures before micro-optimizing syntax.
- Use generators for large streams and `"".join(...)` for string accumulation.
- Use `asyncio` for I/O-bound concurrency and `multiprocessing` for CPU-bound work.
- Batch network and database operations where semantics allow.
- Cache only when invalidation and memory growth are understood.

## Background Jobs and Workers

Use a queue boundary when work is slow, retryable, or too fragile for the request path.

```python
from celery import Celery, Task

app = Celery("tasks", broker="redis://localhost:6379/0")
app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)


@app.task(bind=True, max_retries=3, soft_time_limit=3000, time_limit=3600)
def process_order(self: Task, order_id: str) -> None:
    """Process an order, retrying transient failures with exponential backoff."""
    try:
        do_work(order_id)
    except TransientError as exc:
        raise self.retry(exc=exc, countdown=2**self.request.retries * 60) from exc
```

- Return a job ID immediately for workflows that exceed a few seconds.
- Persist job state transitions.
- Make tasks idempotent.
- Retry only transient failures and send exhausted jobs to a dead-letter path.
- Expose status polling or completion callbacks when callers need visibility.

Queue choices:

| Queue | Best For |
| --- | --- |
| Celery | Mature workflows, scheduling, rich ecosystems |
| Dramatiq | Simpler actor-style APIs |
| RQ | Small Redis-backed job systems |
| Cloud queues | Managed serverless or multi-service architectures |

## Detailed Patterns

Detailed packaging, profiling, worker, and release patterns live in `references/details.md`,
including a strict application-grade `pyproject.toml` example.

## Related Skills

- [python](../python/SKILL.md) — core coding standards and project defaults
- [python-modernization](../python-modernization/SKILL.md) — migrating to uv-native, lockfile-based
  workflows
- [python-configuration](../python-configuration/SKILL.md) — settings patterns that shape runtime
  packaging and deploy behavior
- [python-resilience](../python-resilience/SKILL.md) — retries, timeouts, and cleanup behavior
- [python-async](../python-async/SKILL.md) — async runtime and event-loop concerns
- [cicd](../cicd/SKILL.md) — CI pipelines and publishing automation
- [docker](../docker/SKILL.md) — container packaging and runtime images
- [observability](../observability/SKILL.md) — metrics, traces, and logs for jobs and releases
