# Agent Skills

A curated collection of skills for AI coding agents. Each skill is a self-contained knowledge
module that teaches an agent domain-specific patterns, best practices, and workflows.

## What Are Skills?

Skills are structured Markdown files that AI agents load on demand to gain expertise in a specific
domain. Each skill lives in its own directory with a `SKILL.md` entrypoint and optional reference
files. When a user's request matches a skill's description, the agent reads the skill file and
follows its instructions.

## Skills

### Software Engineering

| Skill | Description |
| ----- | ----------- |
| [clean-code](clean-code/SKILL.md) | Clean Code principles from Robert C. Martin — naming, functions, comments, formatting, error handling, classes, and code smells |
| [systematic-debugging](systematic-debugging/SKILL.md) | Four-phase root cause analysis methodology — reproduction, evidence gathering, hypothesis testing, git bisect, differential debugging |
| [test-driven-development](test-driven-development/SKILL.md) | Strict TDD with red-green-refactor cycle, common rationalizations to avoid, and testing anti-patterns |
| [task-orchestrator](task-orchestrator/SKILL.md) | Decomposes complex tasks into subtasks, assigns to appropriate skills, runs independent work in parallel |

### Python

| Skill | Description |
| ----- | ----------- |
| [python](python/SKILL.md) | Comprehensive guide — code style (ruff), design patterns, type safety, project structure, configuration, anti-patterns |
| [python-async](python-async/SKILL.md) | asyncio patterns — event loops, coroutines, tasks, gather, semaphores, channels, async context managers |
| [python-infrastructure](python-infrastructure/SKILL.md) | Packaging (pyproject.toml), performance optimization, background jobs (Celery), deployment workflows |
| [python-resilience](python-resilience/SKILL.md) | Fault tolerance — retries with backoff, timeouts, context managers, resource cleanup, observability |
| [python-testing](python-testing/SKILL.md) | pytest patterns — fixtures, mocking, parameterization, async tests, coverage, property-based testing |

### Rust

| Skill | Description |
| ----- | ----------- |
| [rust](rust/SKILL.md) | Comprehensive guide — ownership, borrowing, lifetimes, error handling, traits, generics, API design, clippy |
| [rust-async](rust-async/SKILL.md) | Async Rust with Tokio — runtime setup, task spawning, JoinSet, channels, streams, select, cancellation |
| [rust-testing](rust-testing/SKILL.md) | Testing patterns — unit/integration/async tests, rstest, proptest, criterion benchmarks, doctests |

### Tooling

| Skill | Description |
| ----- | ----------- |
| [agent-browser](agent-browser/SKILL.md) | Browser automation CLI for AI agents — session management, authentication, video recording, snapshots |
| [browser-use](browser-use/SKILL.md) | Browser interactions for web testing, form filling, screenshots, and data extraction |
| [find-skills](find-skills/SKILL.md) | Discovers and installs skills from the open skills ecosystem via the Skills CLI |
| [markdown-documentation](markdown-documentation/SKILL.md) | Markdown and GitHub Flavored Markdown formatting for documentation and technical writing |

## Directory Structure

Each skill follows the same layout:

```text
skill-name/
├── SKILL.md              # Main skill file (entrypoint)
├── references/           # Optional deep-dive reference docs
│   ├── topic-a.md
│   └── topic-b.md
└── templates/            # Optional reusable templates
    └── example.sh
```

The `SKILL.md` file starts with YAML frontmatter containing a `name` and `description`, followed
by the skill's instructions in the body.

## Installation

Clone this repo into your agent's skills directory:

```bash
git clone git@github.com:mitch-avis/agent-skills.git ~/.agents/skills
```

Most AI coding agents discover skills in `~/.agents/skills/` or `.agents/skills/` at the project
level. Consult your agent's documentation for the exact paths it searches.

## Linting

All Markdown files are validated with [markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2):

```bash
markdownlint-cli2 "**/*.md"
```

Lines are wrapped at 100 characters. See [.markdownlint.json](.markdownlint.json) for the full
configuration.

## License

[MIT](LICENSE)
