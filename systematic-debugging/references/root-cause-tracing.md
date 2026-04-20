# Root Cause Tracing

Bugs often manifest deep in the call stack (git init in wrong directory, file created in wrong
location, database opened with wrong path). Fix where the error appears and you're treating a
symptom.

**Core principle:** Trace backward through the call chain until you find the original trigger, then
fix at the source.

## When to Use

- Error happens deep in execution (not at entry point)
- Stack trace shows long call chain
- Unclear where invalid data originated
- Need to find which test/code triggers the problem

## The Tracing Process

### 1. Observe the Symptom

```text
Error: git init failed in /Users/dev/project/packages/core
```

### 2. Find Immediate Cause

**What code directly causes this?**

```python
subprocess.run(["git", "init"], cwd=project_dir, check=True)
```

### 3. Ask: What Called This?

```text
WorktreeManager.create_session_worktree(project_dir, session_id)
  → called by Session.initialize_workspace()
  → called by Session.create()
  → called by test at Project.create()
```

### 4. Keep Tracing Up

**What value was passed?**

- `project_dir = ""` (empty string!)
- Empty string as `cwd` to `subprocess.run` resolves to `os.getcwd()`
- That's the source code directory!

### 5. Find Original Trigger

**Where did empty string come from?**

```python
# Returns SimpleNamespace(tmp_dir="")
context = setup_core_test()
# Accessed before fixture initialised it!
Project.create("name", context.tmp_dir)
```

## Adding Stack Traces

When you can't trace manually, add instrumentation:

```python
import os
import subprocess
import sys
import traceback


def git_init(directory: str) -> None:
    print(
        "DEBUG git init:",
        {
            "directory": directory,
            "cwd": os.getcwd(),
            "stack": "".join(traceback.format_stack()),
        },
        file=sys.stderr,
    )
    subprocess.run(["git", "init"], cwd=directory, check=True)
```

Write to `sys.stderr` in tests — captured logger output may be suppressed by pytest.

Run and capture:

```bash
pytest 2>&1 | grep 'DEBUG git init'
```

### Rust Equivalent

Capture a backtrace right before the dangerous operation. `Backtrace::force_capture()` works even
when `RUST_BACKTRACE` is unset, which is what you want for ad-hoc debugging.

```rust
use std::backtrace::Backtrace;
use std::env;
use std::path::Path;
use std::process::Command;

fn git_init(directory: &Path) -> std::io::Result<()> {
    eprintln!(
        "DEBUG git init: directory={} cwd={:?}\n{}",
        directory.display(),
        env::current_dir().ok(),
        Backtrace::force_capture(),
    );
    Command::new("git")
        .arg("init")
        .current_dir(directory)
        .status()?;
    Ok(())
}
```

Write to `stderr` (not `tracing` / `log`) when debugging tests — `cargo test` captures stdout but
leaves `eprintln!` visible without `--nocapture`. Run with:

```bash
cargo test 2>&1 | grep 'DEBUG git init'
# Or, to see all output even from passing tests:
cargo test -- --nocapture 2>&1 | grep 'DEBUG git init'
```

For a permanent instrumentation hook in async code, prefer the `tracing` crate so you can toggle
with `RUST_LOG=debug`:

```rust
use tracing::debug;

debug!(
    directory = %directory.display(),
    cwd = ?env::current_dir().ok(),
    backtrace = ?Backtrace::capture(),
    "about to git init",
);
```

Analyze stack traces:

- Look for test file names
- Find the line number triggering the call
- Identify the pattern (same test? same parameter?)

## Finding Which Test Causes Pollution

Use the bisection script `find-polluter.sh` in this directory:

```bash
./find-polluter.sh '.git' 'pytest' 'tests/**/test_*.py'
./find-polluter.sh '.git' 'cargo test --test' 'tests/*.rs'
```

Runs tests one-by-one, stops at first polluter.

## Real Example: Empty projectDir

**Symptom:** `.git` created in `packages/core/` (source code)

**Trace chain:**

1. `git init` runs in `os.getcwd()` — empty cwd parameter
2. WorktreeManager called with empty `project_dir`
3. `Session.create()` passed empty string
4. Test accessed `context.tmp_dir` before pytest fixture ran
5. `setup_core_test()` returns `tmp_dir=""` initially

**Root cause:** Module-level variable initialization accessing empty value

**Fix:** Made `tmp_dir` a property that raises if accessed before fixture setup

**Also added defense-in-depth:**

- Layer 1: Project.create() validates directory
- Layer 2: WorkspaceManager validates not empty
- Layer 3: NODE_ENV guard refuses git init outside tmpdir
- Layer 4: Stack trace logging before git init

## Key Principle

**NEVER fix just where the error appears.** Trace back to find the original trigger. Then add
validation at each layer so the bug becomes structurally impossible.

## Stack Trace Tips

- **Python tests:** write to `sys.stderr` — captured logger output may be suppressed by pytest.
- **Rust tests:** use `eprintln!` — `cargo test` only swallows stdout. Use
  `Backtrace::force_capture()` to ignore `RUST_BACKTRACE`. For sustained instrumentation in async
  code, use the `tracing` crate gated by `RUST_LOG`.
- **Before operation:** log before the dangerous operation, not after it fails
- **Include context:** directory, cwd, environment variables, timestamps
- **Capture stack:** `traceback.format_stack()` (Python) or `std::backtrace::Backtrace` (Rust) shows
  the complete call chain
