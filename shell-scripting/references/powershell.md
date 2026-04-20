# PowerShell Reference

Comprehensive PowerShell scripting patterns for both Windows PowerShell 5.1 and PowerShell 7+ on
Linux/macOS/Windows. Default to PowerShell 7+ unless legacy 5.1 is required.

## Table of Contents

- [PowerShell Reference](#powershell-reference)
  - [Table of Contents](#table-of-contents)
  - [Strict Mode and Mandatory Header](#strict-mode-and-mandatory-header)
  - [Naming and Style](#naming-and-style)
  - [Parameters and CmdletBinding](#parameters-and-cmdletbinding)
  - [Pipeline Functions](#pipeline-functions)
  - [Variables and Types](#variables-and-types)
  - [Control Flow](#control-flow)
  - [Operators](#operators)
  - [Pipeline and Filtering](#pipeline-and-filtering)
  - [Error Handling](#error-handling)
  - [Cross-Platform Patterns](#cross-platform-patterns)
  - [File and Path Operations](#file-and-path-operations)
  - [Module Management (PSResourceGet)](#module-management-psresourceget)
  - [Common Pitfalls](#common-pitfalls)
  - [Security Hardening](#security-hardening)

## Strict Mode and Mandatory Header

```powershell
#Requires -Version 7.0
#Requires -Modules @{ ModuleName = 'Az.Accounts'; ModuleVersion = '2.0.0' }

[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'Medium')]
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$Path,

    [ValidateRange(1, 100)]
    [int]$MaxItems = 10,

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSDefaultParameterValues['*:ErrorAction']            = 'Stop'
$PSDefaultParameterValues['Out-File:Encoding']        = 'utf8'
$PSDefaultParameterValues['Set-Content:Encoding']     = 'utf8'
$PSDefaultParameterValues['ConvertTo-Json:Depth']     = 10
```

| Setting | Why |
| --- | --- |
| `Set-StrictMode -Version Latest` | Errors on uninitialized vars, missing properties, bad function calls |
| `$ErrorActionPreference = 'Stop'` | Non-terminating errors become terminating (catchable) |
| `$PSDefaultParameterValues` (`*:ErrorAction = 'Stop'`) | Forces every cmdlet, even ones that ignore the global preference |
| `ConvertTo-Json:Depth = 10` | Default depth of 2 silently truncates nested objects |
| `*:Encoding = 'utf8'` | Cross-platform consistent file output (Windows defaults to UTF-16LE in 5.1) |

## Naming and Style

- Functions: **`Verb-Noun`**, singular noun, approved verb. Run `Get-Verb` to list.
- Parameters and properties: **PascalCase** (`$FilePath`, not `$filepath`).
- Local variables: **camelCase** (`$lineCount`).
- Constants: **`Set-Variable -Option Constant`** or `[const]`-style ALL_CAPS.
- Never use aliases in scripts: `Get-ChildItem` not `ls`/`gci`/`dir`; `Where-Object` not `?`;
  `ForEach-Object` not `%`.
- One statement per line; use backtick line continuation sparingly — prefer splatting:

```powershell
# Splatting: preferred over backtick continuation
$params = @{
    Path        = 'C:\logs'
    Recurse     = $true
    Filter      = '*.log'
    ErrorAction = 'Stop'
}
$logs = Get-ChildItem @params
```

## Parameters and CmdletBinding

```powershell
function Invoke-DeployApp {
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High',
                   DefaultParameterSetName = 'ByName')]
    param(
        [Parameter(Mandatory, ParameterSetName = 'ByName', Position = 0)]
        [ValidateNotNullOrEmpty()]
        [string]$Name,

        [Parameter(Mandatory, ParameterSetName = 'ById')]
        [ValidatePattern('^[0-9a-f]{8}$')]
        [string]$Id,

        [ValidateSet('Dev', 'Staging', 'Prod')]
        [string]$Environment = 'Dev',

        [ValidateRange(1, 10)]
        [int]$Replicas = 1,

        [Parameter(ValueFromPipeline, ValueFromPipelineByPropertyName)]
        [string[]]$Tag
    )

    process {
        if (-not $PSCmdlet.ShouldProcess("$Name@$Environment", 'Deploy')) { return }
        # do work
    }
}
```

Validation attributes do input checking before your code runs:

| Attribute | Use |
| --- | --- |
| `[ValidateNotNullOrEmpty()]` | Reject `$null` and `''` |
| `[ValidateSet('a','b','c')]` | Restrict to enum values (also gives tab completion) |
| `[ValidateRange(1,100)]` | Numeric range |
| `[ValidatePattern('^\d+$')]` | Regex |
| `[ValidateScript({ Test-Path $_ })]` | Custom predicate |
| `[ValidateCount(1,5)]` | Array length bounds |

## Pipeline Functions

Use `begin`/`process`/`end` for true pipeline support:

```powershell
function Format-FileInfo {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory, ValueFromPipeline)]
        [System.IO.FileInfo]$File
    )
    begin   { $count = 0 }
    process {
        $count++
        [pscustomobject]@{
            Name   = $File.Name
            SizeKB = [math]::Round($File.Length / 1KB, 2)
            Age    = (Get-Date) - $File.LastWriteTime
        }
    }
    end     { Write-Verbose "Processed $count files" }
}

Get-ChildItem *.log | Format-FileInfo | Sort-Object SizeKB -Descending
```

## Variables and Types

```powershell
# Strong typing (recommended for parameters and return-relevant locals)
[string]$name      = 'alice'
[int]$age          = 30
[datetime]$start   = Get-Date
[hashtable]$opts   = @{ Verbose = $true; Force = $false }
[string[]]$tags    = 'web', 'prod'

# Automatic variables
$PSScriptRoot      # directory containing the script
$PSCommandPath     # full path of the script
$MyInvocation      # info about how this was called
$args              # leftover positional args (avoid; use param() instead)
$_  / $PSItem      # current pipeline object
$IsWindows / $IsLinux / $IsMacOS   # PS 7+
$PSVersionTable    # PS version, OS, edition

# Force array (avoid the "single item != array" trap)
$results = @( Get-Thing -Filter 'x' )    # always an array, even with 0 or 1 item
```

## Control Flow

```powershell
# if/elseif/else
if ($x -gt 10) { ... } elseif ($x -gt 0) { ... } else { ... }

# switch (regex, wildcard, file)
switch -Regex ($input) {
    '^\d+$'   { 'number' }
    '^[a-z]+' { 'word'   }
    default   { 'other'  }
}

switch -File 'config.txt' {
    'enabled=true' { $enabled = $true }
}

# loops
foreach ($item in $collection) { ... }     # consumes whole collection first
$collection | ForEach-Object  { ... }      # streams (lower memory)
for ($i = 0; $i -lt 10; $i++) { ... }
while ($condition) { ... }
do { ... } while ($condition)

# parallel (PS 7+)
1..100 | ForEach-Object -Parallel { Invoke-Thing $_ } -ThrottleLimit 8
```

## Operators

| Comparison | Logic | Other |
| --- | --- | --- |
| `-eq` `-ne` `-gt` `-lt` `-ge` `-le` | `-and` `-or` `-not` (or `!`) | `-match` (regex) |
| `-like` (wildcard) | `-xor` | `-replace` (regex replace) |
| `-contains` `-in` | `-band` `-bor` (bitwise) | `-split` `-join` |
| `-is` `-isnot` (type) | | `-as` (type cast, returns `$null` on failure) |

Case-sensitive variants exist as `-ceq`, `-cmatch`, etc. Default operators are case-**insensitive**.

PowerShell 7+ adds:

```powershell
$value  = $condition ? 'yes' : 'no'        # ternary
$result = $maybeNull ?? 'default'           # null-coalescing
$obj   ??= (Get-Default)                    # null-coalescing assignment
$a?.B?.C                                    # null-conditional member access
```

## Pipeline and Filtering

```powershell
Get-Process |
    Where-Object   { $_.WorkingSet64 -gt 100MB } |
    Sort-Object    -Property WorkingSet64 -Descending |
    Select-Object  -First 10 -Property Name, Id, @{N='WS_MB'; E={ [int]($_.WorkingSet64 / 1MB) }}

# Group / Measure
Get-ChildItem | Group-Object Extension | Sort-Object Count -Descending
Get-ChildItem | Measure-Object -Property Length -Sum -Average

# Convert objects to/from formats
Get-Process | ConvertTo-Json   -Depth 5
Get-Process | ConvertTo-Csv    -NoTypeInformation
Get-Content config.json | ConvertFrom-Json
Import-Csv users.csv
Import-PowerShellDataFile config.psd1
```

## Error Handling

```powershell
try {
    $content = Get-Content -LiteralPath $Path -Raw -ErrorAction Stop
}
catch [System.IO.FileNotFoundException] {
    Write-Error "File not found: $Path"
    exit 1
}
catch [System.UnauthorizedAccessException] {
    Write-Error "Permission denied: $Path"
    exit 13
}
catch {
    Write-Error "Unexpected: $($_.Exception.Message)"
    Write-Verbose $_.ScriptStackTrace
    exit 1
}
finally {
    if ($tempFile -and (Test-Path $tempFile)) {
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
    }
}

# Throw a terminating error
throw [System.ArgumentException]::new("bad value: $value", 'value')

# Non-terminating error (continues script)
$PSCmdlet.WriteError(
    [System.Management.Automation.ErrorRecord]::new(
        [Exception]::new('msg'), 'MyId',
        [System.Management.Automation.ErrorCategory]::InvalidData, $obj))

# trap (script-wide handler — use sparingly; try/catch is preferred)
trap { Write-Error "TRAP: $_"; exit 1 }
```

Notes:

- Many cmdlets emit **non-terminating** errors that `try/catch` won't see unless you set
  `-ErrorAction Stop` (or use `$ErrorActionPreference = 'Stop'` globally).
- Don't `return` inside `try` — assign to a variable and return after the `try/catch/finally`.
- `$Error[0]` holds the most recent error; `$Error.Clear()` resets the collection.

## Cross-Platform Patterns

```powershell
# Path construction
$config = Join-Path $PSScriptRoot 'config.json'
$temp   = [System.IO.Path]::GetTempPath()
$home   = [Environment]::GetFolderPath('UserProfile')

# OS branching (PS 7+)
if     ($IsWindows) { $sep = ';' }
elseif ($IsLinux)   { $sep = ':' }
elseif ($IsMacOS)   { $sep = ':' }

# Environment variables — names are case-sensitive on Linux/macOS
$path = $env:PATH       # works everywhere
$user = [Environment]::UserName  # cross-platform user name

# File system case sensitivity
Get-ChildItem -LiteralPath $path   # avoid wildcards if filename may have brackets
```

## File and Path Operations

```powershell
# Read file
$raw   = Get-Content -LiteralPath $path -Raw            # one string
$lines = Get-Content -LiteralPath $path                 # array of lines

# Write file (atomic-ish — write to temp, move)
$tmp = [System.IO.Path]::GetTempFileName()
try {
    $content | Set-Content -LiteralPath $tmp -Encoding utf8
    Move-Item -LiteralPath $tmp -Destination $target -Force
}
finally {
    if (Test-Path $tmp) { Remove-Item $tmp -Force }
}

# Test path strictly
if (Test-Path -LiteralPath $path -PathType Leaf) { ... }   # file
if (Test-Path -LiteralPath $path -PathType Container) { ... } # directory

# Walk directory tree
Get-ChildItem -LiteralPath $root -Recurse -File -Filter '*.log' |
    ForEach-Object { ... }
```

Always prefer `-LiteralPath` over `-Path` when the path may contain wildcard characters (`[`, `]`,
`*`, `?`).

## Module Management (PSResourceGet)

PSResourceGet is the modern replacement for PowerShellGet (PS 7.4+ ships with it).

```powershell
# Find / install / update
Find-PSResource    -Name 'Az.*'
Install-PSResource -Name Az -Scope CurrentUser -TrustRepository
Update-PSResource  -Name Az
Get-InstalledPSResource

# Save offline, install later
Save-PSResource    -Name Az -Path D:\OfflineModules
Install-PSResource -Name Az -Path D:\OfflineModules

# In a script: declare hard requirements
#Requires -Modules @{ ModuleName = 'Pester'; ModuleVersion = '5.5.0' }
```

Legacy `Install-Module` / `Find-Module` still work and now route through PSResourceGet.

## Common Pitfalls

| Wrong | Right | Why |
| --- | --- | --- |
| `if (Test-Path a -or Test-Path b)` | `if ((Test-Path a) -or (Test-Path b))` | Logical operators bind loosely; cmdlet calls need parens |
| `ConvertTo-Json $obj` | `ConvertTo-Json $obj -Depth 10` | Default depth is 2 (silent truncation) |
| `$arr.Count -gt 0` | `($null -ne $arr) -and ($arr.Count -gt 0)` | StrictMode errors on `$null.Count` |
| `"X = $($a.b.c.d)"` | `$v = $a.b.c.d; "X = $v"` | Deep `$()` interpolation is fragile |
| `Write-Host` for data | `Write-Output` (or just emit the object) | `Write-Host` writes to host, breaks pipelines |
| `-Path $userInput` (untrusted) | `-LiteralPath $userInput` | Wildcard chars cause unintended matches |
| `$result = func; if ($result)` (when `func` returns multiple) | `[array]$result = @(func)` | PS unwraps single-item arrays |
| Returning from inside `try { }` | Assign to var, return after `finally` | Skips `finally` cleanup in some edge cases |
| Using emoji/Unicode in script output | Use ASCII (`[OK]`, `[ERR]`, `[WARN]`) | Console encoding varies; CI logs corrupt |
| `Get-Content $path \| ConvertFrom-Json` | `Get-Content $path -Raw \| ConvertFrom-Json` | Without `-Raw` you pass an array of lines |

## Security Hardening

- **Execution policy** is not a security boundary. It's a speed bump. Real protection comes from
  code signing + WDAC/AppLocker.
- **Sign production scripts**:

  ```powershell
  $cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | Select-Object -First 1
  Set-AuthenticodeSignature -FilePath .\script.ps1 -Certificate $cert -TimestampServer http://timestamp.digicert.com
  ```

- **Never** interpolate untrusted input into `Invoke-Expression` (`iex`). Use `&` with an array of
  arguments instead:

  ```powershell
  & $exe @argArray            # safe — args are not re-parsed
  Invoke-Expression "$exe $userInput"   # CODE INJECTION
  ```

- **Secrets**: use `Microsoft.PowerShell.SecretManagement` + a vault (KeePass, Azure Key Vault,
  CredMan), never hardcode or commit. For ad-hoc, `Get-Credential` prompts and returns a
  `PSCredential` with the password as `[SecureString]`.
- **Script Block Logging** + **Module Logging** + **Transcription**: enable via Group Policy or
  registry for production hosts (events 4103, 4104 in `Microsoft-Windows-PowerShell/Operational`).
- **Constrained Language Mode** + **JEA** (Just Enough Administration) for delegated admin — see
  Microsoft docs for full setup.
- **`-WhatIf` and `-Confirm`**: implement via `[CmdletBinding(SupportsShouldProcess)]` on any
  function that mutates state, then guard with `if ($PSCmdlet.ShouldProcess(...))`.
