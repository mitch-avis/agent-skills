---
name: python-type-safety
description: >-
  Use before adding or changing Python type hints, generics, protocols, or TypedDicts, and whenever
  pyright or ty reports errors. Covers strict pyright- and ty-aware annotations, narrowing
  optionals, boundary typing, and interfaces that are safe to refactor.
---

# Python Type Safety

Use types as checked documentation. The goal is not type density for its own sake. The goal is to
make interfaces safer to change and misuse harder to express.

## Defaults

- Run `pyright` and `ty` together; both must report 0 errors (configuration is in the `python`
  skill).
- Annotate every public function, method, and class attribute.
- Use modern built-in generics and unions: `list[str]`, `User | None`.
- Keep untyped or `Any`-heavy boundaries narrow and well-named.

## Core Patterns

### Public API Annotations

```python
def get_user(user_id: str) -> User | None:
    """Return the user with ``user_id``, or ``None`` if there is none."""
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
    """Anything that can deliver a message to a user."""

    def send(self, message: str) -> None:
        """Deliver ``message``."""
```

### Generic Reuse

```python
def first[ItemT](items: list[ItemT]) -> ItemT | None:
    """Return the first item, or ``None`` for an empty list."""
    return items[0] if items else None
```

## Boundary Discipline

- Convert raw JSON, env vars, and external payloads into typed models near the boundary.
- Avoid leaking ORM rows, ad hoc dicts, or partially validated objects through public APIs.
- Prefer response and DTO models at transport edges.
- Keep type aliases and protocols close to the abstractions they describe.

## Configuration Guidance

New projects start in strict mode. An existing repo keeps its mode and tightens it one package
at a time with `strict = ["<package>"]`. Don't turn a strict check off project-wide: a dependency
that ships without stubs gets its own stub under `typings/` (`pyright --createstub <package>`
drafts one). `pythonVersion` matches the project's `requires-python`
floor; `3.14` below is an example.

```toml
[tool.pyright]
pythonVersion = "3.14"
typeCheckingMode = "strict"
venvPath = "."
venv = ".venv"

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
- No inline type-checker suppressions (`# type: ignore`, `# pyright: ignore`): fix the types with
  narrowing, a protocol or a typed stub.
- No relying on runtime conventions where a protocol or typed model would make the contract clear.

## Related Skills

- [python](../python/SKILL.md) — core Python defaults and lightweight type guidance
- [python-web-apis](../python-web-apis/SKILL.md) — typed request and response boundaries
- [python-testing](../python-testing/SKILL.md) — test doubles and refactoring safety
- [python-modernization](../python-modernization/SKILL.md) — migrating legacy code to modern
  typing workflows
