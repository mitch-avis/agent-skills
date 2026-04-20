# Instruction File Formats

Reference for all instruction file types recognized by major AI coding agents.

## Repository-Wide: `copilot-instructions.md`

- **Path**: `.github/copilot-instructions.md`
- **Scope**: every chat request and agent task in the repository
- **Recognized by**: GitHub Copilot, VS Code agents
- **Format**: Markdown, optional YAML frontmatter

Always-on. Use for project overview, build/test commands, global coding conventions, and
architecture constraints.

```markdown
---
applyTo: "**"
---
# Project Instructions

## Development Commands
- Build: `make build`
- Test: `make test`
- Lint: `make lint`
```

## Path-Specific: `*.instructions.md`

- **Path**: `.github/instructions/**/*.instructions.md`
- **Scope**: files matching the `applyTo` glob, or semantically matched to the current task via the
  `description`
- **Recognized by**: GitHub Copilot, VS Code agents
- **Format**: Markdown with YAML frontmatter

Applied automatically when the agent works on files matching the glob pattern. Use for
language-specific conventions, framework patterns, or rules scoped to a directory.

### Frontmatter Fields

| Field | Required | Description |
| --- | --- | --- |
| `name` | No | Display name shown in UI; defaults to filename |
| `description` | No | Short description (third person); aids semantic matching |
| `applyTo` | No | Glob relative to workspace root; omit for manual-only |

```markdown
---
description: 'Python coding conventions for this project'
applyTo: '**/*.py'
---
# Python Standards

- Use type hints for all function signatures
- Follow PEP 8 with project-specific overrides noted below
```

### Location Precedence

Searched recursively in these default locations:

| Scope | Default path |
| --- | --- |
| Workspace | `.github/instructions/` |
| Workspace (Claude format) | `.claude/rules/` |
| User profile | `~/.copilot/instructions/`, `~/.claude/rules/` |

Organize by subdirectory for large projects:

```text
.github/instructions/
├── frontend/
│   ├── react.instructions.md
│   └── accessibility.instructions.md
├── backend/
│   └── api-design.instructions.md
└── testing/
    └── unit-tests.instructions.md
```

## Multi-Agent Portable: `AGENTS.md`

- **Path**: repository root (and optionally subfolders)
- **Scope**: all chat requests in the workspace (or subfolder if nested)
- **Recognized by**: GitHub Copilot, Claude Code, VS Code agents
- **Format**: plain Markdown, no special frontmatter required

Use when multiple AI agents share the workspace and you want a single set of instructions recognized
by all of them. Subfolder `AGENTS.md` files apply instructions scoped to that subtree — useful in
monorepos.

## Claude-Compatible: `CLAUDE.md`

- **Path**: workspace root, `.claude/CLAUDE.md`, or `~/.claude/CLAUDE.md`
- **Scope**: always-on for the workspace or user
- **Recognized by**: Claude Code, VS Code (when enabled)
- **Format**: plain Markdown

Use when Claude Code is a primary agent. VS Code also reads `CLAUDE.md` as always-on instructions
when the `chat.useClaudeMdFile` setting is enabled.

Local variant `CLAUDE.local.md` is for machine-specific instructions not committed to version
control.

### Claude Rules Files

- **Path**: `.claude/rules/*.md`
- **Format**: Markdown with optional `paths` array (not `applyTo`)

```markdown
---
description: 'Python conventions'
paths:
  - '**/*.py'
---
# Python rules for Claude
```

## Reusable Skills: `SKILL.md`

- **Path**: `~/.agents/skills/<name>/SKILL.md` (global) or `.agents/skills/<name>/SKILL.md`
  (project-local)
- **Scope**: loaded on demand when the skill description matches the task
- **Recognized by**: Claude Code, VS Code agents with skill discovery
- **Format**: Markdown with required YAML frontmatter

Use for patterns reusable across multiple projects. Skills are not always-on — they are loaded only
when their description matches the current task.

### Frontmatter Fields

| Field | Required | Description |
| --- | --- | --- |
| `name` | Yes | Lowercase letters, numbers, hyphens only; max 64 chars |
| `description` | Yes | What it does and when to use it (third person); max 1024 chars |

```yaml
---
name: my-skill-name
description: >-
  Does X and Y for Z. Use when the user asks about X or needs to
  perform Y on Z files.
---
```

### Directory Layout

```text
skill-name/
├── SKILL.md              # Main entrypoint (loaded when triggered)
├── references/           # Deep-dive docs (loaded as needed)
│   └── topic.md
└── templates/            # Reusable templates or scripts
    └── example.sh
```

Keep `SKILL.md` under 500 lines. Use reference files for detailed content and link to them from the
main file.

## Instruction Priority

When multiple instruction types coexist, all are provided to the agent. In case of conflict,
higher-priority instructions take precedence:

1. Personal / user-level instructions (highest)
2. Repository instructions (`copilot-instructions.md`, `AGENTS.md`)
3. Organization-level instructions (lowest)

## Organization-Level Instructions

Defined at the GitHub organization level and automatically applied to all repositories the user has
access to. Lowest priority — repository instructions override them.

## Choosing the Right Format

| Question | Recommendation |
| --- | --- |
| One set of rules for the whole repo? | `copilot-instructions.md` |
| Different rules for different file types? | `*.instructions.md` with `applyTo` |
| Multiple AI agents in use? | `AGENTS.md` |
| Claude Code as primary agent? | `CLAUDE.md` |
| Patterns reusable across repos? | `SKILL.md` in `~/.agents/skills/` |
| Monorepo with distinct subprojects? | Subfolder `AGENTS.md` or scoped `*.instructions.md` |
