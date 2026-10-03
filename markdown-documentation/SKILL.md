---
name: markdown-documentation
description: >-
  Use before writing or editing any Markdown file (README, docs, AGENTS.md, CLAUDE.md, changelogs,
  plans). Covers GitHub Flavored Markdown formatting, lists, links, tables, code blocks, alerts,
  collapsible sections, and mermaid, plus the markdownlint-cli2 check on changed files.
---

# Markdown Documentation

House rules for Markdown that renders well on GitHub and passes markdownlint. Syntax details live
in the references; load one only when the task needs it.

## Reference Guides

| Topic | File | Load When |
| --- | --- | --- |
| Text formatting | [text-formatting.md](references/text-formatting.md) | Bold, italic, strikethrough, emphasis |
| Lists | [lists.md](references/lists.md) | Ordered, unordered, nested, and task lists |
| Links, images, code blocks, tables | [links-and-images.md](references/links-and-images.md) | Link and image syntax, fenced code, table syntax |
| Extended GFM syntax | [extended-syntax-github-flavored-markdown.md](references/extended-syntax-github-flavored-markdown.md) | Footnotes, task lists, autolinks, emoji |
| Collapsible sections, highlighting, badges | [collapsible-sections.md](references/collapsible-sections.md) | `<details>`/`<summary>`, syntax highlighting, badges |
| Alerts and callouts | [alerts-and-callouts.md](references/alerts-and-callouts.md) | Note, tip, important, warning, caution blocks |
| Mermaid diagrams | [mermaid skill](../mermaid/SKILL.md) | Embedding diagrams in Markdown documents |
| New document skeleton | [doc-template.md](templates/doc-template.md) | Writing a new README or doc page from scratch |

## Line Length and Wrapping

- Fill prose to 100 columns: wrap each paragraph so lines run as close to 100 characters as they
  can, not one sentence per line.
- When you edit a paragraph, re-fill only that paragraph; leave untouched paragraphs alone so the
  diff stays small.
- Code blocks and tables are exempt from the limit. Table rows stay on one line.

## Linting

Run `markdownlint-cli2` on every changed Markdown file, including agent instruction files
(`AGENTS.md`, `CLAUDE.md`, `SKILL.md`), and fix what it reports:

- If the repo has its own config (`.markdownlint.json`, `.markdownlint.yaml`, or
  `.markdownlint-cli2.*`), run `markdownlint-cli2 <files>` from the repo root so that config
  applies.
- Otherwise run `markdownlint-cli2 --config ~/.markdownlint-cli2.yaml <files>`.

Don't create a markdownlint config in a repo that lacks one unless asked.

## Code Blocks

- Give every fenced block a language. Use `text` for plain output or pseudocode.
- Pick the language that matches the content (`bash`, `python`, `rust`, `toml`, `yaml`, `json`,
  `sql`, `markdown`), because syntax highlighting depends on it.

## Tables

- Surround tables with blank lines, and give every row the same number of cells.
- Use leading and trailing pipes, and the simple `| --- |` separator rather than padded columns.

## General Rules

- ATX headings (`#`), with blank lines around headings, lists, code blocks, and tables.
- No trailing whitespace, no consecutive blank lines, and a single newline at the end of the file.

## Links, Images, and Accessibility

- Use descriptive link text, not "click here".
- Use relative links for files inside the repo.
- Give every image alt text, and don't put text content in images.

## Prose in Source Files

Comments and docstrings follow the language's own conventions (for example, Google-style
docstrings in Python). Start with a one-line summary, separate it from the body with a blank line,
use consistent section labels, and fill the body to the same 100-column limit instead of aligning
text into columns.

## Related Skills

- [mermaid](../mermaid/SKILL.md) — embed diagrams inside Markdown documentation
