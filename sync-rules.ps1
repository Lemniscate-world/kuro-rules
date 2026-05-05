# sync-rules.ps1 -- Synchronize Kuro Rules to all git repos
# Syncs AGENTS.md (master) + IDE redirector files
# Usage: .\sync-rules.ps1 [-Force] [-DryRun] [-Project <name>]
param(
    [switch]$Force,
    [switch]$DryRun,
    [string]$Project
)

$ErrorActionPreference = "Stop"
$RULES_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$DOCS_DIR = Split-Path -Parent $RULES_DIR

# AGENTS.md = master rules
# Redirectors = thin files that tell each IDE to read AGENTS.md
$RULE_FILES = @(
    "AGENTS.md",
    ".cursorrules",
    "copilot-instructions.md",
    ".windsurfrules",
    "AI_GUIDELINES.md"
)

$excludeFile = Join-Path $RULES_DIR "exclude.txt"
$excluded = @("kuro-rules")
if (Test-Path $excludeFile) {
    $excludeLines = Get-Content $excludeFile | Where-Object { $_ -and $_ -notmatch "^\s*#" }
    foreach ($line in $excludeLines) { $excluded += $line.Trim() }
}

$allDirs = Get-ChildItem -Path $DOCS_DIR -Directory -ErrorAction SilentlyContinue
$projects = @()
foreach ($dir in $allDirs) {
    if ((Test-Path (Join-Path $dir.FullName ".git")) -and ($excluded -notcontains $dir.Name)) {
        $projects += $dir.Name
    }
}

if ($Project) {
    $projects = $projects | Where-Object { $_ -eq $Project }
    if (-not $projects) { Write-Host "ERROR: '$Project' not found" -ForegroundColor Red; exit 1 }
}

$syncCount = 0
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$logEntries = @()

Write-Host "`n=== kuro-rules sync ===" -ForegroundColor Cyan
Write-Host "Files: $($RULE_FILES -join ', ')" -ForegroundColor Gray
Write-Host "Repos: $($projects.Count)" -ForegroundColor Gray
if ($DryRun) { Write-Host "[DRY RUN]" -ForegroundColor Yellow }
Write-Host ""

foreach ($proj in $projects) {
    $targetDir = Join-Path $DOCS_DIR $proj
    $projSynced = @()

    foreach ($file in $RULE_FILES) {
        $src = Join-Path $RULES_DIR $file
        $dst = Join-Path $targetDir $file
        if (-not (Test-Path $src)) { continue }

        # For copilot-instructions.md, ensure .github/ exists
        if ($file -eq "copilot-instructions.md") {
            $githubDir = Join-Path $targetDir ".github"
            $dstAlt = Join-Path $githubDir "copilot-instructions.md"
            if (Test-Path $githubDir) { $dst = $dstAlt }
        }

        $needsSync = $false
        if (-not (Test-Path $dst)) { $needsSync = $true }
        elseif ($Force) { $needsSync = $true }
        else {
            $srcHash = (Get-FileHash $src -Algorithm MD5).Hash
            $dstHash = (Get-FileHash $dst -Algorithm MD5).Hash
            if ($srcHash -ne $dstHash) { $needsSync = $true }
        }

        if ($needsSync) {
            if (-not $DryRun) { [System.IO.File]::Copy($src, $dst, $true) }
            $projSynced += $file
            $syncCount++
        }
    }

    if ($projSynced.Count -gt 0) {
        Write-Host "  SYNCED -> $proj ($($projSynced -join ', '))" -ForegroundColor Green
        $logEntries += "- $proj : $($projSynced -join ', ')"
    } else {
        Write-Host "  $proj -- up to date" -ForegroundColor DarkGray
    }
}

Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "Synced: $syncCount file operations across repos" -ForegroundColor Green

if (-not $DryRun -and $logEntries.Count -gt 0) {
    $logFile = Join-Path $RULES_DIR "SYNC_LOG.md"
    $logHeader = "## $timestamp`n"
    $logBody = ($logEntries -join "`n") + "`n`n"
    if (Test-Path $logFile) {
        $existing = Get-Content $logFile -Raw
        $newContent = "# Sync Log`n`n" + $logHeader + $logBody + ($existing -replace "^# Sync Log\s*\n*", "")
    } else { $newContent = "# Sync Log`n`n" + $logHeader + $logBody }
    [System.IO.File]::WriteAllText($logFile, $newContent, [System.Text.Encoding]::UTF8)
    Write-Host "SYNC_LOG.md updated" -ForegroundColor Gray
}