param(
    [int]$Port = 8765,
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DashboardDir = Join-Path $RootDir "dashboard"
$GeneratorPath = Join-Path $DashboardDir "generate_dashboard.py"

if (-not (Test-Path $GeneratorPath)) {
    throw "Dashboard generator not found: $GeneratorPath"
}

Write-Host "[*] Refreshing dashboard snapshot..." -ForegroundColor Cyan
python $GeneratorPath

if ($LASTEXITCODE -ne 0) {
    throw "Dashboard snapshot generation failed."
}

$Url = "http://127.0.0.1:$Port"

if (-not $NoOpen) {
    Start-Process $Url | Out-Null
}

Write-Host "[*] Serving dashboard at $Url" -ForegroundColor Green
Write-Host "[*] Press Ctrl+C to stop." -ForegroundColor DarkGray

Push-Location $DashboardDir
try {
    python -m http.server $Port
}
finally {
    Pop-Location
}
