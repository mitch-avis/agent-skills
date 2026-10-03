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

| Skill | Description |
| --- | --- |
| [code-review](code-review/SKILL.md) | Read-only review of diffs, branches, and PRs — phased workflow, severity rubric (P0–P3), per-dimension checklists, structured report template |
| [committing-code](committing-code/SKILL.md) | Conventional Commits — logical commit boundaries with tests kept beside their code, selective staging, checks before committing |
| [systematic-debugging](systematic-debugging/SKILL.md) | Four-phase root cause analysis — reproduction, evidence, hypothesis, git bisect, differential debugging, Python + Rust toolkits |
| [test-driven-development](test-driven-development/SKILL.md) | Red-green-refactor, Arrange-Act-Assert test structure, characterization tests for refactors, testing anti-patterns |
| [task-orchestrator](task-orchestrator/SKILL.md) | Delegating to subagents — decides when it pays off, writes self-contained briefs, limits concurrency, verifies and merges results |

### Web & Frontend

| Skill | Description |
| --- | --- |
| [frontend-design](frontend-design/SKILL.md) | Top-level frontend workflow for design, redesign, implementation, audits, and validation |
| [frontend-redesign](frontend-redesign/SKILL.md) | Existing UI redesign, polish, and audit workflow that preserves product behavior while upgrading quality |
| [frontend-react](frontend-react/SKILL.md) | React and Next.js implementation defaults for testing, linting, typechecking, performance, and validation |

### Python

| Skill | Description |
| --- | --- |
| [python](python/SKILL.md) | Core Python workflow — uv, ruff, pyright and ty, testing, architecture, packaging, configuration, and operational safety |
| [python-async](python-async/SKILL.md) | asyncio and ASGI patterns — structured concurrency, cancellation, timeouts, queues, and FastAPI-style services |
| [python-web-apis](python-web-apis/SKILL.md) | HTTP and ASGI service patterns — FastAPI handlers, dependency injection, response contracts, error mapping, and API tests |
| [python-configuration](python-configuration/SKILL.md) | Typed settings and deployment config — environment variables, startup validation, secret files, and env-specific behavior |
| [python-infrastructure](python-infrastructure/SKILL.md) | Project mechanics — uv workflows, dependency groups, strict `pyproject.toml` structure, lockfiles, profiling, workers, and release practices |
| [python-modernization](python-modernization/SKILL.md) | Modern Python workflow upgrades — uv-native setup, pyright and ty, lockfiles, dependency groups, PEP 723 scripts, and legacy-tool migration |
| [python-resilience](python-resilience/SKILL.md) | Failure-handling patterns — validation, exception design, retries, timeouts, cleanup, partial failures, and telemetry |
| [python-testing](python-testing/SKILL.md) | pytest patterns — Arrange-Act-Assert, fixtures, mocks, async tests, coverage, markers, and property-based testing |
| [python-type-safety](python-type-safety/SKILL.md) | pyright- and ty-aware typing patterns — annotations, protocols, generics, narrowing, and safer Python interfaces |
| [python-anti-patterns](python-anti-patterns/SKILL.md) | Review checklist for common Python mistakes across architecture, async, typing, testing, config, and operations |

The curated Python family also includes bundled reference docs for foundations, packaging,
profiling, migration workflows, background jobs, cleanup-heavy failure handling, and web API
details.

### Rust

| Skill | Description |
| --- | --- |
| [rust](rust/SKILL.md) | Comprehensive guide — ownership, borrowing, lifetimes, error handling, traits, generics, API design, clippy |
| [rust-async](rust-async/SKILL.md) | Async Rust with Tokio — runtime setup, task spawning, JoinSet, channels, streams, select, cancellation |
| [rust-testing](rust-testing/SKILL.md) | Testing patterns — Arrange-Act-Assert, unit/integration/async tests, rstest, proptest, criterion benchmarks, doctests |

### Kubernetes & Helm

| Skill | Description |
| --- | --- |
| [kubernetes](kubernetes/SKILL.md) | Workloads, manifests, RBAC, NetworkPolicies, Pod Security Standards, storage, troubleshooting, cluster design |
| [helm](helm/SKILL.md) | Helm 4 chart development, Go templating, values management, hooks, commands, multi-environment deployments |

### Containers & Docker

| Skill | Description |
| --- | --- |
| [docker](docker/SKILL.md) | Dockerfiles (uv-based Python builds), multi-stage builds, image optimization, security hardening, health checks, Docker Compose |

### CI/CD

| Skill | Description |
| --- | --- |
| [cicd](cicd/SKILL.md) | Pipelines for GitHub Actions (uv and cargo starters), GitLab CI, Jenkins, and ArgoCD — security gates, action pinning, caching, deployment strategies |

### Databases

| Skill | Description |
| --- | --- |
| [sql-database](sql-database/SKILL.md) | Multi-dialect (PostgreSQL, MySQL, SQLite) schema design, indexing, migrations, query patterns, ORM integration, EXPLAIN |

### Tooling

| Skill | Description |
| --- | --- |
| [generating-custom-instructions](generating-custom-instructions/SKILL.md) | AGENTS.md-first instruction files (thin `@AGENTS.md` CLAUDE.md, `.claude/rules`, optional Copilot files) built from codebase analysis |
| [markdown-documentation](markdown-documentation/SKILL.md) | House Markdown rules — 100-column fill, code fences, tables, links, and the markdownlint-cli2 check |

### Diagramming

| Skill | Description |
| --- | --- |
| [mermaid](mermaid/SKILL.md) | Create, style, and render Mermaid diagrams — flowcharts, sequence, class, ERD, C4, state, architecture, with SVG/PNG/ASCII export |

### Observability

| Skill | Description |
| --- | --- |
| [observability](observability/SKILL.md) | Logging for CLIs and scripts; for services, Prometheus metrics, OpenTelemetry tracing, log aggregation, ES\|QL search, and SLOs |

### Shell Scripting

| Skill | Description |
| --- | --- |
| [shell-scripting](shell-scripting/SKILL.md) | Bash and PowerShell — light and full workflows, strict mode, traps, arg parsing, security, portability, ShellCheck/PSScriptAnalyzer, Bats/Pester |

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

Clone the repo, then link each skill into the directory your agent reads:

```bash
git clone git@github.com:mitch-avis/agent-skills.git ~/.agents/skills

# Claude Code loads personal skills only from ~/.claude/skills/
mkdir -p ~/.claude/skills
for skill in ~/.agents/skills/*/; do
    [[ -f "${skill}SKILL.md" ]] && ln -sfn "${skill%/}" ~/.claude/skills/
done
```

Other agents look in different places (some read `~/.agents/skills/` directly); check your
agent's documentation.

## Checks

Markdown is linted with [markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2), and
the Python and Bash code examples in every skill are checked by `scripts/check_examples.py` (ruff
format and the full house lint rules, and ShellCheck). Run both before committing;
[AGENTS.md](AGENTS.md) has the full gate list and the steps for adding or removing a skill.

```bash
uv sync
markdownlint-cli2 "**/*.md"
.venv/bin/python scripts/check_examples.py
```

## Acknowledgments

These skills were consolidated and rewritten from multiple open-source skill repositories. The
original 70+ skills were merged into the skills you see here — reorganized by domain, deduplicated,
and tailored to a consistent format. Temporary imported frontend and React skills were distilled
into the curated frontend skill family, then removed from the published set.

### Source Repositories

| Repository | Original Skills | Contributed To |
| --- | --- | --- |
| [404kidwiz/claude-supercode-skills](https://github.com/404kidwiz/claude-supercode-skills) | rust-engineer | rust |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | frontend-ui-engineering | frontend-design, frontend-react |
| [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) | rust-patterns, rust-testing, python-patterns | rust, rust-testing, python |
| [ailabs-393/ai-labs-claude-skills](https://github.com/ailabs-393/ai-labs-claude-skills) | docker-containerization | docker |
| [aj-geddes/useful-ai-prompts](https://github.com/aj-geddes/useful-ai-prompts) | markdown-documentation, kubernetes-deployment, docker-containerization, gitlab-cicd-pipeline, cicd-pipeline-setup, code-review-analysis, logging-best-practices, application-logging | markdown-documentation, kubernetes, docker, cicd, code-review, observability |
| [akin-ozer/cc-devops-skills](https://github.com/akin-ozer/cc-devops-skills) | bash-script-generator | shell-scripting |
| [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) | sql-queries, code-review | sql-database, code-review |
| [anthropics/skills](https://github.com/anthropics/skills) | frontend-design | frontend-design |
| [apollographql/skills](https://github.com/apollographql/skills) | rust-best-practices | rust, rust-async, rust-testing |
| [axtonliu/axton-obsidian-visual-skills](https://github.com/axtonliu/axton-obsidian-visual-skills) | mermaid-visualizer | mermaid |
| [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates) | mermaid-diagram-specialist, Linux Production Shell Scripts | mermaid, shell-scripting |
| [elastic/agent-skills](https://github.com/elastic/agent-skills) | observability-logs-search | observability |
| [github/awesome-copilot](https://github.com/github/awesome-copilot) | pytest-coverage, conventional-commit, git-commit, copilot-instructions-blueprint-generator, generate-custom-instructions-from-codebase, suggest-awesome-github-copilot-instructions, multi-stage-dockerfile, sql-optimization, sql-code-review, postgresql-optimization, postgresql-code-review, review-and-refactor, premium-frontend-ui | python-testing, committing-code, generating-custom-instructions, docker, sql-database, code-review, frontend-design |
| [google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli) | code-reviewer | code-review |
| [imxv/pretty-mermaid-skills](https://github.com/imxv/pretty-mermaid-skills) | pretty-mermaid | mermaid |
| [intellectronica/agent-skills](https://github.com/intellectronica/agent-skills) | beautiful-mermaid | mermaid |
| [jeffallan/claude-skills](https://github.com/jeffallan/claude-skills) | rust-engineer, kubernetes-specialist, sql-pro, code-reviewer | rust, kubernetes, sql-database, code-review |
| [josiahsiegel/claude-plugin-marketplace](https://github.com/josiahsiegel/claude-plugin-marketplace) | powershell-master, bash-master | shell-scripting |
| [julianoczkowski/designer-skills](https://github.com/julianoczkowski/designer-skills) | frontend-design-julianoczkowski | frontend-design |
| [laurigates/claude-plugins](https://github.com/laurigates/claude-plugins) | shell-expert | shell-scripting |
| [leonardomso/rust-skills](https://github.com/leonardomso/rust-skills) | rust-skills | rust |
| [leonxlnx/taste-skill](https://github.com/leonxlnx/taste-skill) | design-taste-frontend, design-taste-frontend-v1, high-end-visual-design, industrial-brutalist-ui, minimalist-ui, redesign-existing-projects | frontend-design, frontend-redesign |
| [manutej/luxor-claude-marketplace](https://github.com/manutej/luxor-claude-marketplace) | docker-compose-orchestration | docker |
| [martinholovsky/claude-skills-generator](https://github.com/martinholovsky/claude-skills-generator) | cicd-expert, SQLite Database Expert | cicd, sql-database |
| [millionco/react-doctor](https://github.com/millionco/react-doctor) | react-doctor | frontend-react |
| [mindrally/skills](https://github.com/mindrally/skills) | gitlab-workflow, mysql-best-practices, fastapi-python | cicd, sql-database, python-web-apis |
| [obra/superpowers](https://github.com/obra/superpowers) | test-driven-development, systematic-debugging, requesting-code-review | test-driven-development, systematic-debugging, code-review |
| [onewave-ai/claude-skills](https://github.com/onewave-ai/claude-skills) | code-review-pro | code-review |
| [patricio0312rev/skills](https://github.com/patricio0312rev/skills) | dockerfile-optimizer | docker |
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | impeccable | frontend-design, frontend-redesign |
| [personamanagmentlayer/pcl](https://github.com/personamanagmentlayer/pcl) | helm-expert, docker-expert, argocd-expert | helm, docker, cicd |
| [planetscale/database-skills](https://github.com/planetscale/database-skills) | mysql | sql-database |
| [pluginagentmarketplace/custom-plugin-nodejs](https://github.com/pluginagentmarketplace/custom-plugin-nodejs) | docker-deployment | docker |
| [pproenca/dot-skills](https://github.com/pproenca/dot-skills) | shell | shell-scripting |
| [sanyuan0704/code-review-expert](https://github.com/sanyuan0704/code-review-expert) | code-review-expert | code-review |
| [shubhamsaboo/awesome-llm-apps](https://github.com/shubhamsaboo/awesome-llm-apps) | code-reviewer | code-review |
| [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) | rust-pro, rust-async-patterns, software-architecture, kubernetes-architect, helm-chart-scaffolding, docker-expert, cicd-automation-workflow-automate, powershell-windows, linux-shell-scripting, bash-linux, bash-scripting, bash-pro | rust, rust-async, task-orchestrator, kubernetes, helm, docker, cicd, shell-scripting |
| [softaworks/agent-toolkit](https://github.com/softaworks/agent-toolkit) | commit-work, mermaid-diagrams | committing-code, mermaid |
| [thebushidocollective/han](https://github.com/thebushidocollective/han) | shell-best-practices | shell-scripting |
| [vercel-labs/skills](https://github.com/vercel-labs/skills) | vercel-react-best-practices, vercel-react-view-transitions, vercel-composition-patterns, vercel-microfrontends, web-design-guidelines | frontend-design, frontend-react |
| [vince-winkintel/gitlab-cli-skills](https://github.com/vince-winkintel/gitlab-cli-skills) | gitlab-cli-skills | cicd |
| [wispbit-ai/skills](https://github.com/wispbit-ai/skills) | rust-expert-best-practices-code-review | rust |
| [trailofbits/skills](https://github.com/trailofbits/skills) | modern-python | python, python-infrastructure, python-modernization |
| [wshobson/agents](https://github.com/wshobson/agents) | python-code-style, python-design-patterns, python-project-structure, python-error-handling, python-anti-patterns, python-type-safety, python-configuration, async-python-patterns, python-testing-patterns, python-packaging, python-performance-optimization, python-background-jobs, python-resilience, python-resource-management, uv-package-manager, python-observability, service-mesh-observability, rust-async-patterns, k8s-manifest-generator, k8s-security-policies, helm-chart-scaffolding, gitlab-ci-patterns, sql-optimization-patterns, postgresql-table-design, code-review-excellence, shellcheck-configuration, bash-defensive-patterns | python, python-async, python-testing, python-infrastructure, python-resilience, python-configuration, python-type-safety, python-anti-patterns, python-modernization, observability, rust-async, kubernetes, helm, cicd, sql-database, code-review, shell-scripting |
| [zhanghandong/rust-skills](https://github.com/zhanghandong/rust-skills) | rust-router, rust-refactor-helper, rust-trait-explorer, rust-code-navigator, rust-learner, rust-symbol-analyzer, rust-call-graph, rust-deps-visualizer, rust-skill-creator, rust-daily | rust |

## License

[MIT](LICENSE)
