# Operational Recipes

Ready-to-adapt snippets for common production patterns. Copy, paste, customize.

## Structured Logging

### Bash — leveled logger to stderr

```bash
LOG_LEVEL="${LOG_LEVEL:-INFO}"      # DEBUG | INFO | WARN | ERROR
declare -rA LOG_LEVELS=([DEBUG]=10 [INFO]=20 [WARN]=30 [ERROR]=40)

_log() {
    local level="$1"; shift
    (( ${LOG_LEVELS[$level]:-0} >= ${LOG_LEVELS[$LOG_LEVEL]:-20} )) || return 0
    printf '[%(%Y-%m-%dT%H:%M:%S%z)T] [%s] [%s] %s\n' \
        -1 "$level" "${SCRIPT_NAME:-shell}" "$*" >&2
}
log_debug() { _log DEBUG "$@"; }
log_info()  { _log INFO  "$@"; }
log_warn()  { _log WARN  "$@"; }
log_error() { _log ERROR "$@"; }
die()       { log_error "$@"; exit 1; }

# Usage: LOG_LEVEL=DEBUG ./script.sh
```

### Bash — JSON log lines (for ingest into Loki/Splunk/CloudWatch)

```bash
log_json() {
    local level="$1"; shift
    local msg="$*"
    msg=${msg//\\/\\\\}; msg=${msg//\"/\\\"}    # crude JSON escape
    printf '{"ts":"%(%Y-%m-%dT%H:%M:%S%z)T","level":"%s","script":"%s","msg":"%s"}\n' \
        -1 "$level" "${SCRIPT_NAME}" "$msg" >&2
}
```

### PowerShell — structured logging with PSObjects

```powershell
function Write-StructuredLog {
    [CmdletBinding()] param(
        [ValidateSet('DEBUG','INFO','WARN','ERROR')] [string]$Level = 'INFO',
        [Parameter(Mandatory)] [string]$Message,
        [hashtable]$Data
    )
    $entry = [pscustomobject]@{
        ts      = (Get-Date).ToString('o')
        level   = $Level
        script  = (Split-Path -Leaf $PSCommandPath)
        message = $Message
        data    = $Data
    }
    $json = $entry | ConvertTo-Json -Compress -Depth 10
    [Console]::Error.WriteLine($json)
}

Write-StructuredLog -Level INFO -Message 'Started' -Data @{ pid = $PID; user = $env:USER }
```

## Retry with Exponential Backoff

### Bash

```bash
# Usage: retry <max_attempts> <initial_delay_seconds> <command...>
retry() {
    local -ri max=$1
    local -i  delay=$2
    shift 2
    local -i attempt=1

    until "$@"; do
        local -ri rc=$?
        if (( attempt >= max )); then
            log_error "Failed after $attempt attempts (last rc=$rc): $*"
            return "$rc"
        fi
        log_warn "Attempt $attempt failed (rc=$rc); retrying in ${delay}s"
        sleep "$delay"
        (( attempt++, delay *= 2 ))
    done
}

retry 5 1 curl -fsS https://api.example.com/health
```

### PowerShell

```powershell
function Invoke-WithRetry {
    [CmdletBinding()] param(
        [Parameter(Mandatory)] [scriptblock]$ScriptBlock,
        [int]$MaxAttempts = 5,
        [int]$InitialDelaySeconds = 1,
        [type[]]$RetryOn = @([System.Net.WebException], [System.IO.IOException])
    )
    $attempt = 1; $delay = $InitialDelaySeconds
    while ($true) {
        try { return & $ScriptBlock }
        catch {
            $shouldRetry = $RetryOn.Count -eq 0 -or
                ($RetryOn | Where-Object { $_.IsAssignableFrom($_.Exception.GetType()) })
            if (-not $shouldRetry -or $attempt -ge $MaxAttempts) { throw }
            Write-Warning "Attempt $attempt failed: $($_.Exception.Message); retry in $delay s"
            Start-Sleep -Seconds $delay
            $attempt++; $delay *= 2
        }
    }
}

Invoke-WithRetry -ScriptBlock { Invoke-RestMethod 'https://api.example.com/health' }
```

## Dependency Checks

### Bash

```bash
require_cmd() {
    local missing=()
    for cmd in "$@"; do
        command -v -- "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
    done
    (( ${#missing[@]} == 0 )) || die "Missing commands: ${missing[*]}"
}

require_cmd jq curl git

# Version check
require_bash_version() {
    local -ri want_major=$1 want_minor=${2:-0}
    if (( BASH_VERSINFO[0] < want_major )) ||
       { (( BASH_VERSINFO[0] == want_major )) && (( BASH_VERSINFO[1] < want_minor )); }; then
        die "Bash >= ${want_major}.${want_minor} required (have ${BASH_VERSION})"
    fi
}
require_bash_version 4 4
```

### PowerShell

```powershell
function Test-Dependency {
    param([string[]]$Command, [string[]]$Module)
    $missing = @()
    foreach ($c in $Command) {
        if (-not (Get-Command $c -ErrorAction SilentlyContinue)) { $missing += "command:$c" }
    }
    foreach ($m in $Module) {
        if (-not (Get-Module -ListAvailable $m)) { $missing += "module:$m" }
    }
    if ($missing) { throw "Missing: $($missing -join ', ')" }
}

Test-Dependency -Command 'git', 'docker' -Module 'Pester'
```

## Lock Files (single-instance scripts)

```bash
# Using flock (Linux). Aborts immediately if already running.
exec 9>"/var/lock/${SCRIPT_NAME}.lock"
flock -n 9 || die "Already running (lock held)"

# On exit, lock is released automatically when fd 9 closes.
```

```powershell
# Cross-platform single-instance via Mutex
$mutex = New-Object System.Threading.Mutex($false, "Global\$($SCRIPT_NAME)")
if (-not $mutex.WaitOne(0)) { throw 'Already running' }
try { Main }
finally { $mutex.ReleaseMutex(); $mutex.Dispose() }
```

## Atomic Configuration Update

```bash
update_config() {
    local -r target="$1"
    local tmp
    tmp=$(mktemp -p "$(dirname -- "$target")")
    trap 'rm -f -- "$tmp"' RETURN

    # Build new content (read existing if needed)
    {
        cat -- "$target" 2>/dev/null
        printf 'new_setting=%s\n' "$2"
    } > "$tmp"

    chmod --reference="$target" -- "$tmp" 2>/dev/null \
        || chmod 0644 -- "$tmp"
    mv -- "$tmp" "$target"
    trap - RETURN
}
```

## Backup with Rotation

```bash
backup_dir() {
    local -r src="$1" dst_base="$2" keep="${3:-7}"
    local -r ts="$(date +%Y%m%d_%H%M%S)"
    local -r archive="${dst_base}/$(basename -- "$src")_${ts}.tar.gz"

    mkdir -p -- "$dst_base"
    tar -czf "$archive" -C "$(dirname -- "$src")" "$(basename -- "$src")"
    log_info "Backup created: $archive"

    # Rotate: keep N most recent
    find "$dst_base" -maxdepth 1 -name "$(basename -- "$src")_*.tar.gz" -type f \
        -printf '%T@ %p\n' \
        | sort -nr \
        | tail -n +$((keep + 1)) \
        | cut -d' ' -f2- \
        | xargs -r rm -f --
}

backup_dir /etc/myapp /var/backups/myapp 14
```

## Disk / CPU / Memory Monitoring

```bash
# Alert if any filesystem > 90% full
check_disk() {
    df -P | awk 'NR>1 && $5+0 > 90 { print $6 " is " $5 " full" }' | while read -r alert; do
        log_warn "$alert"
    done
}

# Alert if 1-min load average > N
check_load() {
    local -r threshold="$1"
    local load
    load=$(awk '{print $1}' /proc/loadavg)
    awk -v l="$load" -v t="$threshold" 'BEGIN { exit (l > t) ? 0 : 1 }' \
        && log_warn "Load $load exceeds $threshold"
}

# Top memory consumers
top_memory() {
    ps -eo pid,ppid,user,%mem,%cpu,comm --sort=-%mem | head -n "${1:-10}"
}
```

## Run with Timeout

```bash
# coreutils 'timeout' — kills after duration
timeout --kill-after=5s 30s long_command || die "long_command timed out"

# Pure bash for short polling
wait_for() {
    local -r check_cmd="$1" timeout="${2:-30}"
    local elapsed=0
    until eval "$check_cmd" >/dev/null 2>&1; do
        (( elapsed += 1 ))
        (( elapsed >= timeout )) && return 1
        sleep 1
    done
}

wait_for 'curl -fsS http://localhost:8080/ready' 60 \
    || die "Service did not become ready"
```

## Parallel Execution

```bash
# GNU parallel (if available — most flexible)
printf '%s\n' "${urls[@]}" | parallel -j 4 'curl -fsSO {}'

# xargs portable
printf '%s\0' "${urls[@]}" | xargs -0 -P 4 -n 1 curl -fsSO

# Background pids with bounded concurrency
declare -a pids=()
max_jobs=4
for url in "${urls[@]}"; do
    while (( ${#pids[@]} >= max_jobs )); do
        for i in "${!pids[@]}"; do
            kill -0 "${pids[$i]}" 2>/dev/null || unset 'pids[$i]'
        done
        pids=("${pids[@]}")
        sleep 0.1
    done
    curl -fsSO "$url" &
    pids+=($!)
done
wait
```

```powershell
# PowerShell 7+: native parallel
$urls | ForEach-Object -Parallel { Invoke-WebRequest $_ -OutFile (Split-Path -Leaf $_) } `
    -ThrottleLimit 4
```

## User Confirmation / Prompts

```bash
confirm() {
    local prompt="${1:-Continue?} [y/N] "
    local reply
    read -r -p "$prompt" reply
    [[ "$reply" =~ ^[Yy]([Ee][Ss])?$ ]]
}

confirm "Delete $target?" || die "Aborted"
```

```powershell
# Use SupportsShouldProcess instead — gives -WhatIf and -Confirm for free
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param([string]$Target)

if ($PSCmdlet.ShouldProcess($Target, 'Delete')) {
    Remove-Item -LiteralPath $Target -Recurse -Force
}
```

## Cron / systemd Timer Hygiene

```bash
# A cron-friendly script:
#  - sets PATH explicitly (cron's PATH is minimal)
#  - cd's somewhere predictable
#  - logs everything (cron only mails stderr)
#  - uses flock to prevent overlap
#
# crontab line:
# */5 * * * * /usr/local/bin/myjob.sh >> /var/log/myjob.log 2>&1

#!/usr/bin/env bash
set -Eeuo pipefail
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH
cd /  # or to a known working directory

exec 9>/var/lock/myjob.lock
flock -n 9 || { echo "$(date): already running, skipping"; exit 0; }

# ... actual work ...
```

For systemd timers, prefer `Type=oneshot` units over cron — easier to manage, log via journald, and
you get retries via `OnFailure=`.

## Sourcing Common Library

When several scripts share helpers, factor them into a library:

```bash
# lib/common.sh
log_info()  { printf '[INFO]  %s\n' "$*" >&2; }
log_error() { printf '[ERROR] %s\n' "$*" >&2; }
die()       { log_error "$@"; exit 1; }

# bin/myscript.sh
#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"

log_info "Hello"
```
