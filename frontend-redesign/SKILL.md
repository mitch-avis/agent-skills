---
name: frontend-redesign
description: >-
  Use before reworking an existing site, app, dashboard, settings page, or component that needs
  stronger hierarchy, typography, spacing, states, responsiveness, accessibility, or interaction
  quality. Preserves the existing workflow and implementation constraints while improving the
  design.
---

# Frontend Redesign

Use this for existing interfaces.
It is the deep redesign and audit companion to `frontend-design`.

## When to Use

- Redesigning or polishing an existing site or app
- Auditing a UI that feels generic, noisy, inaccessible, or unfinished
- Upgrading visual quality without changing core behavior
- Making a React, Next.js, or vanilla frontend feel more intentional while preserving the stack

## Redesign Read

Before editing, identify:

1. what must not change: workflow, routes, real copy, business rules, supported states
2. what is fair to change: hierarchy, typography, spacing, surfaces, motion, component treatment
3. whether this is a preserve-the-identity redesign or a replace-the-visual-world redesign

Write one line that makes this explicit before editing.

## Preserve Rules

- Preserve product truth and working behavior unless the user asked to change them.
- Keep the existing framework and styling system unless the user explicitly asked for migration.
- Do not smuggle a rewrite into a redesign task.
- Re-check empty, loading, and error states after every visual pass.

## Audit Order

Work in this order.
Earlier layers usually create the later symptoms.

1. structure and layout
2. typography and hierarchy
3. color and surfaces
4. interaction and states
5. content realism and consistency
6. responsive behavior
7. motion and finishing details

## Audit Checklist

Use this section for fast triage.
For a fuller discipline-by-discipline audit, read
[references/audit-checklist.md](references/audit-checklist.md).

### Structure And Layout

- Is the first viewport about the real product or about generic marketing furniture?
- Is the primary action obvious without relying on color alone?
- Is the layout too centered, too symmetrical, or too card-heavy?
- Are containers, gutters, and max widths consistent?
- Does mobile collapse cleanly, or is desktop structure just being squeezed smaller?

### Typography And Hierarchy

- Are the fonts generic or mismatched to the product?
- Do headings create clear hierarchy before decoration does?
- Are body lines too wide, too dense, or too low-contrast?
- Do numbers need tabular treatment or monospace support?

### Color And Surfaces

- Is there one clear palette, or are warm and cool neutrals fighting each other?
- Is the interface leaning on purple-tech defaults the brand never asked for?
- Do surfaces use shadow, border, blur, or texture intentionally?
- Do dark and light sections feel coherent, or accidental?

### Interaction And States

- Are hover, focus, and pressed states present and readable?
- Are loading, empty, error, disabled, and success states designed at all?
- Are links, buttons, and navigation states visually differentiated?
- Are dialogs, drawers, and tooltips reachable and understandable?

### Content And Realism

- Is the copy concrete, or filled with AI filler phrases?
- Are names, dates, stats, and examples believable?
- Are images and icons helping the product story, or just decorating whitespace?

For a focused pass on believable copy, data, and proof, read
[references/content-authenticity.md](references/content-authenticity.md).

## Common Redesign Targets

- Replace generic three-card feature rows with asymmetry, rhythm, or a more purposeful grouping.
- Replace `100vh` hero sections with `100dvh`-safe layouts.
- Replace filler badges, giant rounding, and soft gray shadows with product-specific treatment.
- Replace dead links and placeholder CTAs with real navigation or clearly disabled states.
- Replace unstructured spacing with a coherent vertical rhythm.

## Upgrade Order

When improving an existing surface, prefer this sequence:

1. clean up typography and spacing scale
2. fix primary hierarchy and CTA placement
3. repair states and accessibility
4. simplify surfaces and component treatment
5. add one stronger visual idea
6. finish with restrained motion and polish

## Review Lenses

Separate visual critique from implementation audit.
Both matter.

- Visual critique asks whether hierarchy, typography, spacing, imagery, and motion fit the product.
- Implementation audit asks whether the rendered result still holds up under accessibility,
  responsiveness, theming, state coverage, and performance constraints.
- A redesign is incomplete if the page became prettier but lost labels, focus treatment, or stable
  mobile behavior.

## Example Findings

### Example: SaaS Settings Page

- Problem: every setting block is a card inside a card, with low-contrast labels and no empty
  states
- Upgrade: flatten the structure, tighten the hierarchy, add section intros, and design the empty
  and success states first

### Example: Launch Page

- Problem: centered hero, purple glow, three equal feature cards, vague copy
- Upgrade: lead with a clearer product frame, choose a tighter palette, vary composition, and make
  the proof points specific

## Validation

- Run the narrowest existing tests for changed components or pages.
- Run the repo formatter, lint, and typecheck for the touched app or package.
- For React surfaces, run the repo-pinned `react-doctor` (`npx --no react-doctor --verbose --scope
  changed`, or `design --verbose` for focused UI checks); see [React diagnostics](../frontend-react/references/performance-and-validation.md#react-diagnostics).
- If the task is an explicit review or audit, route to `../code-review/SKILL.md` and use the audit
  and finish-pass rules in [references/audit-and-finish.md](references/audit-and-finish.md).

## Escalation

- If the requested redesign is actually a new surface, go back to `../frontend-design/SKILL.md`.
- If the redesign requires React architecture, state, or performance changes, also read
  `../frontend-react/SKILL.md`.
- If the user explicitly asks for review findings, read `../code-review/SKILL.md` first.

## References

- [references/audit-checklist.md](references/audit-checklist.md) for a longer redesign checklist by
  discipline
- [references/content-authenticity.md](references/content-authenticity.md) for realistic copy,
  names, metrics, and proof patterns
- [references/audit-and-finish.md](references/audit-and-finish.md) for the quality floor and the
  bounded redesign review pass
