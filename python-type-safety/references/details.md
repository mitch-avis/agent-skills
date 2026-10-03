# Python Type Safety — Detailed Patterns

## Type Aliases

Use aliases for repeated or domain-specific shapes.

```python
type JsonObject = dict[str, object]
type UserId = str
```

Aliases reduce noise only when they reveal intent.

## Bounded Type Parameters

Bound a type parameter when the generic code depends on a shared contract.

```python
from pydantic import BaseModel


def validate_model[ModelT: BaseModel](
    model_cls: type[ModelT], payload: dict[str, object]
) -> ModelT:
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


@dataclass
class Result[ValueT, ErrorT: Exception]:
    value: ValueT | None = None
    error: ErrorT | None = None
```

Use this only when it clarifies call sites more than plain exceptions would.

## Callback Types

Type repeated callbacks explicitly.

```python
from collections.abc import Callable

type ProgressCallback = Callable[[int, int], None]
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
