---
name: frontend-react
description: >-
  Use before writing, editing, or reviewing React or Next.js code (.tsx/.jsx components, hooks,
  routes, state, forms, data fetching) and its tests. Sets TypeScript, accessibility, transition,
  and rendering-performance defaults, plus lint, test, and validation workflows.
---

# Frontend React

Use this as the React and Next.js companion to `frontend-design`.
It captures the default engineering rules for implementation, validation, and performance work.

## When to Use

- Building or refactoring React or Next.js components, pages, layouts, and hooks
- Choosing state, routing, form, or data-fetching patterns
- Improving render performance or bundle behavior
- Formatting React and Next.js code with the repo's established tooling
- Adding tests, validation, linting, or diagnostics for React code
- Auditing a React surface for accessibility, architecture, or maintainability

## Output Expectations

- Implement directly when the user asked for code.
- If the request is architectural, explain the new ownership model and then edit the code.
- If the request is review or audit, lead with concrete findings and violated contracts.
- If the request is performance-related, identify the hot path before reaching for optimization
  patterns.

## Default Stack

- React with TypeScript is the default for greenfield frontend work.
- Use Next.js App Router for full React applications unless the repo already points elsewhere.
- In Next.js, keep server components as the default and isolate client interactivity to leaf
  components.
- Reuse the repo's existing router, test stack, styling system, and data-fetching tools before
  adding new ones.

## Example React Read

- "Reading this as a Next.js App Router surface with server-owned data and a small client leaf for
  interaction."
- "Reading this as a local component refactor where state should stay lifted one level instead of
  moving to a global store."

## First Read

Before editing, inspect:

1. package.json scripts and UI dependencies
2. TypeScript config and lint setup
3. component folders, design tokens, and shared primitives
4. routing mode, data-fetching conventions, and test helpers
5. any existing React Compiler or framework guidance already in the repo

## Implementation Shape

Use a default component shape that keeps ownership obvious.

```text
route or page
  -> data boundary / server fetch
  -> stateful container when needed
  -> presentational component tree
  -> small client leaf for interaction-heavy controls
```

## Architecture Defaults

- Prefer composition over boolean prop proliferation.
- Reuse existing components before creating adjacent duplicates.
- Keep components focused. Split only when it improves ownership, testing, or readability.
- Colocate component tests, stories, types, and complex hooks when the repo uses that pattern.
- Use this state ladder unless the repo has a stronger convention:

```text
local state → lifted state → context → URL state → server state → global store
```

- Derive values during render when possible. Do not push simple derived state into effects.
- Avoid defining components inside components.
- If the task is primarily a component-architecture refactor, follow the patterns in
  [references/architecture-patterns.md](references/architecture-patterns.md).
- If the task depends on custom hooks or repetitive async state logic, read
  [references/advanced-hooks.md](references/advanced-hooks.md).

## Component Rules

- Prefer explicit variants, composition, or compound components over boolean mode props.
- Keep handlers close to the state they mutate.
- Split a component when it improves ownership, testability, or render isolation, not just because
  the file grew.
- Do not duplicate a design-system primitive only to change a class string.
- Keep non-UI business logic out of render functions.

## Async And Data Rules

- Check cheap synchronous conditions before awaiting remote work.
- Start independent requests early and await them late.
- Use `Promise.all()` for independent async work.
- Keep data ownership near the route, page, or boundary component instead of leaf presentation
  components unless the repo already has a different pattern.
- If the repo already uses SWR, React Query, or server components, stay consistent with that choice.
- For deeper performance and validation guidance, read
  [references/performance-and-validation.md](references/performance-and-validation.md).

## Forms And State

- Use local state for short-lived form drafts unless the form must survive navigation or coordinate
  across distant siblings.
- Keep validation messages near fields and make them reachable by screen readers.
- Use URL state only for shareable state such as filters, sort, tabs, and pagination.
- Reach for global stores only when multiple distant surfaces truly share live client state.

## Rendering And Interaction Rules

- Use `startTransition` for non-urgent UI updates when it materially improves responsiveness.
- Use `useDeferredValue` for expensive filtering or list rendering when it preserves input
  responsiveness.
- Use `useEffectEvent` only when the repo or framework guidance already supports that pattern.
- Do not add `useMemo` or `useCallback` by default. Add them only when dependency stability,
  memoized children, or measured render cost justifies them.
- Use refs or motion values for high-frequency transient data such as pointer position or drag
  state.

## Accessibility And UI Quality

- Use real buttons, links, labels, and form controls before ARIA-heavy custom elements.
- Keep focus-visible states intact when wrapping primitives.
- Include loading, empty, error, disabled, and success states in component tests or verification.
- Prefer skeletons over generic spinners for content loading.
- Preserve touch target size and readable line length on mobile.

## Styling And Accessibility

- Use the project's tokens, primitives, and semantic HTML first.
- Keep focus-visible states, labels, contrast, and keyboard access intact through refactors.
- Respect `prefers-reduced-motion`.
- Avoid inline styles and arbitrary pixel values when the repo already has a scale or token system.
- Handle loading, empty, error, disabled, and success states as part of the feature, not as polish.

## Performance Guardrails

- Eliminate async waterfalls before micro-optimizing renders.
- Prefer direct imports over barrel files in performance-sensitive paths.
- Keep server-only work out of client bundles.
- Use `startTransition` and `useDeferredValue` when they improve perceived responsiveness, not as
  decoration.
- For lists, first reduce work, then consider virtualization when the rendered volume truly needs
  it.
- If the repo uses the React Compiler, remove stale defensive memoization before adding more.

## Testing And Validation

- Use TDD for behavior changes. Add a focused failing test before implementation when coverage is
  missing.
- Prefer the repo's existing test framework and helpers.
- Run the narrowest affected tests first, then the touched package's formatter, lint, typecheck,
  and build.
- For React changes, run `npx react-doctor@latest --verbose --scope changed`.
- For design-focused React audits, run `npx react-doctor@latest design --verbose`.
- When the user asks for a full React cleanup pass or `/doctor`, run the fetched
  `react-doctor` playbook described in
  [references/performance-and-validation.md](references/performance-and-validation.md).

## Validation Order

Use this order when checks exist:

1. focused tests for the changed behavior
2. formatter for the touched package or app
3. lint and typecheck for the touched package or app
4. build or framework-specific validation for the touched slice
5. `react-doctor` for changed-scope diagnostics

## Advanced Cases

### View Transitions

- Use native view transitions only when the UI change communicates continuity.
- Prioritize shared elements first, then suspense reveals, list identity, state changes, and route
  changes.
- Reserve directional slides for hierarchical navigation such as list to detail or previous and
  next flows.
- Keep lateral navigation subtle. Tabs and peer views rarely need depth animation.
- Trigger transitions through React state transitions. Do not hand-roll direct DOM-level
  transition orchestration unless the platform requires it.

### Deployment-Scale Composition

- Use microfrontends only when team boundaries, release cadence, or platform architecture truly
  require independent deployment.
- Keep shared contracts shallow: navigation, shell boundaries, auth expectations, and path
  ownership.
- Avoid introducing microfrontends just to paper over a component-ownership problem.

### JSON-Driven Rendering

- Only use JSON-rendered component catalogs when the project already depends on that model.
- Keep catalog props typed and narrow.
- Keep rendering boundaries explicit so product state and layout logic stay debuggable.

### React 19 And Type Boundaries

- Only apply React 19-specific patterns when the repo is actually on React 19 or equivalent Next.js
  support.
- Prefer the current repo convention for context access and ref typing over speculative migration.
- When this matters, use
  [references/react-19-types.md](references/react-19-types.md).

## Reference Files

- [references/architecture-patterns.md](references/architecture-patterns.md) for component API,
  state, and composition examples
- [references/advanced-hooks.md](references/advanced-hooks.md) for reusable custom hook patterns
- [references/performance-and-validation.md](references/performance-and-validation.md) for
  performance order, transition rules, and React diagnostics
- [references/performance-rules-catalog.md](references/performance-rules-catalog.md) for a compact
  performance taxonomy when a task is broad
- [references/react-19-types.md](references/react-19-types.md) for version-specific React 19 and
  ref-typing guidance
- [references/view-transitions-implementation.md](references/view-transitions-implementation.md)
  for deeper view-transition implementation guidance

## Example Triggers

- "Refactor this React component with too many boolean props."
- "Build this new page in Next.js and keep the data fetching parallel."
- "Why does this client search freeze while typing?"
- "Run the React validation pass before I commit these UI changes."

## Done When

- The component or page follows the repo's architecture and styling patterns.
- State ownership is clear and no broader than necessary.
- Performance hazards were checked before adding memoization or new dependencies.
- Accessibility and non-happy-path states are present.
- The relevant tests, lint, typecheck, and React diagnostics were run.
