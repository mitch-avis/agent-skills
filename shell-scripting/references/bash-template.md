# Production Bash Script Template

Copy this file as a starting point for any non-trivial Bash script. Replace placeholders, then
delete this comment block.

```bash
#!/usr/bin/env bash
#
# example.sh — short description of what this script does
#
# Usage:
#   example.sh [-v] [-d] [-o OUTPUT] [--] INPUT...
#
# Options:
#   -v, --verbose       Enable verbose (DEBUG) logging
#   -d, --dry-run       Print commands without executing
#   -o, --output DIR    Output directory (default: ./output)
#   -h, --help          Show this help and exit
#       --version       Print version and exit
#
# Exit codes:
#   0   success
#   1   general failure
#   2   invalid arguments
#   3   missing dependency
#   130 interrupted (SIGINT)
#

set -Eeuo pipefail
shopt -s inherit_errexit nullglob
IFS=$'\n\t'

# ---------- Constants ----------
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly SCRIPT_NAME="$(basename -- "${BASH_SOURCE[0]}")"
readonly SCRIPT_VERSION="1.0.0"

readonly EXIT_SUCCESS=0
readonly EXIT_FAILURE=1
readonly EXIT_INVALID_ARGS=2
readonly EXIT_MISSING_DEP=3

# ---------- Globals (set by parse_args) ----------
VERBOSE=0
DRY_RUN=0
OUTPUT_DIR="./output"
declare -a INPUTS=()

# ---------- Logging ----------
log()       { printf '[%(%Y-%m-%dT%H:%M:%S%z)T] [%s] %s\n' -1 "$1" "${*:2}" >&2; }
log_info()  { log INFO  "$@"; }
log_warn()  { log WARN  "$@"; }
log_error() { log ERROR "$@"; }
log_debug() { (( VERBOSE )) && log DEBUG "$@" || true; }
die()       { log_error "$@"; exit "${EXIT_FAILURE}"; }

# ---------- Help ----------
usage() {
    sed -n '3,/^$/p' "${BASH_SOURCE[0]}" | sed -E 's/^# ?//'
}

# ---------- Cleanup ----------
TMPDIR=""
cleanup() {
    local -ri exit_code=$?
    [[ -n "${TMPDIR}" && -d "${TMPDIR}" ]] && rm -rf -- "${TMPDIR}"
    exit "${exit_code}"
}
err_handler() {
    log_error "Failed at ${BASH_SOURCE[1]}:${BASH_LINENO[0]} (exit $?)"
}
trap cleanup EXIT
trap err_handler ERR
trap 'log_warn "Interrupted"; exit 130' INT TERM

# ---------- Helpers ----------
require_cmd() {
    local -a missing=()
    for cmd in "$@"; do
        command -v -- "${cmd}" >/dev/null 2>&1 || missing+=("${cmd}")
    done
    if (( ${#missing[@]} )); then
        log_error "Missing required commands: ${missing[*]}"
        exit "${EXIT_MISSING_DEP}"
    fi
}

run() {
    log_debug "+ $*"
    if (( DRY_RUN )); then
        log_info "[dry-run] $*"
        return 0
    fi
    "$@"
}

# ---------- Argument parsing ----------
parse_args() {
    local -a positional=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -v|--verbose)  VERBOSE=1; shift ;;
            -d|--dry-run)  DRY_RUN=1; shift ;;
            -o|--output)   OUTPUT_DIR="$2"; shift 2 ;;
            --output=*)    OUTPUT_DIR="${1#*=}"; shift ;;
            -h|--help)     usage; exit "${EXIT_SUCCESS}" ;;
            --version)     printf '%s %s\n' "${SCRIPT_NAME}" "${SCRIPT_VERSION}"; exit 0 ;;
            --)            shift; positional+=("$@"); break ;;
            -*)            log_error "Unknown option: $1"; usage >&2; exit "${EXIT_INVALID_ARGS}" ;;
            *)             positional+=("$1"); shift ;;
        esac
    done
    INPUTS=("${positional[@]}")

    (( ${#INPUTS[@]} )) || { log_error "At least one INPUT is required"; exit "${EXIT_INVALID_ARGS}"; }
}

# ---------- Validation ----------
validate() {
    require_cmd jq curl    # adjust per actual deps
    mkdir -p -- "${OUTPUT_DIR}"

    for input in "${INPUTS[@]}"; do
        [[ -e "${input}" ]] || die "Input not found: ${input}"
        [[ -r "${input}" ]] || die "Input not readable: ${input}"
    done
}

# ---------- Main work ----------
process_one() {
    local -r input="$1"
    local -r dest="${OUTPUT_DIR}/$(basename -- "${input}")"

    log_info "Processing ${input} -> ${dest}"
    run cp -- "${input}" "${dest}"
}

main() {
    parse_args "$@"
    validate

    TMPDIR="$(mktemp -d)"
    log_debug "Workdir: ${TMPDIR}"

    for input in "${INPUTS[@]}"; do
        process_one "${input}"
    done

    log_info "Done. ${#INPUTS[@]} item(s) written to ${OUTPUT_DIR}"
}

main "$@"
```

## Notes on the template

- The header comment is parsed by `usage()` via `sed`, so keep it formatted consistently.
- `run` centralizes dry-run support — wrap any state-mutating command with it.
- `require_cmd` fails fast if a dependency is missing instead of getting a confusing error 50 lines
  into the script.
- `TMPDIR` is created lazily so a `--help` invocation doesn't pollute `/tmp`.
- The ERR trap reports the location of the failing command before the EXIT trap cleans up.
- For scripts that need lock files, add `flock -n 9 || die "already running"` at the top of
  `main` with `exec 9>"/var/lock/${SCRIPT_NAME}.lock"` above it.
