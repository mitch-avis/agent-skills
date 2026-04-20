# Security

Hardening guidance for shell scripts that handle untrusted input, secrets, or run with elevated
privileges. Apply the relevant items to **every** production script.

## Threat Model in One Paragraph

The two dominant threats are **command injection** (an attacker controls part of a string that
becomes a command) and **race conditions / TOCTOU** (file state changes between check and use).
Defenses: never let untrusted data become code, validate at the boundary, use atomic operations, and
run with least privilege.

## Command Injection

### Bash: never `eval` user input

```bash
# DANGER — code injection
eval "$user_command"
bash -c "$user_command"
ssh "$host" "$user_command"        # ssh re-parses the remote string

# SAFE — build an array, expand with "${cmd[@]}"
cmd=(grep "$pattern" "$file")
"${cmd[@]}"

# SAFE — pass args via positional params, never reinterpret as code
process() {
    local pattern="$1" file="$2"
    grep -- "$pattern" "$file"
}
process "$user_pattern" "$user_file"

# Remote: pass the script via stdin, not as a string argument
ssh "$host" 'bash -s' <<'EOF'
    set -e
    echo "Running on $(hostname)"
EOF
```

### PowerShell: never `Invoke-Expression`

```powershell
# DANGER
Invoke-Expression "$cmd $userArg"
iex "$cmd $userArg"

# SAFE — call operator with array of args (no re-parsing)
& $cmd @argArray

# SAFE — Start-Process with -ArgumentList as array
Start-Process -FilePath $cmd -ArgumentList $userArg, $otherArg -Wait
```

### Argument injection — the `--` discipline

Filenames starting with `-` get parsed as options. Always end option lists with `--`:

```bash
rm -- "$file"
mv -- "$src" "$dest"
chown -- "$user" "$path"
grep -- "$pattern" "$file"
```

The same applies in PowerShell when passing args to native commands:

```powershell
# Use the stop-parsing token --% (PS 5.1+) when calling native exes that need it
& git --% log --oneline -- $userPath
```

## Input Validation at the Boundary

Validate **before** any work. Use allow-lists, not deny-lists.

```bash
# Bash — regex allow-list
[[ "$user_id" =~ ^[a-zA-Z0-9_-]{1,32}$ ]] || die "Invalid user_id: $user_id"
[[ "$port"    =~ ^[0-9]+$ ]] && (( port >= 1 && port <= 65535 )) \
    || die "Invalid port: $port"

# Reject path traversal
[[ "$path" == */..* || "$path" == /* ]] && die "Reject absolute or traversal paths"

# Canonicalize and confine to a base directory
real=$(realpath -- "$base/$user_path")
[[ "$real" == "$base"/* ]] || die "Path escapes base: $real"
```

```powershell
# PowerShell — validation attributes do this declaratively
[ValidatePattern('^[a-zA-Z0-9_-]{1,32}$')]
[ValidateRange(1, 65535)]
[ValidateScript({
    $real = Resolve-Path -LiteralPath $_ -ErrorAction Stop
    $real.Path.StartsWith($base, [StringComparison]::OrdinalIgnoreCase)
})]
```

## Secure Temporary Files

```bash
# Bash — always mktemp, always trap-clean
TMPFILE=$(mktemp) || die "mktemp failed"
TMPDIR=$(mktemp -d) || die "mktemp -d failed"
trap 'rm -rf -- "${TMPDIR}" "${TMPFILE}"' EXIT INT TERM

# In a specific dir (e.g., same FS as target for atomic mv)
TMPFILE=$(mktemp -p "$(dirname -- "$target")")

# DANGER — predictable name, race-prone
tmp=/tmp/myscript.$$
echo "..." > "$tmp"             # symlink attack possible
```

```powershell
$tmpFile = [System.IO.Path]::GetTempFileName()
$tmpDir  = Join-Path ([System.IO.Path]::GetTempPath()) ([Guid]::NewGuid())
New-Item -ItemType Directory -Path $tmpDir | Out-Null

try {
    # ... work ...
}
finally {
    Remove-Item -LiteralPath $tmpFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $tmpDir  -Recurse -Force -ErrorAction SilentlyContinue
}
```

## Atomic File Writes

Avoid partial writes that leave consumers reading half-updated content:

```bash
tmp=$(mktemp -p "$(dirname -- "$target")")
trap 'rm -f -- "$tmp"' EXIT
generate_content > "$tmp"
chmod 0644 -- "$tmp"
mv -- "$tmp" "$target"          # atomic rename on the same filesystem
```

## Secrets Handling

- **Never** pass secrets on the command line — they appear in `ps aux`, shell history, and process
  environment of children. Use stdin or a secret file with restricted perms.
- **Never** log secrets, even in DEBUG. Maintain an explicit allow-list of values to log.
- **Never** commit secrets, including in test fixtures. Use `git-secrets`, `gitleaks`, or
  `pre-commit` hooks.

```bash
# Read secret from env var (set by orchestrator); fail closed
: "${API_TOKEN:?API_TOKEN must be set in the environment}"

# Or from a 0600 file
[[ -r "$secret_file" ]] || die "secret unreadable: $secret_file"
[[ "$(stat -c '%a' "$secret_file")" == "600" ]] || die "secret has loose perms"
api_token=$(<"$secret_file")

# When invoking curl, prefer a netrc/header file over -u user:pass
curl -sSf -H "@$header_file" "$url"
```

PowerShell:

```powershell
# Use SecretManagement + a vault
Install-Module Microsoft.PowerShell.SecretManagement -Scope CurrentUser
Install-Module Microsoft.PowerShell.SecretStore     -Scope CurrentUser
Register-SecretVault -Name LocalStore -ModuleName Microsoft.PowerShell.SecretStore -DefaultVault
Set-Secret -Name 'ApiToken' -Secret (Read-Host -AsSecureString)
$token = Get-Secret -Name 'ApiToken' -AsPlainText   # use sparingly

# Never put secrets in script string fields
[SecureString]$pwd = Read-Host -AsSecureString
$cred = [PSCredential]::new($user, $pwd)
```

## Least Privilege

- Drop privileges as early as possible. If you only need to read `/etc`, don't run as root.
- Refuse to run as root unless required:

  ```bash
  if [[ "$(id -u)" -eq 0 && "${ALLOW_ROOT:-0}" != "1" ]]; then
      die "Refusing to run as root (set ALLOW_ROOT=1 to override)"
  fi
  ```

- Don't `sudo` from inside a script. Make the user run the script with `sudo` if needed.
- Use `chmod 0700` for scripts containing sensitive logic; `0755` for general use.

## SUID/SGID on Shell Scripts

The Linux kernel **ignores** the SUID/SGID bit on `#!`-interpreted scripts (CVE history is brutal).
Don't rely on it. If you need privileged operations:

- Write a small `setuid` C wrapper, or
- Configure `sudo` with a tightly scoped `NOPASSWD` rule for one specific command, or
- Use Linux capabilities (`setcap cap_net_bind_service=+ep`).

## File Path Safety

```bash
# Refuse empty path expansion (catastrophic with rm)
rm -rf -- "${dir:?dir must be set}"/*

# Use absolute paths for system commands when running from cron / setuid contexts
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH

# Or hardcode for ultra-paranoid scripts
readonly RM=/bin/rm
"${RM}" -rf -- "$dir"
```

## Curl-Bash Anti-Pattern

The familiar `curl ... | bash` is the worst-case install pattern. If you ship one:

- Serve over HTTPS with a fixed cert pin (or document `--tlsv1.3 --max-time 30`).
- Always include a checksum (SHA-256) and signing in your install docs.
- Make the script idempotent and inspectable. Never auto-execute on download.
- Prefer signed packages (apt/yum/brew) for production.

## Logging That Doesn't Leak

```bash
# Redact known-sensitive patterns
log_request() {
    local body="$1"
    body=${body//$API_TOKEN/[REDACTED]}      # bash 4+ pattern replacement
    body=$(printf '%s' "$body" | sed -E 's/("password":")[^"]+/\1[REDACTED]/g')
    log_debug "request body: $body"
}
```

## Pre-Flight Checklist

Run through this before shipping a security-relevant script:

- [ ] No `eval`, `Invoke-Expression`, `bash -c "$var"` with untrusted input
- [ ] Every external command call quotes its variables
- [ ] Inputs validated against an allow-list regex/range
- [ ] Paths confined to expected base; canonicalized with `realpath` / `Resolve-Path`
- [ ] `--` used to terminate options before user-supplied paths
- [ ] Secrets never on CLI, never in logs, never in git
- [ ] Temp files via `mktemp` / `GetTempFileName`, cleaned up via trap / finally
- [ ] Atomic file writes via temp + `mv`
- [ ] Refuses or warns when running as root unless explicitly required
- [ ] No SUID/SGID on the script; use sudoers rule or wrapper instead
- [ ] PATH is set explicitly for cron / setuid / privileged contexts
- [ ] ShellCheck (or PSScriptAnalyzer) passes with no warnings
- [ ] Unit/integration tests cover at least one malicious-input case
