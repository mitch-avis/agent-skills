# Portability

Guidance for writing shell scripts that work across multiple shells (POSIX `sh`, Bash, Dash,
Ksh, Zsh) and operating systems (Linux distros, macOS, BSD, WSL, Git Bash).

## Choose the Right Shebang

| Shebang | Use when |
| --- | --- |
| `#!/usr/bin/env bash` | Default for new scripts. Works wherever `bash` is on `PATH`. |
| `#!/bin/bash` | Faster startup, but assumes Bash is at `/bin/bash` (false on some systems). |
| `#!/bin/sh` | True POSIX-only scripts. Cannot use any Bash-specific features. |
| `#!/usr/bin/env pwsh` | Cross-platform PowerShell 7+. |

`/bin/sh` is **not** Bash on Debian/Ubuntu (it's `dash`), Alpine (`busybox sh`), or Android.
Writing `#!/bin/sh` and using `[[ ]]` will silently fail on those systems.

## Bashism Detection

Run ShellCheck in POSIX mode to find Bash-isms:

```bash
shellcheck --shell=sh script.sh
```

`checkbashisms` (Debian's `devscripts` package) is a complementary tool.

## Bash → POSIX `sh` Mapping

| Bash feature | POSIX equivalent |
| --- | --- |
| `[[ expr ]]` | `[ expr ]` (with quoting) — separate `&&` instead of `-a` |
| `[[ str =~ regex ]]` | `expr "$str" : 'regex'` or `case "$str" in pat) ... ;; esac` |
| `(( arith ))` | `[ "$((expr))" -ne 0 ]` |
| `arr=(a b c)` arrays | Space-separated string + `set -- a b c` (use `"$@"`) |
| `${arr[@]}` | `"$@"` |
| `${var//pat/repl}` | `echo "$var" \| sed 's/pat/repl/g'` |
| `${var^^}`, `${var,,}` | `echo "$var" \| tr a-z A-Z` / `tr A-Z a-z` |
| `${var:offset:len}` | `expr substr "$var" $((offset+1)) $len` |
| `local var` (in functions) | Not POSIX. Use unique names or subshells. |
| `function name { }` | `name() { }` |
| `read -r` (long opts) | `read -r` is fine; `-p prompt` is not POSIX |
| Process substitution `<(...)` | Named pipes (`mkfifo`) or temp files |
| Here-strings `<<<` | `printf '%s\n' "$x" \| ...` |
| `mapfile -t arr <file` | `while IFS= read -r line; do ...; done < file` |
| `echo -e`, `echo -n` | Use `printf` (always portable) |
| `source file` | `. file` |
| `\d`, `\w`, `\s` in regex | Use POSIX classes: `[[:digit:]]`, `[[:alpha:]]`, `[[:space:]]` |

## POSIX `sh` Strict Mode

POSIX `sh` doesn't support `pipefail`. The closest you get:

```sh
#!/bin/sh
set -eu
# IFS="$(printf '\n\t')"   # uncomment for safer iteration
```

To approximate `pipefail` portably, write to a temp and check intermediate codes:

```sh
out=$(producer 2>&1) || die "producer failed"
echo "$out" | consumer
```

## Cross-Platform Command Differences

### `sed -i` (in-place edit)

```bash
# GNU (Linux)
sed -i 's/old/new/' file

# BSD (macOS) — requires backup arg, even if empty
sed -i '' 's/old/new/' file

# Portable: write to temp, move
tmp=$(mktemp) && sed 's/old/new/' file > "$tmp" && mv "$tmp" file
```

### `readlink -f` (canonicalize path)

```bash
# GNU
readlink -f path

# macOS (no -f)
brew install coreutils
greadlink -f path

# Pure portable
realpath() (
    cd -P -- "$(dirname -- "$1")" && printf '%s\n' "$PWD/${1##*/}"
)
```

### `date` arithmetic

```bash
# GNU
date -d '1 day ago' +%F

# BSD
date -v -1d +%F

# Portable
python3 -c "import datetime; print((datetime.date.today() - datetime.timedelta(days=1)).isoformat())"
```

### `find` differences

```bash
# GNU `find -printf` — not POSIX, not on BSD
find . -printf '%P\n'

# Portable
find . -type f -exec basename {} \;
```

### `grep -P` (PCRE) — not portable

Use `grep -E` (extended) or `awk` / `perl` instead.

### `xargs -r` (skip if empty input) — not POSIX

```bash
# Portable equivalent
find . -name '*.tmp' -print0 | { read -r -d '' first || exit 0; printf '%s\0%s' "$first" "$(cat)"; } | xargs -0 rm
# Or simpler: just use find -delete or -exec
```

## OS Detection

```bash
case "$(uname -s)" in
    Linux*)     OS=Linux ;;
    Darwin*)    OS=macOS ;;
    CYGWIN*|MINGW*|MSYS*) OS=Windows ;;
    FreeBSD*)   OS=FreeBSD ;;
    *)          OS=Unknown ;;
esac

case "$(uname -m)" in
    x86_64|amd64) ARCH=amd64 ;;
    arm64|aarch64) ARCH=arm64 ;;
    *)            ARCH=$(uname -m) ;;
esac

# Distro detection on Linux
if [[ -r /etc/os-release ]]; then
    . /etc/os-release
    echo "${ID} ${VERSION_ID}"   # debian 12, alpine 3.19, etc.
fi
```

In PowerShell 7+:

```powershell
if     ($IsWindows) { ... }
elseif ($IsLinux)   { ... }
elseif ($IsMacOS)   { ... }
$PSVersionTable.OS         # full OS string
$PSVersionTable.Platform   # 'Win32NT' or 'Unix'
```

## Locale and Encoding

Force a deterministic locale at the top of any script that processes text, to avoid surprises
with `sort`, `awk`, `tr`, regex character classes, etc.:

```bash
export LC_ALL=C        # POSIX/byte locale — fastest, most predictable
export LANG=C
```

Use `LC_ALL=C.UTF-8` instead if you need UTF-8 awareness (available on most modern systems).

## Git Bash / MSYS / Cygwin Pitfalls

- Path translation: `C:\foo\bar` ↔ `/c/foo/bar`. MSYS auto-converts when calling Windows
  binaries; this can mangle args. Disable with `MSYS_NO_PATHCONV=1`.
- Line endings: configure git with `core.autocrlf=input` on Linux/macOS, `true` on Windows.
- Some commands (`ps`, `kill`) behave differently from native Linux equivalents.
- Always test scripts on the target platform before shipping.

## Checklist for "Truly Portable" Scripts

- [ ] Shebang is `#!/bin/sh`, not `#!/bin/bash`
- [ ] `shellcheck --shell=sh` passes
- [ ] No `[[ ]]`, `(( ))`, arrays, process substitution, `<<<`, `local`, `source`
- [ ] All `echo` calls replaced with `printf`
- [ ] `sed -i`, `readlink -f`, `date -d` and similar avoided or wrapped
- [ ] `LC_ALL=C` (or `C.UTF-8`) set explicitly
- [ ] Tested on at least: Linux GNU, macOS BSD, Alpine BusyBox
