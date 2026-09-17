# Redesign audit checklist

Use this when a redesign needs a fuller pass than the short checklist in `frontend-redesign`.

## Typography

- Browser default fonts or generic UI fonts used without product intent
- Headlines too weak to carry hierarchy
- Body text too wide, too dense, or too low-contrast
- Only regular and bold weights used, with no intermediate hierarchy
- Numeric data that should align but does not

## Color and surfaces

- More than one accent color competing for attention
- Warm and cool neutrals mixed without reason
- Generic black shadows or purple-tech gradients substituting for brand direction
- Empty surfaces with no product evidence or material depth
- Dark sections dropped into a light page, or the reverse, with no coherent palette logic

## Layout

- Everything centered and symmetrical even when the content hierarchy is uneven
- Equal-height card grids where the content lengths are clearly different
- Missing max-width constraints or unstable gutters
- Buttons, titles, or price blocks misaligned across sibling cards
- No overlap, depth, or compositional variation when the page needs stronger hierarchy

## Interaction and states

- No hover or pressed feedback
- Missing focus treatment
- Empty, loading, error, disabled, and success states not designed
- Dead links, fake CTAs, or no current-page indication in navigation
- Motion that uses layout properties or ignores reduced-motion

## Content and realism

- Generic product copy that could fit any startup
- Fake names, fake round stats, or identical blog dates
- Unclear or apologetic error messages
- Proof points that claim outcomes without showing real evidence

## Components and omissions

- Card shells used by default instead of because elevation communicates something
- Dialogs or accordions used as generic filler patterns
- Missing back navigation, 404 treatment, privacy links, or skip links where the surface calls for
  them
- Missing form validation and recovery guidance
