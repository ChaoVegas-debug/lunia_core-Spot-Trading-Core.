#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Split-Path -Path $MyInvocation.MyCommand.Path -Parent | Split-Path -Parent)
$timestamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$artifactBase = Join-Path $root 'artifacts'
$artifactDir = Join-Path $artifactBase "verify_$timestamp"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

function Write-Log($msg) { Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg" }
function Write-Warn($msg) { Write-Warning $msg }

Write-Log "Root directory: $root"
Write-Log "Artifacts directory: $artifactDir"

# Environment info
$envInfo = @()
foreach ($tool in 'python','pip','docker','docker compose','git','node','npm') {
    try {
        if ($tool -like '* *') {
            $split = $tool.Split(' ')
            if (Get-Command $split[0] -ErrorAction SilentlyContinue) {
                $envInfo += "$tool: $(& $split[0] $split[1] --version 2>$null)"
            } else {
                $envInfo += "$tool: not installed"
            }
        } elseif (Get-Command $tool -ErrorAction SilentlyContinue) {
            $envInfo += "$tool: $(& $tool --version 2>$null)"
        } else {
            $envInfo += "$tool: not installed"
        }
    } catch {
        $envInfo += "$tool: error collecting version"
    }
}
$envInfo | Out-File -FilePath (Join-Path $artifactDir 'environment.txt')

# Lint/test helpers
function Run-Optional($command, $logFile) {
    try {
        Invoke-Expression $command 2>&1 | Tee-Object -FilePath $logFile
        Write-Log "✔ $command"
    } catch {
        Write-Warn "✖ $command ($_ )"
    }
}

if (Get-Command pytest -ErrorAction SilentlyContinue) {
    Run-Optional "pytest -q tests/auth tests/portfolio tests/risk" (Join-Path $artifactDir 'pytest.log')
} else {
    Write-Warn "pytest not available; skipping tests"
}

Write-Log "Verification finished"
"Artifacts stored in $artifactDir" | Out-File -FilePath (Join-Path $artifactDir 'summary.txt')
