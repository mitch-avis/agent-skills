# Frontend anti-patterns

Use this when a surface feels generic, sloppy, or AI-generated and you need more precise language
for what is wrong.

## Layout tells

- Centered hero plus three equal cards as the default structure
- Card inside card inside card, with no hierarchy benefit
- `100vh` full-screen sections that break on mobile browsers
- Fixed-width desktop layouts squeezed onto mobile instead of being recomposed
- Sidebar-first dashboards when the task would scan better with top-level grouping

## Typography tells

- Generic default fonts with no relation to the product
- Headings that rely on color accents instead of scale and weight
- Body text that runs too wide or too faint
- Numbers that should align but do not use tabular figures or monospace support
- Eyebrow labels and numbered sections added by default instead of because the content needs them

## Surface tells

- Purple or indigo gradients standing in for brand direction
- Oversized border radii and soft shadows on everything
- Blur and glass effects used as decoration rather than material language
- Borders, shadows, and fills all competing on the same surface
- Empty regions that rely on texture, chrome, or glow instead of content, proof, or product state

## Motion tells

- `transition-all`
- The same fade-up animation on every section
- Decorative perpetual motion with no state or hierarchy purpose
- Layout-property animation where transform or opacity would do
- Motion that vanishes useful feedback under reduced-motion instead of offering a quieter version

## Content tells

- Vague headlines and feature blurbs that could describe any product
- Fake names, fake round numbers, and placeholder companies
- Proof points that claim value without showing anything specific
- Decorative images that do not help the task or story
- AI filler words such as "seamless", "elevate", "next-gen", or "game-changer"

## Component tells

- Monolithic components controlled by stacks of booleans
- Dialogs and tooltips used where inline disclosure would be clearer
- Icon systems mixed without a reason
- Loading, empty, error, and disabled states treated as afterthoughts

## Escalation signals

When several of these appear together, treat the problem as systemic rather than local.
That usually means the redesign should start with hierarchy, tokens, and layout structure before
surface polish.
