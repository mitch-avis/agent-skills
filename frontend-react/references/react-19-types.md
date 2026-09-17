# React 19 and typing notes

Use this only when the project is actually on React 19 or equivalent framework support.

## Context access

- Follow the repo's current context pattern first.
- If the project has adopted React 19 `use()`-based context access, stay consistent within that
  codebase instead of mixing patterns arbitrarily.
- If a codebase still uses `useContext()` everywhere, do not migrate one isolated component just to
  look modern.

## Ref typing

- Avoid adding new `forwardRef` wrappers by reflex.
- Prefer the repo's current ref convention and component boundary style.
- If a component exposes a ref, make the public ref target explicit and narrow.

When React 19 ref patterns are in use, keep the public API small and avoid passing refs through
layers that do not need them.

## Migration discipline

- Do not mix React 18 and React 19 guidance in the same change without checking the actual app
  version and team conventions.
- A version-specific API change is not a cleanup task on its own. Only migrate when the codebase is
  ready for it or the task explicitly asks for it.

## Compound component upgrades

- Keep context and child APIs stable during migration.
- Prefer updating one component family at a time rather than mixing old and new context patterns
  across one surface.
