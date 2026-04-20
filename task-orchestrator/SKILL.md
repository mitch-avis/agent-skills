---
name: task-orchestrator
description: >-
  Decomposes complex, multi-step, or cross-domain tasks into subtasks, assigns each to the most
  appropriate skill or subagent, runs independent subtasks in parallel, and synthesizes results. Use
  whenever a request involves more than one skill, touches multiple languages or file types,
  requires a plan-then-execute workflow, contains multiple numbered or comma-separated tasks, or is
  ambiguous and benefits from decomposition before execution. Also use when the user explicitly asks
  to break work into parts, delegate to subagents, or run things in parallel.
---

# Task Orchestrator

Parse complex requests, decompose into subtasks, delegate to subagents, run in parallel where
possible, and synthesize results.

## When to Use

- Task spans multiple skills or languages (Rust + Python + docs)
- Request is ambiguous and needs decomposition before execution
- Multiple independent work items can run in parallel
- Task requires a plan-execute-verify cycle
- User provides a numbered list or comma-separated set of tasks
- Request contains phrases like "go through each", "update all", or "review everything"
- Work can be split into research, implementation, and validation phases

## Workflow

### 1. Parse the Request

Identify:

- **Goal:** What is the user trying to accomplish?
- **Scope:** What files, modules, or systems are involved?
- **Constraints:** Standards, deadlines, dependencies?
- **Deliverables:** What artifacts must be produced?

### 2. Decompose into Subtasks

Break the goal into the smallest independent work units. Each subtask must have:

- A clear, single objective
- An assigned skill (from the available skill set)
- Defined inputs and expected outputs
- Independence flag: can it run in parallel with others?

**Decomposition heuristic:**

```text
Request
  |
  +-- Are there independent parts? --> Split into parallel subtasks
  |
  +-- Is there a natural sequence?  --> Chain as sequential subtasks
  |
  +-- Is it a single atomic action? --> Execute directly
```

### 3. Assign Skills

Map each subtask to the best available skill:

| Domain                     | Skill                          |
| -------------------------- | ------------------------------ |
| Rust code                  | rust                           |
| Rust async / Tokio         | rust-async                     |
| Rust tests                 | rust-testing                   |
| Python code                | python                         |
| Python async               | python-async                   |
| Python resilience          | python-resilience              |
| Python tests               | python-testing                 |
| Python packaging / infra   | python-infrastructure          |
| Kubernetes manifests       | kubernetes                     |
| Helm charts                | helm                           |
| Dockerfiles / containers   | docker                         |
| CI/CD pipelines            | cicd                           |
| Markdown / docs            | markdown-documentation         |
| Mermaid diagrams           | mermaid                        |
| Shell scripts (bash, sh)   | shell-scripting                |
| PowerShell scripts         | shell-scripting                |
| ShellCheck / PSAnalyzer    | shell-scripting                |
| Bats / Pester tests        | shell-scripting                |
| Code quality               | clean-code                     |
| Code review / PR audit     | code-review                    |
| TDD methodology            | test-driven-development        |
| Debugging / root cause     | systematic-debugging           |
| Git commits                | committing-code                |
| Browser automation (CLI)   | agent-browser                  |
| Browser automation (daemon)| browser-use                    |
| Finding / installing skills| find-skills                    |
| Custom instruction files   | generating-custom-instructions |
| Creating / improving skills| skill-creator                  |
| Multi-step orchestration   | task-orchestrator (self)       |
| SQL schema / queries / ORM | sql-database                   |

### 4. Execute

**Parallel execution** — for subtasks with no dependencies:

Launch independent subtasks as parallel subagents. Each subagent receives:

- The subtask description
- Relevant skill context
- Input artifacts from prior steps (if any)

**Sequential execution** — for subtasks with dependencies:

Execute in dependency order. Pass outputs from completed subtasks as inputs to dependent ones.

**Hybrid execution:**

```text
[Parse request]
       |
  +---------+---------+
  |         |         |
[Rust]  [Python]  [Docs]     <-- parallel
  |         |         |
  +---------+---------+
       |
[Integration test]             <-- sequential (depends on all)
       |
[Final review]
```

### 5. Collect and Validate

After all subtasks complete:

- Verify each subtask produced its expected output
- Check for conflicts between subtask results
- Run cross-cutting validations (linting, formatting, tests)
- If a subtask failed, diagnose and retry or report

### 6. Synthesize

Combine subtask outputs into a coherent final result:

- Merge code changes across files
- Update documentation to reflect all changes
- Run the full test suite
- Format all modified files
- Present a summary of what was done

## Standards Enforcement

Apply these checks to every output:

### Rust

```bash
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test --all-targets --all-features
```

### Python

```bash
ruff format --check .
ruff check .
ty check .       # primary type checker (Astral, still in beta)
pyright .        # fallback type checker (stable)
pytest --cov
```

### Markdown

```bash
markdownlint .
```

### Universal

- Line length: 100 characters
- TDD: Failing test before implementation
- Coverage target: 100% where achievable

## Error Recovery

If a subtask fails:

1. Read the error output carefully
2. Determine if the failure is in the subtask or its inputs
3. Fix the root cause (do not retry blindly)
4. Re-run only the failed subtask and its dependents
5. If stuck after two attempts, report the issue with context

## Confidence Protocol

For ambiguous requests, state confidence before proceeding:

- **HIGH** — Clear requirement, known approach. Proceed.
- **MEDIUM** — Reasonable interpretation, some uncertainty. State assumptions, proceed.
- **LOW** — Multiple valid interpretations. Ask one clarifying question, then proceed with best
  guess.
