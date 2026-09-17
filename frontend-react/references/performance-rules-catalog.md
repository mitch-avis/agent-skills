# React performance rules catalog

Use this when a performance task is broad and you need a compact checklist instead of a single
heuristic.

## Async rules

- `async-*`: eliminate waterfalls, start independent work early, and use suspense intentionally

## Bundle rules

- `bundle-*`: prefer direct imports, defer heavy features, and keep optional code off the critical
  path

## Server rules

- `server-*`: keep serialization narrow, avoid shared mutable module state, and parallelize route
  data where possible

## Client rules

- `client-*`: avoid duplicate fetching, duplicated global listeners, and unnecessary persistence

## Rerender rules

- `rerender-*`: subscribe narrowly, derive during render, and treat memoization as a measured tool

## Rendering rules

- `rendering-*`: reduce DOM work, prefer transform and opacity for motion, and avoid hydration
  mismatches

## JavaScript rules

- `js-*`: improve hot loops, use the right data structures, and defer non-critical work

## Advanced rules

- `advanced-*`: use only when the stack supports them and the simpler fixes are exhausted

Work through the categories in that order unless profiling shows a more direct problem.
