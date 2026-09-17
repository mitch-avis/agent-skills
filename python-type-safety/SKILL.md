---
name: python-type-safety
description: >-
    Strengthens Python code with pyright- and ty-aware type checking, modern annotations, generics,
    protocols, and boundary typing. Use when adding or tightening types, designing reusable
    interfaces, narrowing optionals, or making Python APIs safer to refactor.
---

# Python Type Safety

Use types as checked documentation. The goal is not type density for its own sake. The goal is to
make interfaces safer to change and misuse harder to express.

## Defaults

- Run `pyright` and `ty` together in most modern Python projects.
- Treat `pyright` as the stable baseline today and `ty` as the forward-looking companion.
- Annotate every public function, method, and class attribute.
- Use modern built-in generics and unions: `list[str]`, `User | None`.
- Keep untyped or `Any`-heavy boundaries narrow and well-named.

## Core Patterns

### Public API Annotations

```python
def get_user(user_id: str) -> User | None:
    ...
```

### Type Narrowing

```python
user = get_user(user_id)
if user is None:
    raise UserNotFoundError(user_id)

return user.email
```

### Protocols for Interfaces

```python
from typing import Protocol


class Notifier(Protocol):
    def send(self, message: str) -> None: ...
```

### Generic Reuse

```python
from typing import TypeVar

ItemT = TypeVar("ItemT")


def first(items: list[ItemT]) -> ItemT | None:
    return items[0] if items else None
```

## Boundary Discipline

- Convert raw JSON, env vars, and external payloads into typed models near the boundary.
- Avoid leaking ORM rows, ad hoc dicts, or partially validated objects through public APIs.
- Prefer response and DTO models at transport edges.
- Keep type aliases and protocols close to the abstractions they describe.

## Configuration Guidance

Start with `pyright` standard mode, add `ty` to the same project, and tighten diagnostics as the
codebase becomes more explicit.

```toml
[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "standard"
venvPath = "."
venv = ".venv"
reportMissingImports = "error"
reportArgumentType = "error"
reportReturnType = "error"
reportOptionalMemberAccess = "error"

[tool.ty.environment]
python = ".venv"
```

## Testing and Refactoring

- Use types to simplify refactors, not to replace tests.
- Prefer fakes that satisfy protocols over mocks with loose, untyped behavior.
- Add type aliases when repeated shapes make tests or signatures noisy.

## Detailed Patterns

Detailed generic, protocol, callback, and configuration patterns live in
`references/details.md`.

## Anti-Patterns

- No untyped public APIs.
- No `list` or `dict` without type parameters on public boundaries.
- No sprawling `Any` that spreads through otherwise typed code.
- No type checker suppression without a local reason.
- No relying on runtime conventions where a protocol or typed model would make the contract clear.

## Related Skills

- [python](../python/SKILL.md) — core Python defaults and lightweight type guidance
- [python-web-apis](../python-web-apis/SKILL.md) — typed request and response boundaries
- [python-testing](../python-testing/SKILL.md) — test doubles and refactoring safety
- [python-modernization](../python-modernization/SKILL.md) — migrating legacy code to modern
  typing workflows
