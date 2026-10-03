# Frontend Workflows

Use these flows after the initial Frontend Read.
Choose the narrowest workflow that fits the task.

## New Surface

Use this for a new component, page, or application surface.

1. Inspect the existing design system, routing, and test setup.
2. Default to React and TypeScript only when the repo does not already dictate another framework.
3. Choose the surface mode: Persuade, Operate, Read, or Experience.
4. Write a one-line design read before coding.
5. Build the real interface first, not a marketing shell around it.
6. Include loading, empty, error, disabled, and success states in the first implementation.
7. Validate with the narrowest tests, lint, typecheck, and app-specific checks.
8. For React and Next.js code, read `../frontend-react/SKILL.md`.

## Redesign Existing UI

Use this when a surface already exists and the job is to improve it.

1. Preserve product truth, working behavior, and factual content unless the user asked to replace
   them.
2. Audit the current surface in this order: structure, states, typography, color, spacing,
   interaction, motion.
3. Keep what is specific to the product. Remove what looks generic, duplicated, or accidental.
4. Fix system-level issues before surface polish: tokens, hierarchy, spacing scale, focus treatment,
   responsive breakpoints.
5. Re-check edge states after visual changes. Redesign work often breaks empty and error states
   first.
6. For the full redesign playbook, read `../frontend-redesign/SKILL.md`.

## Review And Audit

Use this path when the user asks to review, audit, or check frontend quality.

1. Treat behavior regressions, inaccessible flows, and broken responsive layouts as correctness
   issues.
2. For explicit review requests, read `../code-review/SKILL.md` first.
3. For explicit redesign findings, upgrade order, and finish-pass checks, read
   `../frontend-redesign/SKILL.md`.
4. For React work, run the repo-pinned `npx --no react-doctor --verbose --scope changed`.
5. For a focused UI audit in React, run `npx --no react-doctor design --verbose`. If the repo
   lacks `react-doctor`, add it as an exact-pinned dev dependency first; see
   [React diagnostics](../../frontend-react/references/performance-and-validation.md#react-diagnostics).
6. Review with two lenses: visual critique and implementation audit. A page can look polished and
   still fail on labels, focus, responsive behavior, or state coverage.

## Design System Routing

Match the system to the product honestly.
If the brief or repo already points at one of these, use the official package instead of mimicking
it by hand.

| Context | Preferred system |
| --- | --- |
| Microsoft or enterprise SaaS | Fluent UI |
| Google or Material surfaces | Material Web or Material 3 |
| IBM analytics and enterprise tooling | Carbon |
| Shopify admin surfaces | Polaris |
| GitHub-adjacent tools or docs | Primer |
| UK public sector | GOV.UK Frontend |
| US public sector | USWDS |
| Modern custom SaaS with existing Tailwind primitives | Existing repo system first, then shadcn/ui only if already supported |

Do not mix multiple design systems in one surface.
Do not import an official system and override most of it into a custom lookalike.

## Icon And Asset Routing

Treat icons and imagery as part of the product language, not filler.

- Use one icon family per surface.
- Keep stroke width and optical weight consistent.
- If the repo already uses Lucide, stay consistent. If the icon choice is open, prefer a family
   with more character such as Phosphor, Radix Icons, Heroicons, or Tabler when it fits the
   product.
- Do not use emoji as a substitute for an icon system in product UI.
- Prefer real product imagery, believable demonstration data, or clearly temporary placeholders over
   decorative gradient backgrounds standing in for content.

## Motion Escalation

Escalate motion only when the task benefits from it.

| Need | Default tool |
| --- | --- |
| Hover, press, small state changes | CSS transitions |
| Component choreography in React | Motion library if the repo already uses it |
| Route or shared-element transitions in React | Use the transition guidance in `../frontend-react/SKILL.md` |
| Heavy scrolltelling or platform-specific choreography | Use only when the brief clearly calls for it |

Regardless of tool choice:

- animate `transform` and `opacity`
- respect `prefers-reduced-motion`
- avoid `transition-all`
- avoid `window.addEventListener('scroll')` for animation-driven rendering
