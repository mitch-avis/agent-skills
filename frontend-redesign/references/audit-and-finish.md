# Redesign audit and finish

Use this reference when the task is a redesign, polish pass, or frontend quality review.

## Two lenses

Review the surface from both angles.

- **Visual critique:** hierarchy, typography, spacing, imagery, motion, product fit
- **Implementation audit:** accessibility, responsiveness, theming, state coverage, performance,
  interaction integrity

A redesign passes only when both lenses hold.

## Quality floor

Check these together in the same inspection round:

- contrast meets the intended accessibility floor
- headings, body copy, and spacing create hierarchy without decorative crutches
- focus, hover, disabled, loading, empty, and error states are present
- the first viewport demonstrates the real product or task, not generic page furniture
- motion clarifies change without overwhelming the task
- browser-owned details such as selection, caret, focus, and scroll behavior do not feel forgotten

## First viewport rule

Treat the first viewport as a thesis.

- For a launch surface, it should explain the offer and action quickly.
- For an operating surface, it should reveal the task and key state quickly.
- For a reading surface, it should establish structure and wayfinding quickly.

If a user can leave after one viewport and only describe a mood, the redesign is not yet specific
enough.

## Prove, do not claim

- Prefer real product evidence, real UI states, or believable demonstration data.
- Replace vague proof points with concrete details.
- Do not hide a thin product story behind gradient effects or card chrome.

## Finish pass

Use bounded review rounds.

1. inspect desktop and mobile together
2. batch the meaningful fixes
3. confirm with one more round
4. stop once the second round is materially clean or the remaining issues are explicit tradeoffs

Do not drift into endless micro-polish loops.
