# Bash Reference

Comprehensive Bash scripting patterns. Apply these on top of the strict-mode foundation in the main
SKILL.md.

## Table of Contents

- [Bash Reference](#bash-reference)
  - [Table of Contents](#table-of-contents)
  - [Strict Mode and the Mandatory Header](#strict-mode-and-the-mandatory-header)
  - [Variables and Scope](#variables-and-scope)
  - [Conditionals and Tests](#conditionals-and-tests)
  - [Loops and Iteration](#loops-and-iteration)
  - [Arrays](#arrays)
  - [Functions](#functions)
  - [Argument Parsing](#argument-parsing)
    - [Manual `case` (most common)](#manual-case-most-common)
    - [`getopts` (POSIX, short options only)](#getopts-posix-short-options-only)
  - [Error Handling and Traps](#error-handling-and-traps)
  - [Command Substitution and Pipelines](#command-substitution-and-pipelines)
  - [Strings and Parameter Expansion](#strings-and-parameter-expansion)
  - [File and Path Operations](#file-and-path-operations)
  - [Process Management](#process-management)
  - [Performance](#performance)
  - [Common Anti-Patterns](#common-anti-patterns)

## Strict Mode and the Mandatory Header

```bash
#!/usr/bin/env bash
#
# script-name.sh — one-line description
#
# Usage: script-name.sh [OPTIONS] ARGUMENTS
#
set -Eeuo pipefail
shopt -s inherit_errexit nullglob   # Bash 4.4+: errexit propagates into $(...); empty globs OK
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly SCRIPT_NAME="$(basename -- "${BASH_SOURCE[0]}")"
readonly SCRIPT_VERSION="1.0.0"
```

| Setting | Purpose |
| --- | --- |
| `set -E` | Functions and subshells inherit ERR trap |
| `set -e` | Exit on first uncaught command failure |
| `set -u` | Treat undefined variables as errors |
| `set -o pipefail` | Pipeline returns first non-zero exit, not just last |
| `shopt -s inherit_errexit` | `set -e` propagates into `$(...)` (Bash 4.4+) |
| `shopt -s nullglob` | Non-matching globs expand to nothing instead of literal pattern |
| `IFS=$'\n\t'` | Disables splitting on spaces; safer iteration |

For interactive debugging, add `set -x` (trace) or `PS4='+ ${BASH_SOURCE}:${LINENO}: '`.

## Variables and Scope

```bash
# Naming: lowercase_with_underscores for locals, UPPERCASE for env / readonly
local user_input="$1"
readonly MAX_RETRIES=3
declare -i counter=0          # integer
declare -a items=()           # indexed array
declare -A config=()          # associative array (Bash 4+)

# Defaults and required
port="${PORT:-8080}"          # use default if PORT unset/empty
: "${API_KEY:?API_KEY is required}"   # fail with message if unset

# Indirect expansion
varname="HOME"; echo "${!varname}"    # prints $HOME

# Always brace + quote in interpolation
echo "log_${name}_$(date +%F).txt"    # OK
echo "log_$name_$(date +%F).txt"      # WRONG: $name_ is one identifier
```

## Conditionals and Tests

```bash
# Bash: prefer [[ ]]
if [[ -f "${file}" && -r "${file}" ]]; then ...; fi
if [[ "${str}" == prefix_* ]];        then ...; fi   # glob
if [[ "${str}" =~ ^[0-9]+$ ]];        then ...; fi   # regex (anchored, no quotes on RHS)

# Arithmetic: (( ))
if (( count > 10 )); then ...; fi
if (( ${#array[@]} == 0 )); then ...; fi

# String tests
[[ -z "$str" ]]   # empty
[[ -n "$str" ]]   # non-empty

# Don't quote the regex on the right side of =~
[[ "${ip}" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]
```

| Test | True if | Test | True if |
| --- | --- | --- | --- |
| `-f f` | regular file | `-d d` | directory |
| `-e p` | path exists | `-L p` | symlink |
| `-s f` | file non-empty | `-r p` | readable |
| `-w p` | writable | `-x p` | executable |
| `-O p` | owned by user | `-G p` | owned by group |
| `f1 -nt f2` | f1 newer | `f1 -ot f2` | f1 older |

## Loops and Iteration

```bash
# Glob iteration (with nullglob, empty matches are skipped automatically)
for file in *.txt; do
    process "${file}"
done

# C-style
for (( i = 0; i < 10; i++ )); do echo "$i"; done

# Read file line-by-line, preserving leading/trailing whitespace
while IFS= read -r line; do
    echo "${line}"
done < input.txt

# NUL-safe iteration over find output (handles weird filenames)
while IFS= read -r -d '' file; do
    process "${file}"
done < <(find . -type f -name '*.log' -print0)

# Read command output into array
mapfile -t lines < <(grep ERROR app.log)
readarray -t numbers < <(seq 1 10)
```

**Never** parse `ls`. Use globs, `find -print0`, or `mapfile`.

## Arrays

```bash
# Indexed
declare -a files=()
files+=("one.txt" "two.txt")
echo "${files[0]}"          # first element
echo "${files[@]}"          # all elements (word-split, individually quoted)
echo "${files[*]}"          # all elements joined by IFS (single string)
echo "${#files[@]}"         # length
echo "${!files[@]}"         # indices
unset 'files[0]'            # remove element
files=("${files[@]}")       # reindex

# Associative (Bash 4+)
declare -A user=([name]="alice" [uid]=1000)
echo "${user[name]}"
[[ -v user[name] ]] && echo "key exists"
for key in "${!user[@]}"; do echo "$key=${user[$key]}"; done

# Pass array to function
process_files() {
    local -a files=("$@")     # copy positional args into local array
    for f in "${files[@]}"; do echo "$f"; done
}
process_files "${files[@]}"
```

## Functions

```bash
# Anatomy
process_log() {
    local -r log_file="$1"
    local -r output_dir="${2:-./output}"
    local error_count=0

    [[ -f "${log_file}" ]] || { log_error "Not found: ${log_file}"; return 1; }

    error_count=$(grep -c ERROR "${log_file}" || true)   # || true: 0 matches isn't an error
    printf '%d\n' "${error_count}"
}

# Capture output
count=$(process_log /var/log/app.log) || die "process_log failed"

# Use status only
if process_log /var/log/app.log >/dev/null; then
    echo "ok"
fi
```

Rules:

- `local` (or `local -r`) for **every** internal variable.
- Return small integer status (`return 0..255`); print data on stdout, errors on stderr.
- Function name = `verb_noun` (e.g., `validate_input`, `process_file`, `cleanup_workdir`).
- Document arguments and return value in a comment block above the function.

## Argument Parsing

### Manual `case` (most common)

```bash
verbose=false
output=""
positional=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--verbose)  verbose=true; shift ;;
        -o|--output)   output="$2"; shift 2 ;;
        --output=*)    output="${1#*=}"; shift ;;
        -h|--help)     usage; exit 0 ;;
        --version)     printf '%s\n' "${SCRIPT_VERSION}"; exit 0 ;;
        --)            shift; positional+=("$@"); break ;;
        -*)            die "Unknown option: $1" ;;
        *)             positional+=("$1"); shift ;;
    esac
done
set -- "${positional[@]}"

[[ -n "${output}" ]] || die "--output is required"
```

### `getopts` (POSIX, short options only)

```bash
while getopts ':vo:h' opt; do
    case "${opt}" in
        v) verbose=true ;;
        o) output="${OPTARG}" ;;
        h) usage; exit 0 ;;
        :) die "Option -${OPTARG} requires an argument" ;;
        \?) die "Unknown option: -${OPTARG}" ;;
    esac
done
shift $((OPTIND - 1))
```

## Error Handling and Traps

```bash
# Multiple traps stack (define from outermost to innermost cleanup)
TMPDIR="$(mktemp -d)" || exit 1

cleanup() {
    local -ri exit_code=$?
    rm -rf -- "${TMPDIR}"
    return "${exit_code}"
}

err_handler() {
    local -ri exit_code=$?
    printf 'ERROR: %s line %d: command exited with status %d\n' \
        "${SCRIPT_NAME}" "${BASH_LINENO[0]}" "${exit_code}" >&2
}

trap cleanup EXIT
trap err_handler ERR
trap 'log_warn "Interrupted"; exit 130' INT TERM

# Logging primitives
log()       { printf '[%(%F %T)T] [%s] %s\n' -1 "$1" "${*:2}" >&2; }
log_info()  { log INFO  "$@"; }
log_warn()  { log WARN  "$@"; }
log_error() { log ERROR "$@"; }
log_debug() { [[ "${DEBUG:-0}" == 1 ]] && log DEBUG "$@" || true; }
die()       { log_error "$@"; exit 1; }
```

To opt out of `set -e` for a single command: append `|| true`. To capture an exit code without
aborting: `cmd && status=0 || status=$?`.

## Command Substitution and Pipelines

```bash
# Always $(), never backticks
result=$(curl -fsS https://example.com)

# Read whole file into variable
content=$(<"$file")             # faster than $(cat "$file")

# Process substitution (avoid pipe creating subshell that loses variables)
while IFS= read -r line; do
    (( count++ ))
done < <(grep ERROR app.log)
echo "$count"                   # works; would be 0 if you used `grep ... | while`

# Multiple commands into array
mapfile -t users < <(awk -F: '{print $1}' /etc/passwd)
```

`pipefail` is critical: without it, `cmd_that_fails | cat` exits 0.

## Strings and Parameter Expansion

```bash
str="hello-world.txt"

${str#prefix}     # strip shortest matching prefix     -> "hello-world.txt" (no match)
${str%.txt}       # strip shortest matching suffix     -> "hello-world"
${str%.*}         # strip everything after last `.`    -> "hello-world"
${str##*-}        # strip longest prefix up to last `-` -> "world.txt"
${str/-/_}        # replace first `-` with `_`          -> "hello_world.txt"
${str//-/_}       # replace all `-` with `_`            -> "hello_world.txt"
${str^^}          # uppercase all                       -> "HELLO-WORLD.TXT"
${str,,}          # lowercase all
${str:0:5}        # substring (offset 0, length 5)      -> "hello"
${#str}           # length                              -> 15

# printf is more predictable than echo
printf '%s\n' "$value"
printf '%q\n' "$value"          # shell-quoted (safe for re-use in shell strings)
printf -v var '%s_%d' "$name" "$id"   # assign without subshell
```

## File and Path Operations

```bash
# Atomic write
tmp=$(mktemp -p "$(dirname -- "$target")")
trap 'rm -f -- "$tmp"' EXIT
generate_content > "$tmp"
mv -- "$tmp" "$target"           # atomic on same filesystem

# Safer mkdir (idempotent)
mkdir -p -- "$dir"

# Resolve a real path (Bash + GNU coreutils)
real=$(readlink -f -- "$path")

# Loop only over existing matches
shopt -s nullglob
for f in *.bak; do rm -- "$f"; done
shopt -u nullglob
```

## Process Management

```bash
# Run with timeout (coreutils)
timeout 30s long_running_command || die "timed out"

# Track and clean up background jobs
declare -a pids=()
worker &;            pids+=($!)
another_worker &;    pids+=($!)

cleanup_jobs() {
    for pid in "${pids[@]}"; do
        kill -TERM "$pid" 2>/dev/null || true
    done
    for pid in "${pids[@]}"; do
        wait "$pid" 2>/dev/null || true
    done
}
trap cleanup_jobs EXIT

# Parallel work via xargs
printf '%s\0' "${files[@]}" | xargs -0 -P 4 -n 1 process_file
```

## Performance

- Prefer Bash builtins (`[[`, `(( ))`, parameter expansion) over forking external commands (`grep`,
  `sed`, `awk`) inside tight loops.
- Process files line-by-line with `while read` rather than reading the whole file repeatedly.
- Avoid useless subshells: `var=$(echo "$x")` → `var=$x`.
- Combine pipelines: `grep ... | sort | uniq` is one fork chain; `for f in $(grep ...); do ...`
  forks per match.
- Use `printf -v var ...` instead of `var=$(printf ...)` to skip the subshell.
- For very large data, switch to `awk` or a real language — Bash is not a data processor.

## Common Anti-Patterns

| Anti-pattern | Fix |
| --- | --- |
| `cat file \| grep pat` | `grep pat file` |
| `for f in $(ls *.txt)` | `for f in *.txt` |
| `if [ $? -eq 0 ]` | `if cmd; then` |
| `which cmd` | `command -v cmd` |
| `` `cmd` `` (backticks) | `$(cmd)` |
| `echo -e "$x"` | `printf '%b\n' "$x"` |
| `cd dir; cmd` | `(cd dir && cmd)` or `cd dir \|\| exit` |
| `[[ $count > 10 ]]` (string compare!) | `(( count > 10 ))` |
| `eval "$cmd"` with user input | Build an array: `cmd=(grep "$pat" "$file"); "${cmd[@]}"` |
| `rm -rf $dir/*` (unquoted!) | `rm -rf -- "${dir:?}"/*` (the `:?` aborts if `$dir` is empty) |
