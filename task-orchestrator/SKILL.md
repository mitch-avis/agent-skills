---
name: task-orchestrator
description: >-
  Use when the user asks to split work across subagents, delegate, or run tasks in parallel, or
  before launching two or more subagents for one task. Decides whether delegation pays off, writes
  self-contained subagent briefs, sets concurrency and worktree limits, and verifies and merges
  subagent results. A multi-part request alone is not a reason to delegate.
---

# Task Orchestrator

Delegate work to subagents only when it pays off, brief them so they can work without your
context, and verify what they return before relying on it.

## Decide Whether to Delegate

Each subagent starts cold: it re-reads files, re-derives context, and costs a session of its own.
Delegate only when that cost buys something.

- **Delegate:** independent work items that need no shared context mid-task; wide searches or
  audits where you need the conclusion, not the file dumps; long checks that can run while you work
  on something else.
- **Don't delegate:** small or sequential edits, work that depends on decisions still being made in
  the conversation, or tasks where writing the brief costs more than doing the work.
- When the host tool or the repo sets its own delegation rules (for example, "spawn subagents only
  when the user asks"), those come first.

A numbered or multi-part request is a checklist, not a reason to delegate. Work through it directly
unless its items meet the bar above.

## Plan the Split

For each subtask, write down:

- One objective and its deliverable
- Its inputs, including outputs of earlier subtasks
- Whether it can run alongside the others or must wait for one
- Which skills apply, if the host offers skills

Run independent subtasks together and chain dependent ones in order. Keep integration and final
validation in the main session.

## Brief Each Subagent

A subagent knows only what its brief says. Include:

- The objective, the scope, and what "done" means
- The repo rules that apply: which instruction files to read (`AGENTS.md`, `CLAUDE.md`), the
  validation command or gate, and the actions it must not take without asking (pushing, deleting,
  editing generated files, touching other repos)
- Input artifacts and the decisions already made, so it does not reopen them
- What to return: files changed, check results with the exact commands run, and open questions,
  not a narrative

## Concurrency Limits

- Heavy jobs that saturate CPU, GPU, or memory (model training, long builds, large backtests) run
  one at a time. Parallelize the light work around them.
- Two subagents never edit the same working tree at the same time. Give each its own git worktree,
  or run them in sequence.
- Read-only subagents (search, review, audit) can share a tree.

## Verify and Merge Results

A subagent's report is input to verify, not a source to copy.

- Confirm each deliverable by reading the files or diffs, not the summary.
- Re-run the checks a subagent says passed; never relay a pass you did not see.
- Look for conflicts between subtasks (the same file, incompatible assumptions) before merging.
- Run the repo's full gate once on the merged result.
- Report what each subtask changed, the gate results, and anything that still needs a decision.

## When a Subtask Fails

1. Read its error output and decide whether the fault is in the subtask or in its inputs.
2. Fix the root cause; do not retry blindly.
3. Re-run only the failed subtask and the subtasks that depend on it.
4. After two failed attempts, stop and report what was tried, with the errors.
