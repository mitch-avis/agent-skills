# React architecture patterns

Use these patterns when the task is about component design, state ownership, or API cleanup.

## Composition over mode props

Prefer explicit structure over piles of booleans.

- Good: separate `CardHeader`, `CardBody`, `CardFooter`, or explicit `PrimaryButton` and
  `SecondaryButton` variants
- Risky: `compact`, `dense`, `inline`, `minimal`, and `editable` booleans accumulating on one
  component

When a prop changes layout and behavior together, the API usually wants either composition or an
explicit variant enum.

```tsx
type NoticeProps = {
  tone: 'info' | 'warning' | 'success'
  title: string
  children: React.ReactNode
}

export function Notice({ tone, title, children }: NoticeProps) {
  return (
    <section aria-live="polite" data-tone={tone}>
      <h2>{title}</h2>
      <div>{children}</div>
    </section>
  )
}
```

## Ownership ladder

Move state only as high as the real consumer requires.

1. local UI state inside the component
2. lifted state across nearby siblings
3. context for widely shared, low-volatility state
4. URL state for shareable filters, tabs, sorting, or pagination
5. server state for remote data and cache ownership
6. global store only when distant surfaces share live client state

If a component passes props through layers that do not use them, restructure before adding a global
store.

## Container and presentation

Keep data ownership and display concerns separate when the component does both poorly.

```tsx
export function AccountPage() {
  const accountQuery = useAccount()

  if (accountQuery.isLoading) return <AccountSkeleton />
  if (accountQuery.error) return <AccountError />
  if (!accountQuery.data) return <AccountEmpty />

  return <AccountDetails account={accountQuery.data} />
}
```

Presentation components should not know where data came from.
Boundary components should own loading, empty, and error states.

## Compound components

Use compound components when siblings need shared state and a coherent API.

```tsx
type TabsContextValue = {
  activeTab: string
  setActiveTab: (nextTab: string) => void
}

const TabsContext = createContext<TabsContextValue | null>(null)

export function Tabs({ defaultTab, children }: { defaultTab: string; children: React.ReactNode }) {
  const [activeTab, setActiveTab] = useState(defaultTab)

  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab }}>
      {children}
    </TabsContext.Provider>
  )
}

export function useTabs() {
  const context = useContext(TabsContext)
  if (!context) throw new Error('useTabs must be used within Tabs')
  return context
}
```

This pattern is usually clearer than stacking booleans such as `vertical`, `compact`, `inline`,
and `withIcons` onto one monolithic component.

## Error boundaries

- Use an error boundary for recoverable UI failures that should not take down the whole screen.
- Keep route-level data failures and render-time component crashes conceptually separate.
- Pair error boundaries with loading and empty states rather than treating them as a substitute.

## Forms and drafts

- Keep drafts local unless they must survive route changes or coordinate across distant panels.
- Keep labels, help text, errors, and success messages close to fields.
- Make submit buttons describe the action they perform.
- Do not use placeholder text as the only label.

## Interaction quality

- Real buttons for actions, real links for navigation, real labels for fields
- `focus-visible` states on the actual focused element or its visible wrapper
- empty, loading, disabled, error, and success states are part of the feature contract
- mobile touch targets stay large enough to use without precision
