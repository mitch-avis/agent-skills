# Instruction File Formats

Reference for all instruction file types recognized by major AI coding agents.

## Multi-Agent Portable: `AGENTS.md`

- **Path**: repository root (and optionally subfolders)
- **Scope**: all chat requests in the workspace (or subfolder if nested)
- **Recognized by**: GitHub Copilot, Codex, VS Code agents, and Claude Code (see below)
- **Format**: plain Markdown, no special frontmatter required

The default home for a repository's rules: one file that every agent can read. Subfolder
`AGENTS.md` files apply instructions scoped to that subtree, which is useful in monorepos.

Claude Code reads `AGENTS.md` directly only when there is no `CLAUDE.md`, `.claude/CLAUDE.md`, or
`CLAUDE.local.md` in the working directory or above it. As soon as any of those exists, it reads
the `CLAUDE.md` files instead. The reliable bridge is a thin `CLAUDE.md` whose first line imports
the shared file:

```markdown
@AGENTS.md

<!-- Claude Code-only notes go below the import. -->
```

Claude Code never reads anything under a `.agents/` directory on its own; reference those files
from `AGENTS.md` if agents need them.

## Claude Code: `CLAUDE.md`

- **Path**: workspace root, `.claude/CLAUDE.md`, or `~/.claude/CLAUDE.md`
- **Scope**: always-on for the workspace or user
- **Recognized by**: Claude Code, VS Code (when enabled)
- **Format**: plain Markdown

Keep it thin: `@AGENTS.md` plus any Claude Code-only notes, so the rules live in one place. VS Code
also reads `CLAUDE.md` as always-on instructions when the `chat.useClaudeMdFile` setting is
enabled.

Local variant `CLAUDE.local.md` is for machine-specific instructions not committed to version
control.

### Claude Rules Files

- **Path**: `.claude/rules/*.md` (project) or `~/.claude/rules/*.md` (user)
- **Format**: Markdown with optional frontmatter. `paths` is the only field Claude Code reads; any
  other field (such as `description`) is ignored.
- **Loading**: a rule without `paths` loads at session start; a rule with `paths` loads when Claude
  reads or edits a matching file.

```markdown
---
paths:
  - '**/*.py'
---
# Python rules for Claude
```

## Copilot Repository-Wide: `copilot-instructions.md`

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

## Copilot Path-Specific: `*.instructions.md`

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

## Reusable Skills: `SKILL.md`

- **Path**: depends on the agent. Claude Code loads only `~/.claude/skills/<name>/SKILL.md`
  (personal) and `.claude/skills/<name>/SKILL.md` (project); a shared collection elsewhere, such as
  `~/.agents/skills/`, needs a symlink per skill into `~/.claude/skills/`. Other agents may read
  `~/.agents/skills/` or `.agents/skills/` directly; check their docs.
- **Scope**: loaded on demand when the skill description matches the task
- **Recognized by**: Claude Code, VS Code agents with skill discovery, and other Agent Skills hosts
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

Precedence differs by tool:

- **Claude Code**: every discovered file is concatenated into context; none overrides another.
  User files load before project files and directories load from the root down, so the most
  specific file is read last, but on a direct conflict Claude may follow either. Keep the layers
  consistent, and state precedence in words where it matters (for example, "this repo's
  `AGENTS.md` wins over personal defaults").
- **GitHub Copilot**: all instruction types are provided, and on conflict personal instructions
  win over repository instructions, which win over organization instructions.

### Copilot Organization-Level Instructions

Defined at the GitHub organization level and applied to every repository the user can access.
Lowest priority in Copilot; repository instructions override them.

## Choosing the Right Format

| Question | Recommendation |
| --- | --- |
| One set of rules for the whole repo? | `AGENTS.md`, plus a thin `CLAUDE.md` with `@AGENTS.md` |
| Different rules for different file types? | `.claude/rules/*.md` with `paths` (Copilot: `*.instructions.md` with `applyTo`) |
| Copilot also in use? | Optional `.github/copilot-instructions.md` pointing at or mirroring `AGENTS.md` |
| Patterns reusable across repos? | A skill, linked into each agent's skills directory |
| Monorepo with distinct subprojects? | Subfolder `AGENTS.md` (with its own thin `CLAUDE.md`) |
