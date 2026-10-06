param(
    [int]$Top = 5,
    [string]$Exclude = "",
    [switch]$NoPost
)
# run-cowork-pick.ps1 — 1 double-clic = pick Oracle + post Discord. Zero frappe.
$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script = Join-Path $RootDir "scripts\cowork_pick.py"
if (-not (Test-Path $Script)) { throw "cowork_pick.py introuvable: $Script" }
$args = @($Script, "--top", $Top)
if ($Exclude -ne "") { $args += @("--exclude", $Exclude) }
if (-not $NoPost) { $args += @("--discord") } else { Write-Host "[Kuro] Dry-run (pas de post Discord)" -ForegroundColor DarkGray }
Write-Host "[Kuro] Oracle coworking : analyse + pick..." -ForegroundColor Cyan
& python @args
Write-Host "[Kuro] Termine. Reponse attendue : aucune frappe requise." -ForegroundColor Green
