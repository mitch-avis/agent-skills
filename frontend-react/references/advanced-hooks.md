# React hook patterns

Use these when repetitive local logic deserves a reusable hook and the repo does not already have a
better abstraction.

## Toggle state

```tsx
export function useToggle(initialValue = false): [boolean, () => void] {
  const [value, setValue] = useState(initialValue)
  const toggle = () => setValue(currentValue => !currentValue)
  return [value, toggle]
}
```

Use this for simple UI state such as panels, dialogs, and compact mode.

## Debounced value

```tsx
export function useDebounce<T>(value: T, delayMs: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedValue(value), delayMs)
    return () => window.clearTimeout(timer)
  }, [value, delayMs])

  return debouncedValue
}
```

Use this for search inputs or expensive filters, then pair it with `useDeferredValue` when render
cost is also the problem.

## Async query hook

```tsx
type QueryOptions<T> = {
  enabled?: boolean
  onSuccess?: (data: T) => void
  onError?: (error: Error) => void
}

export function useAsyncQuery<T>(fetcher: () => Promise<T>, options?: QueryOptions<T>) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [loading, setLoading] = useState(false)
  const fetcherRef = useRef(fetcher)
  const optionsRef = useRef(options)

  useEffect(() => {
    fetcherRef.current = fetcher
    optionsRef.current = options
  })

  const run = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const result = await fetcherRef.current()
      setData(result)
      optionsRef.current?.onSuccess?.(result)
    } catch (unknownError) {
      const error = unknownError as Error
      setError(error)
      optionsRef.current?.onError?.(error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (options?.enabled !== false) void run()
  }, [options?.enabled, run])

  return { data, error, loading, refetch: run }
}
```

The ref pattern keeps `refetch` stable even when callers pass inline functions or option objects.

## Hook quality rules

- Keep the hook boundary honest: do not hide navigation, analytics, and unrelated side effects in a
  generic hook.
- Return the smallest public surface that supports the real caller.
- Test hooks through behavior when possible, not by poking at implementation details.
