---
name: frontend-design
description: >-
  Use before building or restyling any user-facing UI: layout, styling (CSS, Tailwind), components,
  interaction, accessibility, responsive behavior, design systems, frontend performance, or visual
  polish, including frontend code review. React and Next.js are the default stack unless the project
  already uses another framework.
---

# Frontend Design

- Use this as the top-level skill for frontend work.
- It sets the workflow, quality floor, and routing for design, redesign, React implementation,
  audits, and review.

## Output Expectations

Match the output to the request instead of defaulting to code immediately.

- If the user wants planning, produce a concise design or implementation plan.
- If the user wants implementation, edit the code and validate it.
- If the user wants review, lead with findings and affected contracts.
- If the user wants polish or redesign, preserve product truth and improve the surface without
  inventing product behavior.

## Default Stack

- Respect the existing repo before introducing a new stack.
- Default to React with TypeScript for component work when the prompt is greenfield or ambiguous.
- Default to Next.js App Router for full applications and page-based React work unless the repo or
  brief already points elsewhere.
- Use the existing styling system first. Tailwind is appropriate only when the project already uses
  it or the user explicitly wants it.
- Add motion only when it clarifies state, hierarchy, or feedback.

## Frontend Read

Before editing:

1. Inspect the current components, tokens, font loading, routing, package.json UI dependencies, and
   test, lint, and typecheck scripts.
2. Identify the surface mode: Persuade, Operate, Read, or Experience.
3. Write a one-line "Frontend Read" that names the surface, audience, mode, visual language, and
   implementation stack.
4. Ask one clarifying question only when the answer would change layout, framework, or behavior.

## Example Frontend Reads

- "Reading this as an Operate surface for repeated internal use, leaning toward quiet product UI in
  React with the existing design system."
- "Reading this as a Persuade surface for technical buyers, leaning toward a restrained launch page
  with stronger hierarchy and a React implementation path."
- "Reading this as a redesign of an existing dashboard, so behavior stays fixed while typography,
  states, spacing, and responsive structure get upgraded."

If the brief is open-ended or aesthetically vague, use the optional brief-inference reference in
[references/brief-inference.md](references/brief-inference.md) to choose a sensible level of
visual variance, motion, and density before designing.

## Workflow Routing

Use the smallest path that fits the task.

- New UI in an existing product: reuse the current design system, tokens, and components before
  inventing new ones.
- Greenfield UI with no stack given: default to React and TypeScript, then read
  [../frontend-react/SKILL.md](../frontend-react/SKILL.md).
- Existing UI redesign, polish, or visual audit: read
  [../frontend-redesign/SKILL.md](../frontend-redesign/SKILL.md).
- React or Next.js implementation, architecture, state, transitions, performance, or validation:
  read [../frontend-react/SKILL.md](../frontend-react/SKILL.md).
- Explicit code review: read [../code-review/SKILL.md](../code-review/SKILL.md), then keep the
  frontend findings focused on behavior, accessibility, responsive integrity, and maintainability.
- Official design system match: use the design-system routing section in
  [references/workflows.md](references/workflows.md).

## Surface Modes

Name the surface mode before making major decisions.

- `Persuade`: marketing, launch, pricing, portfolio, campaigns. Success means a first-time visitor
  understands the offer, sees proof, and knows the next action quickly.
- `Operate`: dashboards, settings, editors, admin, internal tools. Success means frequent users can
  scan state, complete tasks, and recover from edge states without friction.
- `Read`: docs, help centers, long-form knowledge pages. Success means the structure and pacing help
  comprehension before ornament does.
- `Experience`: showcases, galleries, product demos, immersive artifacts. Success means the artifact
  or interaction leads, while the interface stays legible and supportive.

- Mode determines density, motion, copy style, and what counts as success.
- A launch page can be expressive.
- A daily workflow surface should optimize scanability before spectacle.

## Core Directives

### Subject Before Style

- Ground the design in the product, audience, and task.
- The brief wins over personal taste.

### Design System First

- Reuse existing tokens, primitives, icons, spacing, and typography.
- If the brief clearly matches a real design system, use the official package rather than a
  lookalike.
- Do not mix multiple design systems in one surface.

### React-First, Not React-Only

- React is the default for greenfield work, not a reason to rewrite an established Vue, Svelte, or
  plain HTML surface.

### Design And Engineering Move Together

- Do not separate visuals from implementation quality.
- Frontend work is incomplete if it looks better but becomes harder to maintain, less accessible, or
  less testable.

### Reuse Before Reinventing

- Inspect existing primitives, page shells, data hooks, and tokens first.
- Extend nearby patterns before introducing new abstractions.
- If a shared abstraction is not clearly reusable across multiple surfaces, keep the logic local.

### Production States Are Mandatory

- Handle loading, empty, error, disabled, success, and recovery states as part of the first pass.

### Accessibility Is a Baseline

- Keyboard access, visible focus states, semantic HTML, labels, and WCAG AA contrast are required.
- Respect `prefers-reduced-motion`.
- Keep touch targets at least 44 x 44 px on mobile.

### Motion Needs a Job

- Use motion to explain entry, exit, hierarchy, or feedback.
- Animate only `transform` and `opacity`.
- Avoid `transition-all`, layout-thrashing scroll handlers, and decorative motion that competes
  with the task.

### Real Content Beats Placeholders

- Use realistic copy, believable data, and meaningful imagery.
- Prefer real assets or well-labeled temporary placeholders over lorem ipsum and generic dashboards.

## Design Floor

- Pick a visual direction deliberately instead of accepting the model's first default.
- Use typography, spacing, and composition to create hierarchy before adding effects.
- Prefer one strong visual decision over many weak ones.
- Keep palettes tight and consistent. One accent usually beats three competing accents.
- Respect the product's actual domain. A finance tool, editorial site, and playful consumer app
  should not converge on the same look.

## Engineering Floor

- Keep ownership clear: route and boundary components own data; presentational components render it.
- Prefer semantic HTML and existing UI primitives over custom click targets.
- Keep state no broader than necessary.
- Avoid performance work driven by superstition. Reach for memoization only when dependencies, child
  memoization, or measured cost justify it.
- Run the narrowest formatter, tests, lint, and typecheck for the changed slice before widening.

## Common Failures

Avoid the defaults that make frontend work look generated instead of designed:

- purple or indigo gradients on white when the brand did not ask for them
- on Persuade and Experience surfaces: Inter, Arial, Roboto, or system fonts as the automatic
  answer, and a centered hero plus three equal feature cards as the default layout (Operate
  surfaces keep the design system's type, where a system font stack is often right)
- `h-screen` full-height sections instead of `min-h-[100dvh]`
- card-inside-card sprawl, oversized rounding, and shadow-heavy surfaces
- fake names, round numbers, and filler marketing copy
- `transition-all`, layout-property animations, and perpetual motion everywhere

Before finalizing, name the look your first draft fell back on and change it unless the brief
asked for it.

For a fuller anti-pattern list, use
[references/audit-anti-patterns.md](references/audit-anti-patterns.md).

## Visual Direction

- Choose a direction deliberately.
- Start with a short design read, then pick one of the reference families in
  [references/aesthetic-directions.md](references/aesthetic-directions.md):
  - functional and restrained
  - Swiss or editorial
  - Japanese minimal
  - Scandinavian product UI
  - brutalist or tactical
  - expressive or premium launch surfaces
- Spend boldness in one place.
- Let the rest of the interface support that decision.

## Working Order

Use this order unless the task clearly needs another sequence:

1. Read the surface and stack.
2. Decide whether this is build, redesign, audit, review, or performance work.
3. Load the narrowest sub-skill.
4. Implement or analyze the highest-value surface first.
5. Validate immediately with the narrowest executable checks.
6. Only then widen to adjacent cleanup.

## Delivery Standard

A frontend change is not done until it:

- matches the surface mode and design system
- works at mobile and desktop breakpoints
- includes non-happy-path states
- passes the relevant validation commands
- leaves the codebase easier to extend

## Validation

Pick the narrowest executable validation for the touched surface:

- run the affected tests first
- run the repo's formatter for the touched surface when one exists
- run lint and typecheck for the touched app or package
- for React changes, run the repo-pinned `react-doctor` (`npx --no react-doctor --verbose --scope
  changed`; `design --verbose` for design audits), adding it as an exact-pinned dev dependency
  first if the repo lacks it; see [React diagnostics](../frontend-react/references/performance-and-validation.md#react-diagnostics)
- use the frontend audit rules in [../frontend-redesign/SKILL.md](../frontend-redesign/SKILL.md)
  when the user wants a formal UI review

## Sub-Skills

Load the relevant sub-skill rather than duplicating all detail here.

- [../frontend-redesign/SKILL.md](../frontend-redesign/SKILL.md) for redesigns, audits, and polish
- [../frontend-react/SKILL.md](../frontend-react/SKILL.md) for React and Next.js implementation
- [../code-review/SKILL.md](../code-review/SKILL.md) for explicit review-only tasks

## Pre-Flight Checklist

- The first viewport communicates the product, workflow, or content clearly.
- Visual hierarchy supports scanning before decoration.
- The layout collapses cleanly below `768px`.
- Focus states, labels, and keyboard flow are present.
- Loading, empty, error, and disabled states are handled.
- Motion respects reduced-motion and avoids layout thrash.
- Imagery and copy are intentional, not filler.
- Validation commands were selected and run for the changed surface.

## References

- [references/workflows.md](references/workflows.md) for build, redesign, audit, and design-system
  routing
- [references/aesthetic-directions.md](references/aesthetic-directions.md) for named visual
  directions
- [references/brief-inference.md](references/brief-inference.md) for optional brief triage when a
  design direction is under-specified
- [references/audit-anti-patterns.md](references/audit-anti-patterns.md) for a fuller list of
  AI-tell and low-quality UI patterns
- [references/high-end-execution.md](references/high-end-execution.md) for premium launch and
  high-distinction execution patterns
- [../frontend-redesign/SKILL.md](../frontend-redesign/SKILL.md) for redesign and audit workflow
- [../frontend-react/SKILL.md](../frontend-react/SKILL.md) for React and Next.js engineering
