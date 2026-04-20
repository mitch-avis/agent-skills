# Production PowerShell Script Template

Copy as the starting point for any non-trivial `.ps1`. Replace placeholders, then delete this
note.

```powershell
<#
.SYNOPSIS
    One-line description of what this script does.

.DESCRIPTION
    Longer description with context, expected inputs, and side effects.

.PARAMETER Path
    Input file or directory to process.

.PARAMETER OutputDir
    Where to write results. Defaults to ./output.

.PARAMETER Force
    Overwrite existing output without prompting.

.EXAMPLE
    PS> ./Invoke-Example.ps1 -Path .\input.csv

.EXAMPLE
    PS> ./Invoke-Example.ps1 -Path .\data -OutputDir D:\out -Verbose -WhatIf

.NOTES
    Author : you
    Version: 1.0.0
#>

#Requires -Version 7.0

[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'Medium')]
param(
    [Parameter(Mandatory, ValueFromPipeline, ValueFromPipelineByPropertyName)]
    [ValidateNotNullOrEmpty()]
    [string[]]$Path,

    [ValidateScript({ Test-Path -LiteralPath (Split-Path $_ -Parent) -PathType Container })]
    [string]$OutputDir = (Join-Path (Get-Location) 'output'),

    [switch]$Force
)

begin {
    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'
    $PSDefaultParameterValues['*:ErrorAction']        = 'Stop'
    $PSDefaultParameterValues['Out-File:Encoding']    = 'utf8'
    $PSDefaultParameterValues['Set-Content:Encoding'] = 'utf8'
    $PSDefaultParameterValues['ConvertTo-Json:Depth'] = 10

    # ---------- Constants ----------
    Set-Variable -Name SCRIPT_NAME    -Value (Split-Path -Leaf $PSCommandPath) -Option Constant
    Set-Variable -Name SCRIPT_VERSION -Value '1.0.0' -Option Constant

    # ---------- Logging ----------
    function Write-Log {
        [CmdletBinding()] param(
            [ValidateSet('INFO', 'WARN', 'ERROR', 'DEBUG')] [string]$Level,
            [Parameter(ValueFromRemainingArguments)] [string[]]$Message
        )
        $ts   = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz')
        $line = "[$ts] [$Level] $($Message -join ' ')"
        switch ($Level) {
            'ERROR' { [Console]::Error.WriteLine($line) }
            'WARN'  { [Console]::Error.WriteLine($line) }
            'DEBUG' { if ($VerbosePreference -ne 'SilentlyContinue') { [Console]::Error.WriteLine($line) } }
            default { [Console]::Error.WriteLine($line) }
        }
    }
    function Write-Info  { Write-Log -Level INFO  @args }
    function Write-Warn2 { Write-Log -Level WARN  @args }
    function Write-Err2  { Write-Log -Level ERROR @args }
    function Write-Dbg   { Write-Log -Level DEBUG @args }

    # ---------- Dependencies ----------
    function Test-Dependency {
        param([string[]]$Command, [string[]]$Module)
        $missing = @()
        foreach ($c in $Command) {
            if (-not (Get-Command $c -ErrorAction SilentlyContinue)) { $missing += "command:$c" }
        }
        foreach ($m in $Module) {
            if (-not (Get-Module -ListAvailable -Name $m)) { $missing += "module:$m" }
        }
        if ($missing.Count) { throw "Missing dependencies: $($missing -join ', ')" }
    }

    # ---------- Setup ----------
    Write-Info "Starting $SCRIPT_NAME v$SCRIPT_VERSION on $($PSVersionTable.OS)"
    Test-Dependency -Command 'git'          # adjust per actual deps
    if (-not (Test-Path -LiteralPath $OutputDir)) {
        if ($PSCmdlet.ShouldProcess($OutputDir, 'Create directory')) {
            New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
        }
    }

    $script:processed = 0
    $script:failed    = 0
}

process {
    foreach ($p in $Path) {
        if (-not (Test-Path -LiteralPath $p)) {
            Write-Warn2 "Skipping missing path: $p"
            $script:failed++
            continue
        }

        try {
            $dest = Join-Path $OutputDir (Split-Path -Leaf $p)
            if ((Test-Path -LiteralPath $dest) -and -not $Force) {
                Write-Warn2 "Exists (use -Force to overwrite): $dest"
                continue
            }

            if ($PSCmdlet.ShouldProcess($p, "Process to $dest")) {
                Write-Dbg "Copying $p -> $dest"
                Copy-Item -LiteralPath $p -Destination $dest -Force:$Force
                $script:processed++
            }
        }
        catch {
            $script:failed++
            Write-Err2 "Failed on '$p': $($_.Exception.Message)"
            Write-Dbg $_.ScriptStackTrace
        }
    }
}

end {
    Write-Info "Done. Processed=$script:processed Failed=$script:failed"
    if ($script:failed -gt 0) { exit 1 }
}
```

## Notes on the template

- `[CmdletBinding(SupportsShouldProcess)]` enables both `-WhatIf` and `-Confirm` for free —
  use `$PSCmdlet.ShouldProcess(...)` to guard mutating actions.
- All logging goes to stderr (`[Console]::Error`) so the pipeline (stdout) stays clean for
  data output.
- `Test-Dependency` fails fast before any work happens.
- `process { }` runs once per pipeline input, allowing the script to be used as both
  `./script.ps1 -Path a, b, c` and `Get-Item a, b, c | ./script.ps1`.
- For long-running scripts that need cancellation, register an event:

  ```powershell
  $null = Register-EngineEvent PowerShell.Exiting -Action { ... cleanup ... }
  ```

- For module-style code, save as `.psm1` and add a `.psd1` manifest (`New-ModuleManifest`).
