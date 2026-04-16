# Agent Skills

A curated collection of skills for AI coding agents. Each skill is a self-contained knowledge module
that teaches an agent domain-specific patterns, best practices, and workflows.

## What Are Skills?

Skills are structured Markdown files that AI agents load on demand to gain expertise in a specific
domain. Each skill lives in its own directory with a `SKILL.md` entrypoint and optional reference
files. When a user's request matches a skill's description, the agent reads the skill file and
follows its instructions.

## Skills

### Software Engineering

| Skill                                                       | Description                                                                                                                           |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| [clean-code](clean-code/SKILL.md)                           | Clean Code principles from Robert C. Martin — naming, functions, comments, formatting, error handling, classes, and code smells       |
| [committing-code](committing-code/SKILL.md)                 | High-quality git commits — Conventional Commits, selective staging, logical splitting, safety checks                                  |
| [systematic-debugging](systematic-debugging/SKILL.md)       | Four-phase root cause analysis methodology — reproduction, evidence gathering, hypothesis testing, git bisect, differential debugging |
| [test-driven-development](test-driven-development/SKILL.md) | Strict TDD with red-green-refactor cycle, common rationalizations to avoid, and testing anti-patterns                                 |
| [task-orchestrator](task-orchestrator/SKILL.md)             | Decomposes complex tasks into subtasks, assigns to appropriate skills, runs independent work in parallel                              |

### Python

| Skill                                                   | Description                                                                                                            |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| [python](python/SKILL.md)                               | Comprehensive guide — code style (ruff), design patterns, type safety, project structure, configuration, anti-patterns |
| [python-async](python-async/SKILL.md)                   | asyncio patterns — event loops, coroutines, tasks, gather, semaphores, channels, async context managers                |
| [python-infrastructure](python-infrastructure/SKILL.md) | Packaging (pyproject.toml), performance optimization, background jobs (Celery), deployment workflows                   |
| [python-resilience](python-resilience/SKILL.md)         | Fault tolerance — retries with backoff, timeouts, context managers, resource cleanup, observability                    |
| [python-testing](python-testing/SKILL.md)               | pytest patterns — fixtures, mocking, parameterization, async tests, coverage, property-based testing                   |

### Rust

| Skill                                 | Description                                                                                                 |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| [rust](rust/SKILL.md)                 | Comprehensive guide — ownership, borrowing, lifetimes, error handling, traits, generics, API design, clippy |
| [rust-async](rust-async/SKILL.md)     | Async Rust with Tokio — runtime setup, task spawning, JoinSet, channels, streams, select, cancellation      |
| [rust-testing](rust-testing/SKILL.md) | Testing patterns — unit/integration/async tests, rstest, proptest, criterion benchmarks, doctests           |

### Tooling

| Skill                                                                     | Description                                                                                           |
| ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| [agent-browser](agent-browser/SKILL.md)                                   | Browser automation CLI for AI agents — session management, authentication, video recording, snapshots |
| [browser-use](browser-use/SKILL.md)                                       | Browser interactions for web testing, form filling, screenshots, and data extraction                  |
| [find-skills](find-skills/SKILL.md)                                       | Discovers and installs skills from the open skills ecosystem via the Skills CLI                       |
| [generating-custom-instructions](generating-custom-instructions/SKILL.md) | Generates and maintains custom instruction files for AI coding agents by analyzing codebase patterns  |
| [markdown-documentation](markdown-documentation/SKILL.md)                 | Markdown and GitHub Flavored Markdown formatting for documentation and technical writing              |
| [skill-creator](skill-creator/SKILL.md)                                   | Create, evaluate, and iteratively improve agent skills with eval-driven benchmarking                  |

### Diagramming

| Skill                       | Description                                                                                                                       |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| [mermaid](mermaid/SKILL.md) | Create, style, and render Mermaid diagrams — flowcharts, sequence, class, ERD, C4, state, architecture, with SVG/PNG/ASCII export |

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

The `SKILL.md` file starts with YAML frontmatter containing a `name` and `description`, followed by
the skill's instructions in the body.

## Installation

Clone this repo into your agent's skills directory:

```bash
git clone git@github.com:mitch-avis/agent-skills.git ~/.agents/skills
```

Most AI coding agents discover skills in `~/.agents/skills/` or `.agents/skills/` at the project
level. Consult your agent's documentation for the exact paths it searches.

## Linting

All Markdown files are validated with
[markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2):

```bash
markdownlint-cli2 "**/*.md"
```

Lines are wrapped at 100 characters. See [.markdownlint.json](.markdownlint.json) for the full
configuration.

## Acknowledgments

These skills were consolidated and rewritten from multiple open-source skill repositories. The
original 46 skills were merged into the 19 you see here — reorganized by domain, deduplicated, and
tailored to a consistent format.

### Source Repositories

| Repository                                                                                        | Original Skills                                                                                                                                                                                                                                                                                                                                                                 | Contributed To                                                                             |
| ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| [wshobson/agents](https://github.com/wshobson/agents)                                             | python-code-style, python-design-patterns, python-project-structure, python-error-handling, python-anti-patterns, python-type-safety, python-configuration, async-python-patterns, python-testing-patterns, python-packaging, python-performance-optimization, python-background-jobs, python-resilience, python-resource-management, python-observability, rust-async-patterns | python, python-async, python-testing, python-infrastructure, python-resilience, rust-async |
| [apollographql/skills](https://github.com/apollographql/skills)                                   | rust-best-practices                                                                                                                                                                                                                                                                                                                                                             | rust, rust-async, rust-testing                                                             |
| [zhanghandong/rust-skills](https://github.com/zhanghandong/rust-skills)                           | rust-router, rust-refactor-helper, rust-trait-explorer, rust-code-navigator, rust-learner, rust-symbol-analyzer, rust-call-graph, rust-deps-visualizer, rust-skill-creator, rust-daily                                                                                                                                                                                          | rust                                                                                       |
| [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills)       | clean-code, rust-pro, rust-async-patterns, software-architecture                                                                                                                                                                                                                                                                                                                | clean-code, rust, rust-async, task-orchestrator                                            |
| [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code)             | rust-patterns, rust-testing                                                                                                                                                                                                                                                                                                                                                     | rust, rust-testing                                                                         |
| [obra/superpowers](https://github.com/obra/superpowers)                                           | test-driven-development, systematic-debugging                                                                                                                                                                                                                                                                                                                                   | test-driven-development, systematic-debugging                                              |
| [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser)                         | agent-browser                                                                                                                                                                                                                                                                                                                                                                   | agent-browser                                                                              |
| [vercel-labs/skills](https://github.com/vercel-labs/skills)                                       | find-skills                                                                                                                                                                                                                                                                                                                                                                     | find-skills                                                                                |
| [browser-use/browser-use](https://github.com/browser-use/browser-use)                             | browser-use                                                                                                                                                                                                                                                                                                                                                                     | browser-use                                                                                |
| [aj-geddes/useful-ai-prompts](https://github.com/aj-geddes/useful-ai-prompts)                     | markdown-documentation                                                                                                                                                                                                                                                                                                                                                          | markdown-documentation                                                                     |
| [jeffallan/claude-skills](https://github.com/jeffallan/claude-skills)                             | rust-engineer                                                                                                                                                                                                                                                                                                                                                                   | rust                                                                                       |
| [404kidwiz/claude-supercode-skills](https://github.com/404kidwiz/claude-supercode-skills)         | rust-engineer                                                                                                                                                                                                                                                                                                                                                                   | rust                                                                                       |
| [leonardomso/rust-skills](https://github.com/leonardomso/rust-skills)                             | rust-skills                                                                                                                                                                                                                                                                                                                                                                     | rust                                                                                       |
| [wispbit-ai/skills](https://github.com/wispbit-ai/skills)                                         | rust-expert-best-practices-code-review                                                                                                                                                                                                                                                                                                                                          | rust                                                                                       |
| [github/awesome-copilot](https://github.com/github/awesome-copilot)                               | pytest-coverage, conventional-commit, git-commit, copilot-instructions-blueprint-generator, generate-custom-instructions-from-codebase, suggest-awesome-github-copilot-instructions                                                                                                                                                                                             | python-testing, committing-code, generating-custom-instructions                            |
| [softaworks/agent-toolkit](https://github.com/softaworks/agent-toolkit)                           | commit-work, mermaid-diagrams                                                                                                                                                                                                                                                                                                                                                   | committing-code, mermaid                                                                   |
| [imxv/pretty-mermaid-skills](https://github.com/imxv/pretty-mermaid-skills)                       | pretty-mermaid                                                                                                                                                                                                                                                                                                                                                                  | mermaid                                                                                    |
| [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates)                 | mermaid-diagram-specialist                                                                                                                                                                                                                                                                                                                                                      | mermaid                                                                                    |
| [axtonliu/axton-obsidian-visual-skills](https://github.com/axtonliu/axton-obsidian-visual-skills) | mermaid-visualizer                                                                                                                                                                                                                                                                                                                                                              | mermaid                                                                                    |
| [intellectronica/agent-skills](https://github.com/intellectronica/agent-skills)                   | beautiful-mermaid                                                                                                                                                                                                                                                                                                                                                               | mermaid                                                                                    |
| [anthropics/skills](https://github.com/anthropics/skills)                                         | skill-creator                                                                                                                                                                                                                                                                                                                                                                   | skill-creator                                                                              |

## License

[MIT](LICENSE)
