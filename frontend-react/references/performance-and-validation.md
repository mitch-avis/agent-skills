# React performance and validation

Use this reference when the task is about sluggish rendering, bundle growth, validation, or
advanced React behavior.

## Performance order

Optimize in this order.

1. remove async waterfalls
2. reduce unnecessary client work
3. keep server and client boundaries honest
4. shrink the bundle
5. optimize renders only when the cost is real

## Remove waterfalls first

- Check cheap sync conditions before awaiting remote values.
- Start independent requests early.
- Await them only where the result is actually needed.
- Use `Promise.all()` for independent data.

```tsx
const profilePromise = getProfile(userId)
const billingPromise = getBilling(userId)

const [profile, billing] = await Promise.all([profilePromise, billingPromise])
```

## Rerender discipline

- Do not add `useMemo` or `useCallback` by reflex.
- First ask what is rerendering, why, and whether the cost is measurable.
- Keep transient high-frequency values in refs or motion values instead of state.
- Use `useDeferredValue` for expensive filtering and `startTransition` for non-urgent updates when
  they preserve responsiveness.

If the repo uses the React Compiler, prefer removing stale defensive memoization before adding more.
The compiler changes the default cost model for `useMemo` and `useCallback`.

## Bundle and boundary discipline

- Prefer direct imports over broad barrel imports in heavy code paths.
- Keep server-only logic and large data shaping out of client bundles.
- Lazy-load heavy dialogs, editors, charts, and rarely used flows when the product experience
  benefits.

## Hydration and serialization

- Fix true server and client mismatches at the source before suppressing warnings.
- Use suppression only for intentionally different content such as timestamps or client-only state
  that cannot match on the server.
- Keep server-component payloads narrow. Avoid serializing large duplicate objects into client
  components when a smaller derived shape would do.

## Performance categories

When a performance task is broad, reason in this order:

1. async waterfalls
2. bundle size and analyzable imports
3. server boundary and serialization
4. client fetch duplication and event listeners
5. rerender frequency
6. render cost and DOM work
7. small JavaScript hot-path fixes

## View transition rules

- Use them when they explain continuity, not to decorate every state change.
- Shared-element transitions usually matter more than page-wide fades.
- Suspense reveals and list identity transitions are useful when data arrival or reordering should
  feel stable.
- Directional navigation is for hierarchical flows, not sibling tabs.

## React diagnostics

After React changes, use these commands when available in the project environment:

```bash
npx react-doctor@latest --verbose --scope changed
npx react-doctor@latest design --verbose
npx react-doctor@latest --verbose
```

Use `scan <url> --format json` only when diagnosing a real runtime interaction problem and the user
can reproduce it locally.

When the user asks for `/doctor` or a full cleanup pass, fetch the current playbook before acting:

```bash
curl --fail --silent --show-error \
  --header 'Cache-Control: no-cache' \
  https://www.react.doctor/prompts/react-doctor-agent.md
```

## Validation order

1. focused behavior test
2. formatter
3. lint and typecheck
4. build or framework validation
5. changed-scope React diagnostics
