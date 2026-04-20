---
name: markdown-documentation
description: >-
  Formats Markdown and GitHub Flavored Markdown for documentation, READMEs, and technical writing.
  Covers text formatting, lists, links, images, tables, code blocks, collapsible sections, alerts,
  and mermaid diagrams. Use when writing or formatting Markdown documents.
---

# Markdown Documentation

## Overview

Master markdown syntax and best practices for creating well-formatted, readable documentation using
standard Markdown and GitHub Flavored Markdown (GFM).

## When to Use

- README files
- Documentation pages
- GitHub/GitLab wikis
- Blog posts
- Technical writing
- Project documentation

## Quick Start

```markdown
# Heading 1

## Heading 2

**Bold text**, *italic text*, ~~strikethrough~~

- Unordered list item
- Another item

1. Ordered list item
2. Another item

[Link text](https://example.com)

![Alt text](image.png)
```

```markdown
| Column A | Column B |
| -------- | -------- |
| Cell 1   | Cell 2   |
```

## Reference Guides

Detailed implementations in the `references/` directory:

| Topic                | File                                                   | Load When                                     |
| -------------------- | ------------------------------------------------------ | --------------------------------------------- |
| Text Formatting      | references/text-formatting.md                          | Bold, italic, strikethrough, emphasis         |
| Lists                | references/lists.md                                    | Ordered, unordered, nested, task lists        |
| Links and Images     | references/links-and-images.md                         | Hyperlinks, images, code blocks, tables       |
| Extended GFM Syntax  | references/extended-syntax-github-flavored-markdown.md | Footnotes, task lists, autolinks, emoji       |
| Collapsible Sections | references/collapsible-sections.md                     | Details/summary, syntax highlighting, badges  |
| Alerts and Callouts  | references/alerts-and-callouts.md                      | Note, tip, important, warning, caution blocks |
| Mermaid Diagrams     | references/mermaid-diagrams.md                         | Embedding diagrams in Markdown documents      |

## Best Practices

### Line Length

- **Maximum line length: 100 characters** for prose text
- Code blocks and tables are exempt from the line-length limit
- Wrap long prose at natural sentence or clause boundaries
- Use semantic line breaks — start a new line after each sentence or at logical clause boundaries

### Formatting Standards

Configure `markdownlint` for enforcement. Recommended `.markdownlint.json`:

```json
{
    "line-length": {
        "line_length": 100,
        "heading_line_length": 100,
        "code_blocks": false,
        "tables": false
    },
    "no-inline-html": false,
    "no-emphasis-as-heading": false,
    "no-duplicate-heading": {
        "siblings_only": true
    }
}
```

### Code Blocks

- **Always specify a language** on fenced code blocks — never use bare `` ``` ``. Use `text` for
  plain text or pseudocode.
- Common languages: `rust`, `python`, `bash`, `toml`, `json`, `yaml`, `typescript`, `sql`,
  `markdown`, `text`
- Use the correct language for the content — syntax highlighting depends on it

### Tables

- Surround tables with blank lines (before and after)
- Ensure consistent column counts across all rows
- Use leading and trailing pipes on every row
- Simple separator style (`| --- | --- |`) is preferred over padded separators for maintainability

### General Rules

- Use blank lines around headings, lists, code blocks, and tables
- Don't wrap text mid-table-row — table rows must be single lines
- Use ATX-style headings (`#` prefix), not setext (underline)
- No trailing whitespace on any line
- End files with a single newline
- No consecutive blank lines

### DO

- Use descriptive link text
- Include table of contents for long documents
- Add alt text to images
- Use code blocks with language specification
- Keep prose lines under 100 characters
- Use relative links for internal docs
- Add badges for build status, coverage, etc.
- Include examples and screenshots
- Use semantic line breaks
- Test all links regularly

### DON'T

- Use "click here" as link text
- Forget alt text on images
- Mix HTML and Markdown unnecessarily
- Use absolute paths for local files
- Create walls of text without breaks
- Skip language specification in code blocks
- Use images for text content (accessibility)
- Use bare `` ``` `` without a language tag
- Wrap lines mid-table-row

## Related Skills

- [mermaid](../mermaid/SKILL.md) — embed diagrams inside Markdown documentation
