# Python Foundations — Detailed Patterns

## Environment and Toolchain

Use a project-local `.venv` and drive it with `uv`.

```bash
uv python install 3.14
uv init --build-backend uv --python 3.14 myproject
uv add httpx
uv add --group dev ruff pyright ty pytest pytest-cov pytest-html pytest-metadata pytest-sugar pytest-xdist
uv sync
uv lock --check
```

- Reuse the existing environment when one already exists.
- Confirm before creating a new `.venv` in an existing repo.
- Run tools as `.venv/bin/<tool>` instead of relying on activation or `uv run`, which re-syncs
  the environment first and can replace packages installed outside the lockfile.

## Naming and Docstrings

- Use descriptive `snake_case` names for modules, functions, and variables.
- Use `PascalCase` for classes and `SCREAMING_SNAKE_CASE` for constants.
- Avoid vague buckets such as `helpers`, `common`, or `misc`.

Use Google-style docstrings, enforced by Ruff's `D` rules with `convention = "google"`:

```python
def process_batch(items: list[Item]) -> BatchResult:
    """Process a batch of items.

    Args:
        items: Items to process.

    Returns:
        Batch results grouped by outcome.

    Raises:
        ValueError: If the input list is empty.
    """
```

## Imports and Public APIs

Prefer absolute imports and deliberate public surfaces.

```python
from myproject.services import UserService

__all__ = ["UserService"]
```

- Re-export only what callers should rely on.
- Keep internal helpers private by omission.

## Project Structure

### Libraries and Packages

```text
src/
└── myproject/
    ├── __init__.py
    ├── api/
    ├── services/
    ├── repositories/
    └── models/
```

### Domain-Oriented Applications

```text
myproject/
├── users/
│   ├── api.py
│   ├── service.py
│   ├── repository.py
│   └── models.py
└── orders/
```

- Keep dependency flow one-way.
- Split files when the reasons to change multiply.
- Prefer business-domain grouping once the codebase gets large.

## Type Safety

Annotate public interfaces and use modern type features.

```python
from typing import Protocol

type JsonValue = str | int | float | bool | dict[str, object] | list[object] | None


class Serializable(Protocol):
    """Anything that can render itself as a JSON object."""

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""
```

- Prefer `User | None` over `Optional[User]` when the project supports Python 3.10+.
- Use `Protocol` for structural interfaces.
- Use `type` aliases for repeated shapes and PEP 695 type parameters for generics.
- Run `pyright` and `ty` together; both must report 0 errors.

## Design Patterns

### Keep It Simple

Use the lightest abstraction that solves the current problem.

```python
FORMATTERS = {
    "json": JsonFormatter,
    "csv": CsvFormatter,
}


def get_formatter(name: str) -> Formatter:
    """Return a new formatter for a registered format name."""
    return FORMATTERS[name]()
```

### Separate Concerns

- Route layer: parse transport inputs and produce transport outputs.
- Service layer: apply business rules.
- Repository or client layer: perform I/O.

### Compose Instead of Inherit

Inject dependencies so tests can swap them easily.

```python
class UserService:
    """User business rules, with storage and notification injected."""

    def __init__(self, repository: UserRepository, notifier: Notifier) -> None:
        """Wire the service to its collaborators."""
        self._repository = repository
        self._notifier = notifier
```

### Rule of Three

Abstract after repeated pressure, not at the first sign of duplication.

## Configuration

Use typed settings rather than `os.getenv()` scattered across the codebase.

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings, validated once at startup."""

    environment: str = Field(default="local", alias="ENVIRONMENT")
    database_url: str = Field(alias="DATABASE_URL")
    debug: bool = Field(default=False, alias="DEBUG")

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")
```

- Fail fast on missing required settings.
- Provide safe local defaults only for non-sensitive values.
- Support mounted secret files when deploying to containers or Kubernetes.

## Common Anti-Patterns to Avoid

- Mixing I/O and business logic in the same function.
- Returning ORM models from public API boundaries.
- Using bare `except` or swallowing exceptions.
- Leaving public functions untyped.
- Building huge grab-bag modules because naming the real boundary feels inconvenient.
