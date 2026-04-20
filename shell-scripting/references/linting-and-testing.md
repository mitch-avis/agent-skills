# Linting and Testing

Static analysis and testing for shell scripts. **Required** before declaring any script done.

## Bash: ShellCheck

[ShellCheck](https://www.shellcheck.net/) catches the great majority of real bugs in shell scripts.
Treat warnings as errors in CI.

### Installation

```bash
# macOS
brew install shellcheck

# Debian/Ubuntu
sudo apt-get install -y shellcheck

# Alpine
apk add --no-cache shellcheck

# Or via the official Docker image
docker run --rm -v "$PWD:/mnt" koalaman/shellcheck script.sh
```

### Usage

```bash
shellcheck script.sh                            # default checks
shellcheck --shell=bash script.sh               # explicit shell
shellcheck --shell=sh script.sh                 # POSIX mode
shellcheck --severity=warning script.sh         # error|warning|info|style
shellcheck --enable=all script.sh               # enable optional checks
shellcheck --format=gcc script.sh               # gcc-compatible output (CI/editors)
shellcheck --format=json script.sh              # for tooling
shellcheck --external-sources script.sh         # follow `source` directives
```

### `.shellcheckrc` (project root)

```text
shell=bash

# Optional checks worth enabling
enable=avoid-nullary-conditions
enable=require-variable-braces
enable=check-unassigned-uppercase
enable=quote-safe-variables

# Sourced files
external-sources=true

# Suppressions (justify each!)
# SC1091: Not following sourced files when path can't be resolved at lint time
disable=SC1091
```

### In-script suppressions

Always pin the suppression to the smallest scope and add a comment explaining **why**:

```bash
# shellcheck disable=SC2034  # exported via `set -a` below; intentional
unused_var="value"

# shellcheck source=./lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
```

### High-impact codes to know

| Code | Meaning | Fix |
| --- | --- | --- |
| SC2086 | Unquoted expansion (most common) | `"$var"` |
| SC2046 | Unquoted command substitution | `"$(cmd)"` |
| SC2155 | `local x=$(cmd)` masks return code | `local x; x=$(cmd)` |
| SC2164 | `cd` without `\|\| exit` | `cd dir \|\| exit` (or rely on `set -e`) |
| SC2181 | `if [ $? -eq 0 ]` | `if cmd; then` |
| SC2009 | `ps \| grep` | `pgrep` |
| SC2012 | Parsing `ls` | use globs or `find` |
| SC2068 | `$@` unquoted | `"$@"` |
| SC2148 | Missing shebang | add `#!/usr/bin/env bash` |
| SC2128 | Expanding array as scalar | `"${arr[@]}"` |
| SC1091 | `source`d file not found at lint time | add `# shellcheck source=path` |

## Bash: shfmt

Auto-formatter for shell scripts. Pairs perfectly with ShellCheck.

```bash
go install mvdan.cc/sh/v3/cmd/shfmt@latest    # or: brew install shfmt
shfmt -d script.sh                            # diff (don't write)
shfmt -w -i 4 -ci -bn -sr script.sh           # write in place
```

| Flag | Meaning |
| --- | --- |
| `-i N` | Indent by N spaces (use `0` for tabs) |
| `-ci` | Switch cases indented |
| `-bn` | Binary ops at line start |
| `-sr` | Space after redirect operators (`> foo` not `>foo`) |
| `-p` | POSIX `sh` mode |

## Bash: Bats (testing)

[Bats-core](https://github.com/bats-core/bats-core) — the de-facto Bash test framework.

### Install

```bash
brew install bats-core
# or
git clone https://github.com/bats-core/bats-core.git && cd bats-core && ./install.sh /usr/local
```

### Test layout

```text
tests/
├── helpers/
│   └── test_helper.bash
├── fixtures/
│   └── sample.csv
└── greet.bats
```

### `tests/greet.bats`

```bash
#!/usr/bin/env bats

setup() {
    load 'helpers/test_helper'
    SCRIPT="${BATS_TEST_DIRNAME}/../bin/greet.sh"
    TMPDIR="$(mktemp -d)"
}

teardown() {
    rm -rf -- "${TMPDIR}"
}

@test "prints help with -h" {
    run "${SCRIPT}" -h
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "fails on missing input" {
    run "${SCRIPT}"
    [ "$status" -eq 2 ]
    [[ "$output" == *"required"* ]]
}

@test "greets a single user" {
    run "${SCRIPT}" --name alice
    [ "$status" -eq 0 ]
    [ "$output" = "Hello, alice" ]
}

@test "handles names with spaces" {
    run "${SCRIPT}" --name "Ada Lovelace"
    [ "$status" -eq 0 ]
    [ "$output" = "Hello, Ada Lovelace" ]
}

@test "stub external command" {
    function curl() { echo "stubbed"; }
    export -f curl
    run "${SCRIPT}" --fetch
    [[ "$output" == *"stubbed"* ]]
}
```

### Run

```bash
bats tests/                          # all
bats --tap tests/                    # TAP output (CI)
bats --filter "greets" tests/        # by name
bats --jobs 4 tests/                 # parallel (bats 1.5+)
```

Useful add-ons: [`bats-assert`](https://github.com/bats-core/bats-assert),
[`bats-support`](https://github.com/bats-core/bats-support),
[`bats-mock`](https://github.com/grayhemp/bats-mock).

## PowerShell: PSScriptAnalyzer

```powershell
Install-PSResource -Name PSScriptAnalyzer -Scope CurrentUser
# or: Install-Module PSScriptAnalyzer -Scope CurrentUser -Force

Invoke-ScriptAnalyzer -Path . -Recurse
Invoke-ScriptAnalyzer -Path . -Recurse -Severity Warning, Error
Invoke-ScriptAnalyzer -Path . -Recurse -ReportSummary
Invoke-ScriptAnalyzer -Path .\script.ps1 -Fix     # auto-fix where possible
```

### `PSScriptAnalyzerSettings.psd1`

```powershell
@{
    Severity     = @('Error', 'Warning')
    IncludeRules = @('PS*')
    ExcludeRules = @(
        'PSAvoidUsingWriteHost'   # OK in interactive scripts
    )
    Rules = @{
        PSUseCompatibleSyntax = @{
            Enable         = $true
            TargetVersions = @('5.1', '7.0')
        }
        PSPlaceOpenBrace = @{
            Enable             = $true
            OnSameLine         = $true
            NewLineAfter       = $true
            IgnoreOneLineBlock = $true
        }
        PSUseConsistentIndentation = @{
            Enable          = $true
            IndentationSize = 4
            Kind            = 'space'
        }
    }
}
```

Reference it: `Invoke-ScriptAnalyzer -Settings .\PSScriptAnalyzerSettings.psd1 -Path .`

### Suppress in-source (justify each!)

```powershell
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSUseShouldProcessForStateChangingFunctions', '',
    Justification = 'Read-only despite verb')]
param(...)
```

### High-impact rules

| Rule | Means |
| --- | --- |
| `PSAvoidUsingCmdletAliases` | No `ls`, `gci`, `?`, `%` etc. in scripts |
| `PSAvoidUsingPositionalParameters` | Use named params for clarity |
| `PSUseDeclaredVarsMoreThanAssignments` | Catch typos / unused vars |
| `PSAvoidUsingPlainTextForPassword` | Use `[SecureString]` or `PSCredential` |
| `PSUseShouldProcessForStateChangingFunctions` | Mutating funcs need `-WhatIf`/`-Confirm` |
| `PSUseSingularNouns` | `Get-User` not `Get-Users` |
| `PSAvoidUsingInvokeExpression` | `iex` is code injection |

## PowerShell: Pester (testing)

```powershell
Install-PSResource -Name Pester -Scope CurrentUser

# Layout: tests/<Name>.Tests.ps1
```

### `tests/Get-Greeting.Tests.ps1`

```powershell
BeforeAll {
    . $PSCommandPath.Replace('.Tests.ps1', '.ps1')
}

Describe 'Get-Greeting' {
    Context 'happy path' {
        It 'greets the named user' {
            Get-Greeting -Name 'alice' | Should -Be 'Hello, alice'
        }

        It 'handles names with spaces' {
            Get-Greeting -Name 'Ada Lovelace' | Should -Be 'Hello, Ada Lovelace'
        }
    }

    Context 'errors' {
        It 'throws on empty name' {
            { Get-Greeting -Name '' } | Should -Throw
        }
    }

    Context 'mocking' {
        It 'calls the API' {
            Mock Invoke-RestMethod { @{ ok = $true } }
            Get-Greeting -Name 'alice' -FromApi | Should -Not -BeNullOrEmpty
            Should -Invoke Invoke-RestMethod -Times 1 -Exactly
        }
    }
}
```

### Run

```powershell
Invoke-Pester                                          # discover & run
Invoke-Pester -Path .\tests -Output Detailed
Invoke-Pester -Path .\tests -CI                        # fail-fast, JUnit-style output
Invoke-Pester -Path .\tests -CodeCoverage .\src\*.ps1
```

## Pre-commit Hooks

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/koalaman/shellcheck-precommit
    rev: v0.10.0
    hooks:
      - id: shellcheck

  - repo: https://github.com/scop/pre-commit-shfmt
    rev: v3.8.0-1
    hooks:
      - id: shfmt
        args: ['-i', '4', '-ci', '-w']

  - repo: local
    hooks:
      - id: psscriptanalyzer
        name: PSScriptAnalyzer
        entry: pwsh -NoProfile -Command "Invoke-ScriptAnalyzer -Path . -Recurse -EnableExit"
        language: system
        files: \.ps(m|d)?1$
```

## CI Templates

### GitHub Actions — full quality gate

```yaml
name: shell-quality

on: [push, pull_request]

jobs:
  bash:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: ShellCheck
        uses: ludeeus/action-shellcheck@master
        with:
          severity: warning
          scandir: '.'

      - name: shfmt
        uses: luizm/action-sh-checker@master
        env:
          SHFMT_OPTS: -i 4 -ci -d

      - name: Bats
        run: |
          sudo apt-get install -y bats
          bats --tap tests/

  powershell:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: PSScriptAnalyzer
        shell: pwsh
        run: |
          Install-Module PSScriptAnalyzer -Force -Scope CurrentUser
          $issues = Invoke-ScriptAnalyzer -Path . -Recurse -Severity Warning, Error
          $issues | Format-Table
          if ($issues) { exit 1 }
      - name: Pester
        shell: pwsh
        run: |
          Install-Module Pester -Force -Scope CurrentUser
          Invoke-Pester -Path ./tests -CI
```

### GitLab CI

```yaml
shellcheck:
  image: koalaman/shellcheck-alpine:stable
  script:
    - shellcheck -S warning $(find . -type f -name '*.sh')

bats:
  image: bats/bats:latest
  script:
    - bats --tap tests/

psscriptanalyzer:
  image: mcr.microsoft.com/powershell:latest
  script:
    - pwsh -c "Install-Module PSScriptAnalyzer -Force; Invoke-ScriptAnalyzer -Path . -Recurse -EnableExit"
```

## Quick Sanity Checks

Before opening a PR, at minimum run:

```bash
# Bash
bash -n script.sh && shellcheck script.sh && shfmt -d script.sh && bats tests/

# PowerShell
pwsh -NoProfile -Command "
    \$ErrorActionPreference = 'Stop'
    Invoke-ScriptAnalyzer -Path . -Recurse -EnableExit
    Invoke-Pester -Path ./tests -CI
"
```
