# Defense-in-Depth Validation

When you fix a bug caused by invalid data, adding validation at one place feels sufficient. But that
single check can be bypassed by different code paths, refactoring, or mocks.

**Core principle:** Validate at EVERY layer data passes through. Make the bug structurally
impossible.

## Why Multiple Layers

Single validation: "We fixed the bug." Multiple layers: "We made the bug impossible."

Different layers catch different cases:

- Entry validation catches most bugs
- Business logic catches edge cases
- Environment guards prevent context-specific dangers
- Debug logging helps when other layers fail

## The Four Layers

### Layer 1: Entry Point Validation

**Purpose:** Reject obviously invalid input at API boundary

```python
def create_project(name: str, working_directory: str) -> Project:
    if not working_directory or not working_directory.strip():
        raise ValueError("working_directory cannot be empty")
    if not Path(working_directory).exists():
        raise FileNotFoundError(f"working_directory does not exist: {working_directory}")
    # ... proceed
```

### Layer 2: Business Logic Validation

**Purpose:** Ensure data makes sense for this operation

```python
def initialize_workspace(project_dir: str, session_id: str) -> None:
    if not project_dir:
        raise ValueError("project_dir required for workspace initialization")
    # ... proceed
```

### Layer 3: Environment Guards

**Purpose:** Prevent dangerous operations in specific contexts

```python
def git_init(directory: str) -> None:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        normalized = Path(directory).resolve()
        tmp_dir = Path(tempfile.gettempdir()).resolve()
        if not str(normalized).startswith(str(tmp_dir)):
            raise RuntimeError(
                f"Refusing git init outside temp dir during tests: {directory}"
            )
    # ... proceed
```

### Layer 4: Debug Instrumentation

**Purpose:** Capture context for forensics

```python
import logging
import traceback

logger = logging.getLogger(__name__)


def git_init(directory: str) -> None:
    logger.debug(
        "About to git init",
        extra={
            "directory": directory,
            "cwd": os.getcwd(),
            "stack": "".join(traceback.format_stack()),
        },
    )
    # ... proceed
```

## Rust Equivalent

The same four layers translate cleanly to Rust. Use the type system as a fifth, free layer
whenever possible — replacing `String` paths with `&Path`/`PathBuf` and untyped flags with newtype
wrappers makes whole categories of "invalid data" unrepresentable.

```rust
use std::env;
use std::path::{Path, PathBuf};
use std::process::Command;

use anyhow::{anyhow, Context, Result};
use tracing::debug;

// Layer 1: entry-point validation
pub fn create_project(name: &str, working_directory: &Path) -> Result<Project> {
    if working_directory.as_os_str().is_empty() {
        return Err(anyhow!("working_directory cannot be empty"));
    }
    if !working_directory.exists() {
        return Err(anyhow!(
            "working_directory does not exist: {}",
            working_directory.display()
        ));
    }
    // ... proceed
    # Ok(Project { name: name.into(), dir: working_directory.into() })
}

// Layer 2: business-logic validation
pub fn initialize_workspace(project_dir: &Path, _session_id: &str) -> Result<()> {
    if project_dir.as_os_str().is_empty() {
        return Err(anyhow!("project_dir required for workspace initialization"));
    }
    Ok(())
}

// Layer 3: environment guard - refuse dangerous operations during tests
pub fn git_init(directory: &Path) -> Result<()> {
    if cfg!(test) || env::var_os("CARGO_PKG_NAME").is_some_and(|_| env::var_os("RUST_TEST_THREADS").is_some()) {
        let tmp = env::temp_dir().canonicalize().context("canonicalize tmp")?;
        let target = directory.canonicalize().context("canonicalize directory")?;
        if !target.starts_with(&tmp) {
            return Err(anyhow!(
                "refusing git init outside temp dir during tests: {}",
                directory.display()
            ));
        }
    }

    // Layer 4: debug instrumentation - capture context before the dangerous op
    debug!(
        directory = %directory.display(),
        cwd = ?env::current_dir().ok(),
        backtrace = ?std::backtrace::Backtrace::capture(),
        "about to git init",
    );

    Command::new("git")
        .arg("init")
        .current_dir(directory)
        .status()
        .context("git init failed")?;
    Ok(())
}
# struct Project { name: String, dir: PathBuf }
```

**Make invalid states unrepresentable.** A typed wrapper turns a runtime check into a
compile-time guarantee:

```rust
/// A directory that has been validated to exist and to be safe for git operations.
pub struct SafeWorkdir(PathBuf);

impl SafeWorkdir {
    pub fn new(path: PathBuf) -> Result<Self> {
        if path.as_os_str().is_empty() {
            return Err(anyhow!("workdir path cannot be empty"));
        }
        if !path.is_dir() {
            return Err(anyhow!("workdir does not exist or is not a directory: {}", path.display()));
        }
        Ok(Self(path))
    }

    pub fn as_path(&self) -> &Path {
        &self.0
    }
}
```

Now any function that takes `&SafeWorkdir` cannot be called with an unvalidated path — Layer 1
becomes a type signature instead of a runtime check.

## Applying the Pattern

When you find a bug:

1. **Trace the data flow** — where does bad value originate? Where is it used?
2. **Map all checkpoints** — list every point data passes through
3. **Add validation at each layer** — entry, business, environment, debug
4. **Test each layer** — try to bypass layer 1, verify layer 2 catches it

## Example from Session

Bug: Empty `projectDir` caused `git init` in source code.

**Data flow:**

1. Test setup → empty string
2. `Project.create(name, '')`
3. `WorkspaceManager.createWorkspace('')`
4. `git init` runs in `process.cwd()`

**Four layers added:**

- Layer 1: `Project.create()` validates not empty/exists
- Layer 2: `WorkspaceManager` validates projectDir not empty
- Layer 3: `WorktreeManager` refuses git init outside tmpdir
- Layer 4: Stack trace logging before git init

## Key Insight

All four layers were necessary. During testing, each layer caught bugs the others missed:

- Different code paths bypassed entry validation
- Mocks bypassed business logic checks
- Edge cases on different platforms needed environment guards
- Debug logging identified structural misuse

**Don't stop at one validation point.** Add checks at every layer.
