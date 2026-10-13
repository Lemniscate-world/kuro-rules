# fleet_sync_scheduled.ps1 -- Weekly fleet automation (KuroFleetSync task).
# 1. Regenerate kuro-rules distribution targets (fail closed: stop on drift error)
# 2. Deploy to all tracked projects (sync-rules.ps1, files only, no commits)
# 3. Upgrade git hooks fleet-wide (kuro-owned hooks only, --upgrade is safe)
# 4. Refresh FLEET_VERSIONS.md snapshot
# Logs to logs/fleet-sync.log. Register with Install-KuroScheduledTask.ps1.
$ErrorActionPreference = "Stop"
$RULES_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$LOG = Join-Path $RULES_DIR "logs\fleet-sync.log"
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Log-Line([string]$msg) {
    $line = "[$stamp] $msg"
    Write-Host $line
    Add-Content -LiteralPath $LOG -Value $line
}

try {
    New-Item -ItemType Directory -Path (Split-Path -Parent $LOG) -Force | Out-Null
    Log-Line "START fleet sync"

    & python (Join-Path $RULES_DIR "scripts\generate_targets.py") --apply 2>&1 | ForEach-Object { Log-Line "gen: $_" }
    if ($LASTEXITCODE -ne 0) { throw "generate_targets --apply failed" }

    & (Join-Path $RULES_DIR "sync-rules.ps1") 2>&1 | ForEach-Object { Log-Line "sync: $_" }

    & python (Join-Path $RULES_DIR "scripts\install_hooks.py") --upgrade 2>&1 | ForEach-Object { Log-Line "hooks: $_" }

    & python (Join-Path $RULES_DIR "scripts\inventory_versions.py") --markdown (Join-Path $RULES_DIR "FLEET_VERSIONS.md") 2>&1 | ForEach-Object { Log-Line "inventory: $_" }

    Log-Line "DONE fleet sync"
} catch {
    Log-Line "FAIL: $_"
    exit 1
}
