---
name: skill-creator
description: >-
  Create new skills, modify and improve existing skills, and measure skill performance
  with eval-driven iteration. Use when users want to create a skill from scratch, edit or
  optimize an existing skill, run evals to test a skill, benchmark skill performance with
  variance analysis, or optimize a skill's description for better triggering accuracy.
---

# Skill Creator

Create, evaluate, and iteratively improve agent skills through a structured
draft-test-review-improve loop.

## Overview

The skill creation process:

1. Capture intent — what the skill does, when it triggers, expected output
2. Write a draft SKILL.md
3. Create test prompts and run them (with-skill and baseline)
4. Evaluate results qualitatively (user review) and quantitatively (assertions)
5. Improve the skill based on feedback
6. Repeat until satisfied
7. Optimize the description for triggering accuracy

Assess where the user is in this process and help them progress. If they already have a draft, skip
straight to evaluation. If they want to iterate informally without formal evals, adapt accordingly.

---

## Creating a Skill

### 1. Capture Intent

Extract answers from conversation history first (tools used, sequence of steps, corrections made,
input/output formats). Then confirm with the user:

1. What should this skill enable an agent to do?
2. When should it trigger? (what user phrases/contexts)
3. What is the expected output format?
4. Are test cases appropriate? Skills with objectively verifiable outputs (file transforms, data
   extraction, code generation) benefit from test cases. Skills with subjective outputs (writing
   style, art) often do not.

### 2. Interview and Research

Ask about edge cases, input/output formats, example files, success criteria, and dependencies. Wait
to write test prompts until this is solidified.

Use available tools (web search, docs, similar skills) to research in parallel where possible. Come
prepared with context to reduce burden on the user.

### 3. Write the SKILL.md

Fill in these components:

- **name**: kebab-case identifier (lowercase, hyphens, max 64 chars)
- **description**: Primary triggering mechanism — include both what the skill does AND specific
  contexts for when to use it. All "when to use" info goes here, not in the body. Agents tend to
  undertrigger skills, so make descriptions slightly assertive (e.g., "Use this skill whenever the
  user mentions dashboards, data visualization, or wants to display any kind of data, even if they
  don't explicitly ask for a 'dashboard'"). Max 1024 characters.
- **compatibility**: Required tools, dependencies (optional, rarely needed)
- **body**: The skill instructions

### Skill Anatomy

```text
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, icons, fonts)
```

### Progressive Disclosure

Skills use a three-level loading system:

1. **Metadata** (name + description) — always in context (~100 words)
2. **SKILL.md body** — loaded when skill triggers (<500 lines ideal)
3. **Bundled resources** — loaded as needed (unlimited size)

Guidelines:

- Keep SKILL.md under 500 lines; overflow into `references/` with clear pointers
- Reference files clearly from SKILL.md with guidance on when to read them
- For large reference files (>300 lines), include a table of contents
- Organize by variant when supporting multiple domains/frameworks

### Writing Principles

- **Imperative tone**: "Run the tests" not "You should run the tests"
- **Explain the why**: LLMs respond better to reasoning than rigid directives. If you find yourself
  writing ALWAYS or NEVER in all caps, reframe with the reasoning behind the constraint instead — it
  produces more reliable behavior
- **Generalize**: Write for many different prompts, not just the test examples
- **Keep it lean**: Remove instructions that are not pulling their weight. Read transcripts to spot
  unproductive patterns the skill is causing
- **No surprises**: Skills must not contain malware, exploit code, or content that could compromise
  system security

### 4. Test Cases

After drafting, propose 2-3 realistic test prompts and confirm with the user. Save to
`evals/evals.json` without assertions initially:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's task prompt",
      "expected_output": "Description of expected result",
      "files": []
    }
  ]
}
```

See [references/schemas.md](references/schemas.md) for the full schema.

---

## Running and Evaluating Test Cases

Execute this as one continuous sequence. Organize results in `<skill-name>-workspace/` as a sibling
to the skill directory, with `iteration-<N>/eval-<ID>/` subdirectories created as needed.

### Step 1: Spawn All Runs

For each test case, launch two runs in the same turn — one with the skill, one baseline:

**With-skill run:**

```text
Execute this task:
- Skill path: <path-to-skill>
- Task: <eval prompt>
- Input files: <eval files if any>
- Save outputs to: <workspace>/iteration-<N>/eval-<ID>/with_skill/outputs/
```

**Baseline run** (same prompt, different config):

- **New skill**: no skill at all → save to `without_skill/outputs/`
- **Improving existing skill**: snapshot the old version first (`cp -r <skill-path>
  <workspace>/skill-snapshot/`), point baseline at the snapshot → save to `old_skill/outputs/`

Write an `eval_metadata.json` for each test case with a descriptive name:

```json
{
  "eval_id": 0,
  "eval_name": "descriptive-name-here",
  "prompt": "The user's task prompt",
  "assertions": []
}
```

### Step 2: Draft Assertions While Runs Execute

Use the wait time productively. Draft objectively verifiable assertions with descriptive names that
read clearly in the benchmark viewer. Avoid forcing assertions onto subjective outputs — those are
better evaluated qualitatively.

Update `eval_metadata.json` and `evals/evals.json` with the assertions.

### Step 3: Capture Timing Data

When each subagent task completes, save the notification's `total_tokens` and `duration_ms`
immediately to `timing.json` in the run directory — this data is not persisted elsewhere.

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

### Step 4: Grade, Aggregate, and Launch the Viewer

Once all runs complete:

1. **Grade each run** — use [agents/grader.md](agents/grader.md) to evaluate assertions against
   outputs. Save to `grading.json` in each run directory. The expectations array must use fields
   `text`, `passed`, and `evidence` (the viewer depends on these exact names). For programmatically
   checkable assertions, write and run a script.

2. **Aggregate into benchmark**:

   ```bash
   python -m scripts.aggregate_benchmark <workspace>/iteration-N \
     --skill-name <name>
   ```

   Produces `benchmark.json` and `benchmark.md` with pass_rate, time, and tokens per configuration.
   See [references/schemas.md](references/schemas.md) for the schema.

3. **Analyst pass** — read the benchmark data and surface hidden patterns. See
   [agents/analyzer.md](agents/analyzer.md) for what to look for (non-discriminating assertions,
   high-variance evals, time/token tradeoffs).

4. **Launch the viewer**:

   ```bash
   python <skill-creator-path>/eval-viewer/generate_review.py \
     <workspace>/iteration-N \
     --skill-name "my-skill" \
     --benchmark <workspace>/iteration-N/benchmark.json
   ```

   For iteration 2+, add `--previous-workspace <workspace>/iteration-<N-1>`.

   **Headless environments**: Use `--static <output_path>` to write a standalone HTML file instead
   of starting a server.

   Always use `generate_review.py` to create the viewer — do not write custom HTML. Generate the
   viewer *before* evaluating outputs yourself. Get results in front of the human first.

### Step 5: Read Feedback

When the user finishes reviewing, read `feedback.json`:

```json
{
  "reviews": [
    {
      "run_id": "eval-0-with_skill",
      "feedback": "the chart is missing axis labels",
      "timestamp": "..."
    }
  ],
  "status": "complete"
}
```

Empty feedback means the user was satisfied. Focus improvements on test cases with specific
complaints.

---

## Improving the Skill

### Improvement Principles

1. **Generalize from feedback.** Skills are used across many different prompts. Rather than fiddly
   overfitting changes or rigid constraints, try different metaphors or patterns of working. If a
   stubborn issue persists, branching out is cheap.

2. **Keep the prompt lean.** Read transcripts, not just final outputs. If the skill causes
   unproductive work, remove the instructions causing it.

3. **Explain the why.** Transmit understanding of the task into the instructions. Reasoning-based
   instructions produce more reliable behavior than rigid rules.

4. **Bundle repeated work.** If multiple test runs independently wrote similar helper scripts, the
   skill should bundle that script in `scripts/` and reference it.

### The Iteration Loop

1. Apply improvements to the skill
2. Rerun all test cases into `iteration-<N+1>/`, including baseline runs
3. Launch the viewer with `--previous-workspace` pointing at the previous iteration
4. Wait for user review
5. Read feedback, improve, repeat

Stop when:

- The user is satisfied
- All feedback is empty
- Improvements plateau

---

## Blind Comparison (Advanced)

For rigorous A/B comparison between skill versions, use the blind comparison system. Read
[agents/comparator.md](agents/comparator.md) and [agents/analyzer.md](agents/analyzer.md) for
details. This gives two outputs to an independent evaluator without revealing which skill produced
which, then analyzes why the winner won.

Optional — the human review loop is usually sufficient.

---

## Description Optimization

The description field is the primary mechanism that determines whether an agent invokes a skill.
After creating or improving a skill, offer to optimize the description for triggering accuracy.

### Step 1: Generate Trigger Eval Queries

Create 20 queries — a mix of should-trigger (8-10) and should-not-trigger (8-10).

```json
[
  {"query": "the user prompt", "should_trigger": true},
  {"query": "another prompt", "should_trigger": false}
]
```

**Query guidelines:**

- Make queries realistic with concrete details (file paths, column names, personal context,
  backstory)
- Mix formal and casual phrasings, varying lengths, abbreviations, typos
- Focus on edge cases rather than clear-cut examples
- Should-trigger: different phrasings of the same intent, cases where the user doesn't name the
  skill explicitly but clearly needs it
- Should-not-trigger: near-misses that share keywords but need something different. Avoid obviously
  irrelevant queries — test genuinely tricky cases

### Step 2: Review with User

Present the eval set using the HTML template in `assets/eval_review.html`:

1. Read the template
2. Replace `__EVAL_DATA_PLACEHOLDER__` with the JSON array, `__SKILL_NAME_PLACEHOLDER__` with the
   skill name, `__SKILL_DESCRIPTION_PLACEHOLDER__` with the current description
3. Write to a temp file and open it
4. User edits queries, toggles triggers, exports → `eval_set.json`

### Step 3: Run the Optimization Loop

```bash
python -m scripts.run_loop \
  --eval-set <path-to-trigger-eval.json> \
  --skill-path <path-to-skill> \
  --model <model-id> \
  --max-iterations 5 \
  --verbose
```

The loop automatically splits the eval set (60% train / 40% test), evaluates the current description
(3 runs per query for reliability), proposes improvements based on failures, and re-evaluates.
Selects `best_description` by test score to avoid overfitting.

### Triggering Mechanics

Skills appear in the agent's available skills list with their name and description. The agent
decides whether to consult a skill based on that description. Agents typically only consult skills
for tasks they cannot easily handle alone — simple one-step queries may not trigger a skill even
with a perfect description match. Eval queries should be substantive enough that an agent would
benefit from consulting a skill.

### Step 4: Apply the Result

Update the skill's SKILL.md frontmatter with `best_description`. Show before/after and report
scores.

---

## Packaging

Package the finished skill into a distributable `.skill` file:

```bash
python -m scripts.package_skill <path/to/skill-folder>
```

### Updating an Existing Skill

When updating rather than creating:

- Preserve the original `name` and directory name unchanged
- Copy to a writable location before editing if the installed path is read-only
- If packaging manually, stage in `/tmp/` first

---

## Environment Adaptations

**With subagents**: Use the full parallel workflow (spawn test cases simultaneously, run baselines,
grade, aggregate, view).

**Without subagents**: Run test cases sequentially by reading the skill's SKILL.md and following its
instructions directly. Skip baseline runs and quantitative benchmarking. Present results inline and
ask for feedback in the conversation.

**Headless / no browser**: Use `--static <output_path>` with `generate_review.py` to produce a
standalone HTML file. Feedback downloads as `feedback.json` when the user clicks "Submit All
Reviews".

---

## Reference Files

### Agents (subagent instructions)

- [agents/grader.md](agents/grader.md) — evaluate assertions against outputs
- [agents/comparator.md](agents/comparator.md) — blind A/B comparison
- [agents/analyzer.md](agents/analyzer.md) — post-hoc analysis of why one version won

### References

- [references/schemas.md](references/schemas.md) — JSON schemas for evals.json, grading.json,
  benchmark.json, history.json, timing.json, metrics.json

### Scripts

| Script                           | Purpose                                        |
| -------------------------------- | ---------------------------------------------- |
| `scripts/run_eval.py`            | Trigger evaluation for a skill description     |
| `scripts/run_loop.py`            | Eval + improve loop with train/test split      |
| `scripts/improve_description.py` | LLM-powered description improvement            |
| `scripts/aggregate_benchmark.py` | Aggregate run results into benchmark stats     |
| `scripts/generate_report.py`     | HTML report from optimization loop output      |
| `scripts/package_skill.py`       | Package skill into distributable `.skill` file |
| `scripts/quick_validate.py`      | Validate SKILL.md frontmatter                  |
| `eval-viewer/generate_review.py` | Interactive eval review viewer                 |
