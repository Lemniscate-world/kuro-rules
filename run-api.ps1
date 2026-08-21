param(
    [int]$Port = 8767,
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ApiPath = Join-Path $RootDir "scripts\kuro_api.py"

if (-not (Test-Path $ApiPath)) {
    throw "kuro_api.py introuvable: $ApiPath"
}

Write-Host "[Kuro] Demarrage de l'API sur http://127.0.0.1:$Port ..." -ForegroundColor Cyan
Write-Host "[Kuro] Endpoints: /api/status /api/projects /api/alerts /api/sessions /api/memory /api/summary /api/ask" -ForegroundColor DarkGray

python $ApiPath --port $Port
