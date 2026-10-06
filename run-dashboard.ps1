param(
    [int]$Port = 8767,
    [switch]$NoOpen,
    [switch]$StaticOnly
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DashboardDir = Join-Path $RootDir "dashboard"
$GeneratorPath = Join-Path $DashboardDir "generate_dashboard.py"

if (-not (Test-Path $GeneratorPath)) {
    throw "Dashboard generator not found: $GeneratorPath"
}

Write-Host "[*] Refreshing dashboard snapshot (fallback hors-ligne)..." -ForegroundColor Cyan
python $GeneratorPath

if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Snapshot statique echoue, l'API servira du live." -ForegroundColor Yellow
}

$Url = "http://127.0.0.1:$Port"

if (-not $NoOpen) {
    Start-Process $Url | Out-Null
}

if ($StaticOnly) {
    Write-Host "[*] Serving STATIC dashboard at $Url (sans API : donnees gelees)" -ForegroundColor Yellow
    Push-Location $DashboardDir
    try {
        python -m http.server $Port
    }
    finally {
        Pop-Location
    }
    return
}

# Defaut : API Kuro (live /api/dashboard + /api/system + UI).
# Le snapshot statique reste le repli si l'API est injoignable.
Write-Host "[*] Serving Kuro API + dashboard at $Url (live, refresh 60s)" -ForegroundColor Green
Write-Host "[*] Press Ctrl+C to stop." -ForegroundColor DarkGray
$env:KURO_RULES_DIR = $RootDir
python -m kuro_dashboard --port $Port
