---
name: python
description: Comprehensive Python development guide covering code style, design patterns, type safety, project structure, configuration, and anti-patterns. Enforces ruff format, ruff check, strict type checking, and 100-character line length. Use for all Python coding, review, and architecture tasks.
---

# Python Development

Consolidated guide for writing clean, typed, well-structured Python.

## Standards

- **Formatter:** `ruff format .`
- **Linter:** `ruff check --fix .` (strict settings)
- **Type checker:** `mypy --strict` or `pyright` in CI
- **Line length:** 100 characters
- **Python version:** 3.12+ for new projects
- **Testing:** TDD — failing tests first, then implementation

## Ruff Configuration

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "SIM",
          "TCH", "RUF", "S", "PTH", "PL"]
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
- Enable strict mode: `mypy --strict` catches errors before runtime

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
src/
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
```

- One concept per file; split at 300–500 lines
- Define `__all__` for every module's public interface
- Flat structure preferred — add depth only for genuine sub-domains
- Organize large projects by business domain (domain-driven)

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
