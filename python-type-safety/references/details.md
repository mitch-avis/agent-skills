# Python Type Safety — Detailed Patterns

## Type Aliases

Use aliases for repeated or domain-specific shapes.

```python
from typing import TypeAlias

JsonObject: TypeAlias = dict[str, object]
UserId: TypeAlias = str
```

Aliases reduce noise only when they reveal intent.

## Bounded Type Variables

Bound a type variable when the generic code depends on a shared contract.

```python
from typing import TypeVar
from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


def validate_model(model_cls: type[ModelT], payload: dict[str, object]) -> ModelT:
    return model_cls.model_validate(payload)
```

## Protocols

Use protocols for structural interfaces instead of inheritance-only contracts.

```python
from typing import Protocol


class Cache(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl: int) -> None: ...
```

## Typed Results

Wrap success and failure when callers need explicit branching.

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

ValueT = TypeVar("ValueT")
ErrorT = TypeVar("ErrorT", bound=Exception)


@dataclass
class Result(Generic[ValueT, ErrorT]):
    value: ValueT | None = None
    error: ErrorT | None = None
```

Use this only when it clarifies call sites more than plain exceptions would.

## Callback Types

Type repeated callbacks explicitly.

```python
from collections.abc import Callable
from typing import TypeAlias

ProgressCallback: TypeAlias = Callable[[int, int], None]
```

## Pyright Tightening

- Promote diagnostics one by one rather than jumping straight to broad strictness.
- Fix import resolution first.
- Eliminate optional misuse next.
- Tackle `Any` spread only after the boundary types are stable.

## Migration Strategy

- Type the public surface before the internals.
- Add models and aliases at system boundaries.
- Replace repeated dict conventions with typed objects.
- Use protocols to decouple legacy implementations before refactoring them.
