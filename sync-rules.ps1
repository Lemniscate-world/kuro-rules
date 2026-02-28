# sync-rules.ps1 -- Synchronize AI rule files from kuro-rules to all git repos
# Auto-detects git repos in ~/Documents, excludes repos listed in exclude.txt
# Usage: .\sync-rules.ps1 [-Force] [-DryRun] [-Project <name>]
# Master copy: ~/Documents/kuro-rules
param(
    [switch]$Force,
    [switch]$DryRun,
    [string]$Project
)

$ErrorActionPreference = "Stop"
$RULES_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$DOCS_DIR = Split-Path -Parent $RULES_DIR

# Files to sync (relative to kuro-rules)
$RULE_FILES = @(
    "AGENTS.md",
    "AI_GUIDELINES.md",
    "GAD.md",
    ".cursorrules",
    "copilot-instructions.md",
    "acquisition_tracker.md",
    "sync_summary.py"
)

# Read exclude list
$excludeFile = Join-Path $RULES_DIR "exclude.txt"
$excluded = @("kuro-rules")  # always exclude self
if (Test-Path $excludeFile) {
    $excludeLines = Get-Content $excludeFile | Where-Object { $_ -and $_ -notmatch '^\s*#' }
    foreach ($line in $excludeLines) {
        $excluded += $line.Trim()
    }
}

# Auto-detect git repos in Documents
$allDirs = Get-ChildItem -Path $DOCS_DIR -Directory -ErrorAction SilentlyContinue
$projects = @()
foreach ($dir in $allDirs) {
    $gitDir = Join-Path $dir.FullName ".git"
    if (Test-Path $gitDir) {
        if ($excluded -notcontains $dir.Name) {
            $projects += $dir.Name
        }
    }
}

if ($Project) {
    $projects = $projects | Where-Object { $_ -eq $Project }
    if (-not $projects) {
        Write-Host "ERROR: Project '$Project' not found or excluded" -ForegroundColor Red
        exit 1
    }
}

$syncCount = 0
$skipCount = 0
$newProjects = @()
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$logEntries = @()

Write-Host "`n=== kuro-rules sync ===" -ForegroundColor Cyan
Write-Host "Source: $RULES_DIR" -ForegroundColor Gray
Write-Host "Detected: $($projects.Count) git repos" -ForegroundColor Gray
Write-Host "Excluded: $($excluded -join ', ')" -ForegroundColor DarkGray
if ($DryRun) { Write-Host "[DRY RUN]" -ForegroundColor Yellow }
Write-Host ""

foreach ($proj in $projects) {
    $targetDir = Join-Path $DOCS_DIR $proj

    $projSynced = @()
    $isNew = $false

    foreach ($file in $RULE_FILES) {
        $src = Join-Path $RULES_DIR $file
        $dst = Join-Path $targetDir $file

        if (-not (Test-Path $src)) { continue }

        $needsSync = $false
        if (-not (Test-Path $dst)) {
            $needsSync = $true
            $isNew = $true
        } elseif ($Force) {
            $needsSync = $true
        } else {
            $srcHash = (Get-FileHash $src -Algorithm MD5).Hash
            $dstHash = (Get-FileHash $dst -Algorithm MD5).Hash
            if ($srcHash -ne $dstHash) { $needsSync = $true }
        }

        if ($needsSync) {
            if ($DryRun) {
                Write-Host "  WOULD COPY $file -> $proj" -ForegroundColor Cyan
            } else {
                Copy-Item -Path $src -Destination $dst -Force
                Write-Host "  SYNCED $file -> $proj" -ForegroundColor Green
            }
            $projSynced += $file
            $syncCount++
        }
    }

    if ($isNew -and -not $DryRun) {
        $newProjects += $proj
    }

    if ($projSynced.Count -eq 0) {
        Write-Host "  $proj -- up to date" -ForegroundColor DarkGray
    } else {
        $logEntries += "- $proj : $($projSynced -join ', ')"
    }
}

Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "Synced: $syncCount files across $($projects.Count) repos" -ForegroundColor Green
if ($newProjects.Count -gt 0) {
    Write-Host "New repos detected: $($newProjects -join ', ')" -ForegroundColor Magenta
}
Write-Host ""

# Update SYNC_LOG.md
if (-not $DryRun -and $logEntries.Count -gt 0) {
    $logFile = Join-Path $RULES_DIR "SYNC_LOG.md"
    $logHeader = "## $timestamp`n"
    $logBody = ($logEntries -join "`n") + "`n`n"

    if (Test-Path $logFile) {
        $existing = Get-Content $logFile -Raw
        $newContent = "# Sync Log`n`n" + $logHeader + $logBody + ($existing -replace '^# Sync Log\s*\n*', '')
    } else {
        $newContent = "# Sync Log`n`n" + $logHeader + $logBody
    }
    Set-Content -Path $logFile -Value $newContent -Encoding UTF8
    Write-Host "SYNC_LOG.md updated" -ForegroundColor Gray
}
