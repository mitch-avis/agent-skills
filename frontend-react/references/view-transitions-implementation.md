# View transitions implementation

Use this when React view transitions are genuinely part of the feature, not just a visual garnish.

## Start with the audit

Add a transition only when it communicates one of these:

- same thing, deeper view
- data arrived
- list order changed
- something entered or exited
- the user moved to a new place

If you cannot name the continuity, skip the transition.

## Implementation order

1. shared elements
2. suspense reveal
3. list identity
4. state enter and exit
5. route change

## Placement rule

The transition wrapper must be the boundary that actually enters, exits, or moves.
If another DOM node wraps it, the animation often becomes a no-op.

## Direction rule

- Use directional slides for hierarchical navigation such as list to detail
- Use subtler fades or no motion for sibling tabs or lateral views
- Keep refresh and background revalidation quiet

## Next.js rule

In Next.js, keep the transition logic consistent with the router and loading boundary structure that
already exists.
Do not bolt transition wrappers around random nodes until the route and suspense boundaries are
clear.

## Fallback rule

Unsupported browsers should still work normally.
The transition is polish, not a requirement for the feature to function.
