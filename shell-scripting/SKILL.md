---
name: shell-scripting
description: >-
  Comprehensive guide for writing, reviewing, refactoring, hardening, linting, and testing shell
  scripts in Bash (plus POSIX sh, dash, ksh) and PowerShell (5.1 and 7+, cross-platform). Covers
  strict mode, defensive patterns, quoting, error handling, traps, argument parsing, functions,
  arrays, portability, security (injection, eval, temp files), performance, logging, dependency
  checks, idempotency, dry-run, ShellCheck/shfmt/Bats/PSScriptAnalyzer/Pester, CI integration,
  cross-platform pitfalls, and production-ready templates. Use whenever the user mentions bash,
  sh, POSIX, Bourne, zsh, ksh, dash, shell, .sh, PowerShell, pwsh, .ps1, ShellCheck, shfmt, Bats,
  Pester, PSScriptAnalyzer, or asks to write/review/debug/lint/port/automate any kind of shell
  script, CLI tool, cron job, systemd ExecStart, Dockerfile RUN line, Makefile recipe, or CI
  pipeline shell step — even if a specific shell is not named.
---

# Shell Scripting

Production-grade Bash and PowerShell scripting: safety, portability, security, performance, testing,
and documentation. This skill is the single source of truth for any shell-related work.

## When to Use

Trigger this skill for any of:

- Writing a new shell script (`.sh`, `.bash`, `.ps1`, `.psm1`)
- Reviewing, debugging, or refactoring existing shell code
- Converting ad-hoc terminal commands into a maintainable script
- Adding `RUN` lines to a Dockerfile, recipes to a Makefile, or steps to a CI pipeline
- Writing cron jobs, systemd `ExecStart` directives, or git hooks
- Setting up linting (ShellCheck, shfmt, PSScriptAnalyzer) or testing (Bats, Pester)
- Porting a script between Bash, POSIX `sh`, zsh, or PowerShell
- Hardening scripts for production (strict mode, traps, secure temp files, input validation)
- Diagnosing portability issues across Linux, macOS, BSD, WSL, Git Bash, or PowerShell 5.1 vs 7+

## Decision: Which Shell?

| Situation | Use |
| --- | --- |
| Linux/macOS automation, modern features needed | Bash 4+ (`#!/usr/bin/env bash`) |
| Maximum portability across UNIX-likes (Alpine, BusyBox, embedded) | POSIX `sh` (`#!/bin/sh`) |
| Windows-native automation, Azure / M365 / AD | PowerShell 7+ (`pwsh`) |
| Cross-platform with strong typing and structured pipelines | PowerShell 7+ (`pwsh`) |
| Object pipelines, COM/.NET interop | PowerShell |
| One-liner pipelines with `grep`/`awk`/`sed` | Bash or POSIX `sh` |

Bash is the default unless the user is on Windows or asks for PowerShell. Pick POSIX `sh` only when
portability to non-Bash environments is a hard requirement — call this out explicitly.

## Reference Files

Load the relevant reference for deeper coverage:

| File | Read when |
| --- | --- |
| [references/bash.md](references/bash.md) | Writing or reviewing any Bash script |
| [references/bash-template.md](references/bash-template.md) | Need a complete production scaffold |
| [references/powershell.md](references/powershell.md) | Writing or reviewing PowerShell |
| [references/powershell-template.md](references/powershell-template.md) | Need a PowerShell scaffold |
| [references/portability.md](references/portability.md) | Targeting POSIX `sh` or multiple shells/OSes |
| [references/security.md](references/security.md) | Handling untrusted input, secrets, or temp files |
| [references/linting-and-testing.md](references/linting-and-testing.md) | Setting up ShellCheck, shfmt, Bats, Pester, PSScriptAnalyzer, or CI |
| [references/operational-recipes.md](references/operational-recipes.md) | Logging, retry/backoff, backups, monitoring, dependency checks |

## Workflow

Follow these steps for every shell-scripting task:

1. **Capture intent.** Confirm shell target, inputs/outputs, error behavior (fail-fast vs continue),
   portability needs, and whether the script is one-shot or production.
2. **Pick a foundation.** Use the templates in `references/bash-template.md` or
   `references/powershell-template.md` rather than starting from scratch.
3. **Write defensively.** Apply the universal principles below from the first line.
4. **Validate.** Run ShellCheck (Bash) or PSScriptAnalyzer (PowerShell) before declaring done. Run
   `bash -n script.sh` / `pwsh -NoProfile -Command "& {. ./script.ps1}"` for syntax.
5. **Test.** Add Bats or Pester tests for any non-trivial logic.
6. **Document.** Include a header comment, `--help`/`-h` output, and required dependencies.

## Universal Principles

These apply to both Bash and PowerShell:

1. **Fail fast, fail loud.** Errors must abort the script with a clear message on stderr and a
   non-zero exit code, unless explicitly handled.
2. **Quote everything.** Unquoted variables are the #1 source of shell bugs.
3. **Validate inputs at the boundary.** Check files exist, arguments are present, formats match —
   before doing any work.
4. **Clean up.** Use traps (Bash) or `try/finally` (PowerShell) to remove temp files, kill
   background jobs, and restore state on exit.
5. **Be idempotent.** Re-running the script must be safe. Check before creating, deleting, or
   modifying.
6. **Support `--dry-run` and `--verbose`.** Critical for any script that mutates state.
7. **Log to stderr, data to stdout.** Pipelines should be composable.
8. **Never `eval` user input.** Use arrays for command building instead.
9. **Lint as you write.** ShellCheck and PSScriptAnalyzer catch real bugs, not just style.

## Bash Quick Reference

### Mandatory script header

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly SCRIPT_NAME="$(basename -- "${BASH_SOURCE[0]}")"
```

| Flag | Effect |
| --- | --- |
| `-E` | ERR trap is inherited by functions, subshells, command substitutions |
| `-e` | Exit on any command failure |
| `-u` | Error on undefined variable reference |
| `-o pipefail` | Pipeline exit code is the first non-zero, not just the last command |
| `IFS=$'\n\t'` | Disables word splitting on spaces — array iteration becomes safe |

For Bash 4.4+, also add `shopt -s inherit_errexit` so `-e` propagates into command substitutions.

### Quoting and variables

```bash
# Always quote — even inside [[ ]]
echo "${name}"
cp "${source}" "${destination}"
[[ -f "${file}" ]] || die "File not found: ${file}"

# Defaults and required vars
port="${PORT:-8080}"                          # default if unset
: "${REQUIRED_VAR:?REQUIRED_VAR must be set}" # error if unset
readonly CONFIG_DIR="/etc/myapp"              # constant
local result=""                               # function-scoped
```

### Conditionals

Prefer `[[ ]]` over `[ ]` in Bash; reach for `(( ))` for arithmetic.

```bash
[[ -f "${file}" && -r "${file}" ]]       # file exists and is readable
[[ "${str}" == prefix_* ]]               # glob match
[[ "${str}" =~ ^[0-9]+$ ]]               # regex match
(( count > 10 ))                         # arithmetic comparison
```

| Test | Meaning | Test | Meaning |
| --- | --- | --- | --- |
| `-f` | regular file | `-d` | directory |
| `-e` | exists (any) | `-r` / `-w` / `-x` | readable / writable / executable |
| `-z` | empty string | `-n` | non-empty string |
| `-v VAR` | variable is set (Bash 4.2+) | `=~` | regex match |

### Functions

```bash
process_file() {
    local -r file="$1"
    local -r output="${2:-/dev/stdout}"

    [[ -f "${file}" ]] || { echo "ERROR: ${file} not found" >&2; return 1; }
    cat -- "${file}" > "${output}"
}
```

- Use `local` for every function variable (`local -r` for constants).
- Return non-zero on error; let the caller decide what to do.
- Send errors to stderr (`>&2`).
- Name functions `verb_noun` (`process_file`, `validate_input`).

### Loops and iteration

```bash
# Glob iteration (handles spaces)
for file in *.txt; do
    [[ -e "${file}" ]] || continue   # skip if no matches
    process "${file}"
done

# Read a file line-by-line, preserving whitespace
while IFS= read -r line; do
    echo "${line}"
done < input.txt

# NUL-safe iteration over find output
while IFS= read -r -d '' file; do
    process "${file}"
done < <(find . -type f -name '*.log' -print0)

# Read command output into an array
mapfile -t lines < <(some_command)
```

### Cleanup with trap

```bash
TMPDIR="$(mktemp -d)" || exit 1
trap 'rm -rf -- "${TMPDIR}"' EXIT
trap 'echo "ERROR on line ${LINENO}" >&2' ERR
```

### Argument parsing

```bash
verbose=false
output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--verbose) verbose=true; shift ;;
        -o|--output)  output="$2"; shift 2 ;;
        -h|--help)    usage; exit 0 ;;
        --)           shift; break ;;
        -*)           echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
        *)            break ;;
    esac
done
```

### Anti-patterns to flag

- Unquoted `$var` — use `"${var}"`
- `[ ]` in Bash where `[[ ]]` works — `[[ ]]` is safer and more featureful
- `cd dir` without error handling — use `cd -- "${dir}"` after `set -e`, or `cd ... || exit`
- Parsing `ls` output — use globs, `find -print0`, or `mapfile`
- `cat file | grep pattern` — use `grep pattern file`
- `for i in $(seq 1 N)` — use `for ((i=1; i<=N; i++))`
- `echo $?` after a command — use `if cmd; then ...; fi` instead
- `which cmd` — use `command -v cmd`
- Backticks `` `cmd` `` — use `$(cmd)`
- `eval` on anything containing user input — use arrays or printf %q

See [references/bash.md](references/bash.md) and
[references/bash-template.md](references/bash-template.md) for deeper coverage and a complete
production scaffold.

## PowerShell Quick Reference

### Mandatory script header

```powershell
#Requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$Path,

    [switch]$WhatIf
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSDefaultParameterValues['*:ErrorAction'] = 'Stop'
```

`Set-StrictMode -Version Latest` + `$ErrorActionPreference = 'Stop'` is the PowerShell equivalent of
`set -euo pipefail`. Without them, errors are silently swallowed.

### Naming and style

- Functions use `Verb-Noun` with **approved verbs** (`Get-Verb` to list).
- Use full cmdlet names (`Get-ChildItem`), never aliases (`ls`, `gci`) in scripts.
- PascalCase for parameters and functions, camelCase for local variables.
- Always specify `-Encoding utf8` on file I/O for cross-platform consistency.

### Cross-platform paths

```powershell
# Good — works on Windows, Linux, macOS
$config = Join-Path $PSScriptRoot 'config.json'
$temp   = [System.IO.Path]::GetTempPath()

# Bad — Windows only
$config = "$PSScriptRoot\config.json"
```

Use the `$IsWindows`, `$IsLinux`, `$IsMacOS` automatic variables for OS branching (PS 7+).

### Error handling

```powershell
try {
    $content = Get-Content -Path $Path -Raw -ErrorAction Stop
}
catch [System.IO.FileNotFoundException] {
    Write-Error "File not found: $Path"
    exit 1
}
catch {
    Write-Error "Unexpected error: $($_.Exception.Message)"
    exit 1
}
finally {
    if ($tempFile) { Remove-Item $tempFile -Force -ErrorAction SilentlyContinue }
}
```

### Common pitfalls

| Wrong | Right |
| --- | --- |
| `if (Test-Path "a" -or Test-Path "b")` | `if ((Test-Path "a") -or (Test-Path "b"))` |
| `ConvertTo-Json $obj` | `ConvertTo-Json $obj -Depth 10` |
| `$array.Count -gt 0` (when `$array` may be `$null`) | `$array -and $array.Count -gt 0` |
| `"Value: $($obj.a.b.c)"` (deep interp) | Assign to `$tmp` first, then interpolate |
| Using emoji/Unicode in script output | Use ASCII (`[OK]`, `[ERR]`, `[WARN]`) |

### Functions with full plumbing

```powershell
function Get-LogError {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory, ValueFromPipeline)]
        [string]$LogPath,

        [int]$MaxResults = 100
    )
    process {
        if (-not (Test-Path -LiteralPath $LogPath)) {
            throw "Log not found: $LogPath"
        }
        Select-String -Path $LogPath -Pattern 'ERROR' |
            Select-Object -First $MaxResults
    }
}
```

See [references/powershell.md](references/powershell.md) and
[references/powershell-template.md](references/powershell-template.md) for cmdlets, modules,
PSResourceGet, security (JEA, WDAC, script block logging), and production scaffolds.

## Linting and Testing — Always

Every shell script must pass static analysis before being considered done.

| Language | Linter | Formatter | Test framework |
| --- | --- | --- | --- |
| Bash | `shellcheck` | `shfmt -i 4 -ci` | `bats-core` |
| POSIX `sh` | `shellcheck --shell=sh` | `shfmt -p` | `bats-core` |
| PowerShell | `Invoke-ScriptAnalyzer` | (built-in via PSSA rules) | `Pester` |

Quick checks:

```bash
shellcheck script.sh                   # lint
shfmt -d script.sh                     # show formatting diff
bash -n script.sh                      # syntax-only check
bats tests/                            # run tests
```

```powershell
Invoke-ScriptAnalyzer -Path . -Recurse -Severity Warning
Invoke-Pester -Path ./tests -Output Detailed
```

See [references/linting-and-testing.md](references/linting-and-testing.md) for installation,
configuration files (`.shellcheckrc`, `PSScriptAnalyzerSettings.psd1`), suppression syntax, CI
templates (GitHub Actions, GitLab CI, Azure DevOps), and Bats / Pester patterns.

## Security Checklist

Before shipping any script that handles untrusted input or runs with elevated privileges:

- [ ] No `eval` on any string derived from user input
- [ ] All variables expanding into commands are quoted (`"${var}"`)
- [ ] Temp files created with `mktemp` (Bash) or `New-TemporaryFile` (PS), cleaned up via trap
- [ ] Input validated against an allow-list regex before use
- [ ] `--` used to terminate options before file paths (`rm -- "${file}"`)
- [ ] Absolute paths used for security-critical commands, or `PATH` is explicitly set
- [ ] No SUID/SGID bits on shell scripts (kernel ignores them anyway, but the intent is unsafe)
- [ ] Secrets read from env vars or files with restricted permissions, never CLI args
- [ ] Output of `printf '%q'` (Bash) or
      `[Management.Automation.Language.CodeGeneration]::EscapeFormatStringContent` (PS) used when
      interpolating into shell strings is unavoidable

See [references/security.md](references/security.md) for full guidance on injection prevention,
secure temp files, secret handling, and command construction with arrays.

## Operational Recipes

For ready-to-adapt snippets covering structured logging with levels and timestamps, retry with
exponential backoff, dependency checking, dry-run flag plumbing, atomic file writes, signal handling
for background processes, and common admin patterns (backup, rotation, monitoring, user management),
see [references/operational-recipes.md](references/operational-recipes.md).

## Common Tasks

### "Convert these commands into a script"

1. Read the commands. Identify inputs (env vars, file paths) and outputs.
2. Start from the Bash or PowerShell template.
3. Wrap the commands in a `main` function. Add `parse_args`, `validate`, `cleanup`.
4. Replace hard-coded values with `${1:-default}` / `param()` arguments.
5. Lint and test.

### "Why does my script silently fail?"

Almost always missing `set -Eeuo pipefail` (Bash) or `Set-StrictMode -Version Latest` +
`$ErrorActionPreference = 'Stop'` (PowerShell). Add them, then rerun.

### "Make this script portable to Alpine/BusyBox"

Switch to POSIX `sh`. See [references/portability.md](references/portability.md) for the mapping
table (no `[[ ]]`, no arrays, no `${var//pat/repl}`, etc.) and `shellcheck --shell=sh` to verify.

### "How do I test a shell script?"

Bats for Bash, Pester for PowerShell. See
[references/linting-and-testing.md](references/linting-and-testing.md) for setup and patterns
(mocking commands, asserting output, capturing exit codes, testing failure paths).
