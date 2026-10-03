---
name: python
description: >-
  Use before writing, editing, or reviewing any Python code (.py files, pyproject.toml), including
  small changes in an existing codebase. Sets the house defaults for uv workflows, ruff, pyright and
  ty, typing, testing, architecture, and packaging, then routes framework- or domain-specific work
  to the python-* sub-skills.
---

# Python Development

Use this skill as the default entry point for Python work. It defines the baseline toolchain,
structure, and quality bar for the rest of the Python skill family.

## Standards

These are defaults. When the repo's instruction files (`AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`)
or its CI declare a command form, a validation script, or a threshold, follow the repo instead.

- **Python version:** Use the latest stable Python (currently 3.14), installed and pinned by uv,
  for new projects. Follow the repo's declared minimum when working in an existing codebase.
- **Environment:** Use a project-local `.venv`, never system Python.
- **Package manager:** Use `uv` for Python installation, dependency management, locking, and
  command execution.
- **Formatter:** `.venv/bin/ruff format .`
- **Linter:** `.venv/bin/ruff check .` (add `--fix` while iterating), with `select = ["ALL"]` and
  a short, documented `ignore` list.
- **Type checkers:** Run `.venv/bin/pyright` and `.venv/bin/ty check`; both must report 0 errors.
  Configure both in `pyproject.toml`. New projects use `typeCheckingMode = "strict"`; existing
  repos keep their mode and tighten it package by package with `strict = ["<package>"]`.
- **Command forms:** Run tools from the project venv as `.venv/bin/<tool>`. `uv run` syncs the
  environment before every command and can replace packages installed outside the lockfile (CUDA
  or torch builds), so use it only where the repo documents it. When the repo has a single
  validation script or gate, that script alone decides whether the checks pass; individual tools
  are for iteration.
- **Testing:** TDD for new features and modules: write the failing test before the production
  code. Small targeted fixes don't require test-first, but must keep the suite green.
- **Line length:** 100 characters for prose and source.
- **Docstrings:** Google style, enforced by Ruff's `D` rules with `convention = "google"`.
- **Build backend:** `uv_build` for new projects (`uv init --build-backend uv`). Keep an existing
  backend unless the task is a migration.

## Default Workflow

1. Inspect the repo's `pyproject.toml`, Python version, and existing tooling before changing
   anything.
2. Reuse the existing `.venv` when present. If it is missing, confirm before creating it.
3. Add or remove dependencies with `uv add` and `uv remove`, not by editing dependency lists by
   hand.
4. Sync the environment with `uv sync` and update the lock file with `uv lock` when dependencies
   change.
5. Run the narrowest failing test or validation first, then format, lint, type-check, and rerun
   tests after changes.

Common commands:

```bash
uv python install 3.14
uv init --build-backend uv --python 3.14 myproject
uv add httpx
uv add --group dev ruff pyright ty pytest pytest-cov pytest-html pytest-metadata pytest-sugar pytest-xdist
uv sync
uv lock --check
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/pyright
.venv/bin/ty check
.venv/bin/pytest
```

For single-file scripts, prefer PEP 723 metadata via `uv init --script`.

## Project Layout

Prefer `src/` layout for libraries and reusable packages. Applications may stay flatter, but keep
module boundaries explicit.

```text
myproject/
├── pyproject.toml
├── README.md
├── .python-version
├── src/
│   └── myproject/
│       ├── __init__.py
│       ├── settings.py
│       ├── users/
│       │   ├── __init__.py
│       │   ├── api.py
│       │   ├── models.py
│       │   ├── repository.py
│       │   └── service.py
│       └── shared/
└── tests/
    ├── conftest.py
    └── test_users.py
```

- Keep one concept per file. Split files that mix concerns; in new code, roughly 300-500 lines is
  the signal to look for a split. When the repo states its own size threshold, use that one.
- Prefer absolute imports.
- Define `__all__` where a module exposes a deliberate public surface.
- Organize large codebases by business domain or architectural boundary, not by catch-all folders
  like `utils` or `helpers`. In an existing repo already built around such a package, follow its
  layout; reorganizing it is a separate, agreed task, not a side effect of other work.
- Keep dependency flow one-way: API or CLI layer -> service layer -> repository or client layer.

## Code Style

- Use `snake_case` for modules, files, functions, and variables.
- Use `PascalCase` for classes and `SCREAMING_SNAKE_CASE` for constants.
- Prefer descriptive names over abbreviations.
- Keep functions focused. Extract helpers when a function has multiple reasons to change or deep
  nesting.
- Write comments only when they explain intent, constraints, or a non-obvious tradeoff.
- Give public modules, classes, and functions Google-style docstrings; Ruff's `D` rules enforce
  them. Keep them concise when the signature already says most of it.

Docstring and comment stability matters:

- Start with one summary sentence ending in punctuation.
- Use one blank line between the summary and any extended text.
- Keep section headers consistent: `Args:`, `Returns:`, `Raises:`.
- Wrap prose at natural clause boundaries so repeated formatter passes remain stable.

## Type Safety

- Annotate all public functions, methods, and class attributes.
- Prefer modern built-in generics and unions: `list[str]`, `dict[str, int]`, `User | None`.
- Use `Protocol` for structural typing, `type` aliases for repeated complex shapes, and PEP 695
  type parameters (`def f[T]`, `class C[T]`) instead of module-level `TypeVar`s.
- Minimize `Any`. Use it only for truly dynamic boundaries or untyped third-party interfaces.
- Narrow optional values before use.

```python
from typing import Protocol

type JsonDict = dict[str, object]


class Serializable(Protocol):
    def to_dict(self) -> JsonDict: ...


class Repository[ModelT]:
    def save(self, entity: ModelT) -> ModelT: ...
```

## Testing

Use pytest with a TDD workflow.

```text
RED -> write or expose one failing test
GREEN -> implement the smallest fix
REFACTOR -> improve structure with tests still green
```

- Prefer behavior-level tests over implementation-coupled tests.
- Cover error paths and edge cases, not only happy paths.
- Mock at I/O boundaries, not deep internals.
- Use `pytest-asyncio` for async code and `monkeypatch` for environment-driven behavior.
- New projects get the house pytest stack in the `dev` group: `pytest`, `pytest-cov`,
  `pytest-html`, `pytest-metadata`, `pytest-sugar`, and `pytest-xdist`, plus `pytest-asyncio` for
  async code. In an existing repo, use the plugins it already has and ask before adding more.

## Design and Architecture

Use straightforward, testable designs.

- **KISS:** Prefer the simplest design that solves the current problem.
- **Single responsibility:** Separate parsing, business rules, I/O, and presentation.
- **Composition over inheritance:** Inject dependencies instead of inheriting behavior.
- **Rule of three:** Wait for repeated pressure before abstracting.
- **Dependency injection:** Pass repositories, clients, caches, and notifiers explicitly so tests
  can swap them easily.
- **Pure core, impure edges:** Keep business rules as side-effect-light as practical.

```python
class OrderService:
    def __init__(self, repo: OrderRepository, notifier: Notifier) -> None:
        self._repo = repo
        self._notifier = notifier
```

## Configuration

Use `pydantic-settings` or an equivalent typed settings layer. Load environment variables once at
startup, validate them immediately, and pass settings inward.

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    secret_key: str = Field(alias="SECRET_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_prefix="APP_",
    )
```

- Never hardcode secrets.
- Fail fast on missing required configuration.
- Use sensible local defaults only for non-sensitive settings.
- Support `secrets_dir` when targeting containers or Kubernetes.

## Resilience and Resource Safety

- Validate inputs at boundaries before expensive work.
- Raise specific exceptions with enough context to debug the failure.
- Centralize retry and timeout policy instead of scattering it across call sites.
- Retry only transient failures.
- Put timeouts on every network or external service call.
- Use `with` and `async with` for files, sockets, pools, and transactions.
- Track partial failures in batches instead of aborting entire runs on the first bad item.

For deeper guidance on retries, cleanup, context managers, and batch error handling, use
`python-resilience`.

## Packaging and Tooling

Keep `pyproject.toml` as the single source of truth. This top-level skill intentionally keeps the
example minimal. The richer, application-grade example lives with
`python-infrastructure/references/details.md` so the core skill does not spend context on repeated
tooling detail.

```toml
[build-system]
requires = ["uv_build>=0.12,<0.13"]
build-backend = "uv_build"

[project]
name = "myproject"
requires-python = ">=3.14"
dependencies = []

[dependency-groups]
dev = [
    "ruff", "pyright", "ty",
    "pytest", "pytest-cov", "pytest-html", "pytest-metadata", "pytest-sugar", "pytest-xdist",
]

[tool.uv]
default-groups = ["dev"]

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

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Guidance:

- Use `[dependency-groups]` for dev and test tooling.
- Use `[project.optional-dependencies]` for optional runtime extras that package consumers install.
- Add `py.typed` for typed distributable packages.
- Commit `uv.lock` for applications, services, and CLIs where reproducibility matters.
- For libraries, follow repo policy: some teams commit `uv.lock` for contributor reproducibility,
  others omit it because downstream users resolve dependencies themselves.
- Build with `uv build`. Publish with the repo's existing release flow.
- Put strict, app-grade tool configuration in the infrastructure layer or its references, not here.

Detailed toolchain, structure, typing, design, and configuration patterns live in
`references/foundations.md`.

## Anti-Patterns

- No `uv pip install ...` or manual virtualenv drift when `uv add`, `uv sync`, and `uv lock` are
  available.
- No bare `except Exception: pass`.
- No mixed I/O and business rules in the same function when a seam can make testing simpler.
- No exposed ORM models or transport-layer objects as public API contracts.
- No untyped collections on public interfaces.
- No blocking calls such as `time.sleep()` or `requests` inside async code.
- No scattered retry logic or double retries across application and infrastructure layers.
- No tests that only cover the happy path.

## Reference Files

- `references/foundations.md` — detailed toolchain, module-structure, typing, and configuration
  patterns

## Routing to Curated Python Skills

Use the dedicated curated Python skills when the task needs more depth than this overview.

| Need | Skill |
| --- | --- |
| Async I/O, structured concurrency, cancellation, ASGI patterns | [python-async](../python-async/SKILL.md) |
| FastAPI, ASGI handlers, dependency injection, response contracts | [python-web-apis](../python-web-apis/SKILL.md) |
| Typed settings, env vars, and secrets files | [python-configuration](../python-configuration/SKILL.md) |
| Pytest, fixtures, coverage, and TDD workflow | [python-testing](../python-testing/SKILL.md) |
| Deeper typing, protocols, and pyright-first design | [python-type-safety](../python-type-safety/SKILL.md) |
| Retries, timeouts, cleanup, and failure handling | [python-resilience](../python-resilience/SKILL.md) |
| Packaging, performance, workers, and release mechanics | [python-infrastructure](../python-infrastructure/SKILL.md) |
| Bootstrapping or migrating to modern Python tooling | [python-modernization](../python-modernization/SKILL.md) |
| Final-pass Python review checklist | [python-anti-patterns](../python-anti-patterns/SKILL.md) |

For logging, metrics, tracing, and production telemetry, also use
[observability](../observability/SKILL.md).
