---
name: python
description: >-
  Comprehensive Python development guide covering code style, design patterns, type safety,
  project structure, configuration, and anti-patterns. Enforces ruff format, ruff check,
  pyright type checking, and 100-character line length. Use for all Python coding, review,
  and architecture tasks.
---

# Python Development

Consolidated guide for writing clean, typed, well-structured Python.

## Standards

- **Formatter:** `ruff format .`
- **Linter:** `ruff check --fix .` (strict settings)
- **Type checker:** `pyright` (standard mode, used via PyLance in VS Code)
- **Line length:** 100 characters
- **Python version:** 3.12+ for new projects
- **Testing:** TDD — failing tests first, then implementation
- **Package manager:** `uv` for installs, venvs, and Python version management
- **Virtual environment:** Always use a `.venv` — never the system Python

## Environment Management

**Always use a virtual environment.** If a `.venv` does not exist in the project, ask the user
before creating one.

### uv (preferred tool)

Keep `uv` up-to-date:

```bash
uv self update
```

Common workflows:

```bash
uv venv                          # create .venv in current directory
uv pip install -e ".[dev]"       # editable install with dev extras
uv pip install -r requirements.txt
uv pip compile pyproject.toml -o requirements.txt
uv run pytest                    # run command inside venv
uv python install 3.12           # install a Python version
uv python pin 3.12               # pin project to Python 3.12
```

## Ruff Configuration

```toml
[tool.ruff]
line-length = 100
target-version = "py312"
extend-exclude = [
    ".venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "build",
    "dist",
]

[tool.ruff.lint]
select = [
    "B",   # flake8-bugbear rules
    "C4",  # flake8-comprehensions rules
    "D",   # pydocstyle rules
    "E",   # pycodestyle errors
    "F",   # pyflakes rules
    "I",   # isort rules
    "N",   # pep8-naming rules
    "S",   # bandit security rules
    "SIM", # flake8-simplify rules
    "UP",  # pyupgrade rules
    "W",   # pycodestyle warnings
]
ignore = [
    "D203", # Conflicts with D211 (no-blank-line-before-class)
    "D213", # Conflicts with D212 (multi-line-summary-first-line)
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101"] # Use of assert is standard in pytest

[tool.ruff.lint.isort]
known-first-party = ["myproject"]

[tool.ruff.format]
docstring-code-format = true
```

## Code Style

- Use absolute imports: `from myproject.services import UserService`
- Google-style docstrings with Args, Returns, Raises sections
- `snake_case` for files, modules, functions, variables
- `PascalCase` for classes
- `SCREAMING_SNAKE_CASE` for constants
- Descriptive names — `user_repository` not `usr_repo`
- Avoid generic names: `utils`, `helpers`, `common`, `shared`

## Type Safety

- Annotate all public functions, methods, and class attributes
- Use `T | None` over `Optional[T]` (Python 3.10+ syntax)
- Use generics (`TypeVar`, `Generic`) to preserve type information
- Use `Protocol` for structural typing (duck typing with safety)
- Minimize `Any` — use specific types or generics instead
- Use `pyright` in standard mode — catches errors before runtime

### Key Patterns

```python
from typing import Protocol, TypeVar

class Serializable(Protocol):
    def to_dict(self) -> dict[str, Any]: ...

ModelT = TypeVar("ModelT", bound=BaseModel)

class Repository(Generic[ModelT]):
    def save(self, entity: ModelT) -> ModelT: ...
```

## Design Patterns

### Layered Architecture

API Layer → Service Layer (business logic) → Repository Layer (data access). Dependencies flow
downward only.

### KISS

Do not add factories, registries, or abstractions unless they solve a real, current problem. A
dictionary and a function often beat a factory class.

### Single Responsibility

Each class has one reason to change. Separate HTTP parsing from business logic from database access.

### Composition Over Inheritance

Pass dependencies through constructors. Do not inherit behaviors when you can compose multiple
capabilities.

### Dependency Injection

```python
class OrderService:
    def __init__(
        self,
        repo: OrderRepository,
        notifier: Notifier,
    ) -> None:
        self.repo = repo
        self.notifier = notifier
```

Enables easy mocking in tests and swappable implementations.

### Rule of Three

Two instances of duplication are acceptable. Abstract only after three occurrences.

## Project Structure

```text
myproject/
  __init__.py
  settings.py
  users/
    __init__.py
    models.py
    service.py
    repository.py
    api.py
  orders/
    ...
tests/
  ...
pyproject.toml
VERSION
```

- One concept per file; split at 300–500 lines
- Define `__all__` for every module's public interface
- Flat structure preferred — add depth only for genuine sub-domains
- Organize large projects by business domain (domain-driven)

## pyproject.toml

Use `pyproject.toml` as the single source of project configuration. Preferred build backend is
`hatchling`. Include tool configs for ruff, pyright, pytest, and coverage inline.

```toml
[build-system]
requires = ["hatchling>=1.26"]
build-backend = "hatchling.build"

[project]
name = "myproject"
dynamic = ["version"]
description = "Project description"
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
dependencies = []

[tool.hatch.build.targets.wheel]
packages = ["myproject"]

[tool.hatch.version]
path = "VERSION"

[tool.ruff]
line-length = 100
target-version = "py312"
extend-exclude = [
    ".venv", ".git", "__pycache__",
    ".pytest_cache", ".mypy_cache",
    "build", "dist",
]

[tool.ruff.lint]
select = [
    "B", "C4", "D", "E", "F", "I",
    "N", "S", "SIM", "UP", "W",
]
ignore = ["D203", "D213"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101"]

[tool.ruff.lint.isort]
known-first-party = ["myproject"]

[tool.ruff.format]
docstring-code-format = true

[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "standard"
reportMissingImports = true
reportMissingTypeStubs = false
venvPath = "."
venv = ".venv"

[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
addopts = [
    "-ra",
    "--strict-markers",
    "--cov=myproject",
    "--cov-report=term-missing",
]
filterwarnings = ["ignore::DeprecationWarning"]
pythonpath = ["."]

[tool.coverage.run]
branch = true
source = ["myproject"]

[tool.coverage.report]
show_missing = true
skip_empty = true
exclude_lines = ["pragma: no cover", "if __name__ == \"__main__\":"]
```

## Configuration

Use `pydantic-settings` for typed, validated configuration:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    secret_key: str  # no default = required

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_nested_delimiter="__",
    )
```

- Never hardcode secrets or environment-specific values
- Fail fast at startup on missing or invalid config
- Provide dev defaults for local convenience
- Use `secrets_dir` for Docker/Kubernetes mounted secrets

## Anti-Patterns

- **No bare `except Exception: pass`** — catch specific exceptions
- **No exposed ORM models in API responses** — use DTOs/schemas
- **No mixed I/O and business logic** — separate into layers
- **No hardcoded config or secrets** — use environment variables
- **No missing type hints on public functions**
- **No untyped collections** — `list[str]` not `list`
- **No `time.sleep()` in async code** — use `await asyncio.sleep()`
- **No scattered retry/timeout logic** — centralize in decorators
- **No double retry** (app + infra both retrying)
- **No tests that only cover happy paths** — test error paths too
