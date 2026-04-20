---
name: generating-custom-instructions
description: >-
  Generates and maintains custom instruction files for AI coding agents. Analyzes codebase patterns,
  conventions, and tooling to produce agent-agnostic instruction files (copilot-instructions.md,
  .instructions.md, AGENTS.md, CLAUDE.md). Use when setting up a new project for AI assistance,
  onboarding a repository, updating stale instructions, or refreshing conventions after a major
  refactor or migration.
---

# Generating Custom Instructions

Analyze a codebase and produce instruction files that teach AI coding agents the project's
conventions, tooling, and architecture. Works for any agent that reads Markdown instruction files
(GitHub Copilot, Claude Code, or others).

## When to Use

- New project needs AI instruction files
- Existing project has no instructions or outdated ones
- Major refactor, migration, or dependency upgrade changed conventions
- Team wants to standardize how agents interact with the codebase
- Consolidating scattered or contradictory instruction files

## Process

### 1. Inventory Existing Instructions

Before creating anything, discover what already exists:

```bash
find . -name 'copilot-instructions.md' \
       -o -name '*.instructions.md' \
       -o -name 'AGENTS.md' \
       -o -name 'CLAUDE.md' \
       -o -name 'GEMINI.md' \
       -o -name 'SKILL.md' \
  | head -50
```

Read each file. Note what topics are covered, what is outdated, and what is missing. Do not create
duplicates.

### 2. Analyze the Codebase

Scan the project to extract facts. Never assume — verify everything against actual code.

**Stack and versions** — detect from config files, lockfiles, and CI manifests:

- Languages and their versions
- Frameworks, their versions, and version constraints
- Key libraries and their pinned or constrained versions

**Tooling commands** — extract exact invocations:

- Build: how to compile, bundle, or package
- Test: how to run the full suite and subsets
- Lint and format: which tools, how to invoke them
- CI: what the pipeline runs and in what order

**Conventions** — observe from the code, do not invent:

- Naming patterns for files, variables, functions, and types
- Module organization and import style
- Error handling approach (Result types, exceptions, error codes)
- Logging patterns and levels
- Documentation style (docstrings, JSDoc, XML comments)
- Test organization, naming, and assertion style

**Architecture:**

- Folder structure and layer boundaries
- Entry points and key modules
- Communication patterns (sync, async, event-driven, RPC)
- Data flow and state management approach

### 3. Draft Instruction Content

Write instructions based solely on observed patterns.

**Include:**

- Build, test, lint, and format commands (exact invocations)
- Repository structure overview with the purpose of each top-level directory
- Naming conventions that diverge from language defaults
- Error handling and logging patterns specific to the project
- Testing approach: framework, patterns, what to test
- Security practices enforced in the codebase
- Architecture constraints and layer boundaries
- Dependency management rules (lockfile policy, approved sources)

**Skip:**

- Anything a linter or formatter already enforces
- General language or framework knowledge the agent already has
- Obvious conventions (PascalCase in C#, snake_case in Python)
- Aspirational rules not reflected in the actual code

**Writing style:**

- State rules directly: "Do X" / "Never Y" / "Prefer X over Y"
- Include reasoning behind non-obvious rules: "Use `date-fns` instead of `moment.js` — moment is
  deprecated and bloats the bundle"
- Show preferred and avoided patterns with short code examples
- Keep each instruction self-contained — one idea per bullet
- Be concise — every sentence must earn its token cost

### 4. Choose File Format and Location

Select the right file type for each set of instructions. See
[instruction-file-formats.md](references/instruction-file-formats.md) for full format
specifications.

| Scope             | File                                     | When to use                                               |
| ----------------- | ---------------------------------------- | --------------------------------------------------------- |
| Repository-wide   | `.github/copilot-instructions.md`        | Stack overview, build/test commands, global conventions   |
| Path-specific     | `.github/instructions/*.instructions.md` | Rules for specific file types, frameworks, or directories |
| Multi-agent       | `AGENTS.md` (root or subfolder)          | When multiple AI agents share the workspace               |
| Claude-compatible | `CLAUDE.md`                              | When Claude Code is used alongside other agents           |
| Reusable skill    | `~/.agents/skills/*/SKILL.md`            | Patterns reusable across multiple projects                |

**Frontmatter** for path-specific files:

```yaml
---
description: 'Brief third-person description of what these rules cover'
applyTo: '**/*.py'
---
```

- `description`: what the instructions cover (third person, used for discovery)
- `applyTo`: glob pattern relative to workspace root; omit to require manual attachment

### 5. Organize the File Set

Structure instructions by concern, not by agent:

```text
.github/
├── copilot-instructions.md          # Repository-wide: stack, build, test, structure
└── instructions/
    ├── python.instructions.md       # Python conventions
    ├── typescript.instructions.md   # TypeScript conventions
    ├── testing.instructions.md      # Test-writing rules
    └── docs.instructions.md         # Documentation standards
AGENTS.md                            # (optional) Multi-agent portable copy
```

**Principles:**

- One file per concern — do not mix unrelated rules
- Repository-wide file stays concise (aim for under 200 lines)
- Path-specific files target narrow globs
- Avoid redundancy — reference shared rules with Markdown links instead of duplicating them
- Version-control instruction files and review them like code

### 6. Validate

After generating instructions:

1. **Accuracy**: every stated convention exists in the codebase
2. **Completeness**: build/test/lint commands work as written
3. **No redundancy**: no duplicated guidance across files
4. **Conciseness**: every sentence changes agent behavior
5. **Freshness**: instructions match the current state, not a past version

## Content Template

Starting point for `.github/copilot-instructions.md`. Strip sections that do not apply; add
project-specific ones as needed.

```markdown
# Project Instructions

## Overview

[One sentence: what this project is and its primary technology.]

## Development Commands

- Build: `[exact command]`
- Test: `[exact command]`
- Lint: `[exact command]`
- Format: `[exact command]`

## Repository Structure

- `src/`: [purpose]
- `tests/`: [purpose]
- `docs/`: [purpose]

## Coding Conventions

[Only non-obvious, project-specific rules with reasoning.]

## Error Handling

[Project's approach — patterns, not platitudes.]

## Testing

[Framework, patterns, what to test, naming conventions.]

## Security

[Input validation, auth patterns, sensitive data handling.]
```

## Handling Migrations

When a project undergoes a major change (framework upgrade, architecture shift, dependency swap),
update instructions to reflect the new state:

1. **Diff the change**: compare before and after to identify transformed patterns
2. **Update rules**: rewrite instructions to match the new conventions
3. **Document transitions**: note deprecated patterns and their replacements
4. **Flag incomplete migrations**: if old-style code remains, say so explicitly so the agent does
   not propagate the old patterns

Example migration note:

```markdown
## Migration: React class components → hooks (in progress)

- All new components MUST use functional components with hooks
- Existing class components in `src/legacy/` will be migrated incrementally
- Do not convert class components unless explicitly asked
- When modifying a class component, prefer minimal changes over full conversion
```

When before/after patterns are useful, document the transformation:

```markdown
## Changed Pattern: Error Handling

BEFORE (pre-migration):
  throw new Error("not found")

AFTER (current convention):
  return Result.err(new NotFoundError(id))
```

## Anti-Patterns

- **Aspirational rules**: describing desired state instead of actual state
- **Framework tutorials**: explaining what React or Django is
- **Linter-enforced rules**: restating what ESLint, Ruff, or Clippy already catches
- **Kitchen-sink files**: 500+ line instruction files that try to cover everything
- **Stale instructions**: rules from a previous version of the stack
- **Conflicting files**: multiple instruction files giving contradictory guidance
- **Agent-specific scaffolding**: instructions that only work for one agent
- **Template variables**: placeholder syntax that no agent can resolve at runtime

## Guiding Principles

1. **Observe, don't assume** — every rule must trace to an actual codebase pattern
2. **Earn your tokens** — if it doesn't change agent behavior, cut it
3. **Non-obvious over obvious** — focus on what the agent cannot infer alone
4. **Concrete over abstract** — show a code example instead of prose description
5. **Current over aspirational** — document what IS, not what SHOULD BE
6. **One concern per file** — split instructions by topic for targeted application
7. **Agent-agnostic** — write for any Markdown-reading agent, not a specific one

## Related Skills

- [code-review](../code-review/SKILL.md) — analyze codebase patterns to extract conventions
