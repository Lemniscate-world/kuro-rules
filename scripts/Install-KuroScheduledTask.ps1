# Install-KuroScheduledTask.ps1 — planifie Kuro en local (Windows, idempotent).
# Utilise schtasks.exe (les cmdlets ScheduledTasks echouent si WMI est corrompu).
# Quotidien 06:00 : kuro_automate.py --daily
# Lundi 07:00    : kuro_automate.py --daily --weekly --full (Discord + ecritures)
# Usage (tache utilisateur, admin non requis) :
#   powershell -ExecutionPolicy Bypass -File scripts\Install-KuroScheduledTask.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\Install-KuroScheduledTask.ps1 -Uninstall
param([switch]$Uninstall)
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSCommandPath -Parent) -Parent
$Py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Py) { throw "python introuvable dans PATH" }
$Script = Join-Path $Root "scripts\kuro_automate.py"
foreach ($name in @("KuroDaily", "KuroWeekly")) {
  try { schtasks /Delete /TN $name /F 2>&1 | Out-Null; Write-Host "Supprime : $name" }
  catch { Write-Host "Absente (rien a supprimer) : $name" }
}
if ($Uninstall) { Write-Host "Desinstalle."; exit 0 }
schtasks /Create /TN "KuroDaily" /TR "`"$Py`" `"$Script`" --daily" /SC DAILY /ST 06:00 /F
if ($LASTEXITCODE -ne 0) { throw "Echec creation KuroDaily" }
schtasks /Create /TN "KuroWeekly" /TR "`"$Py`" `"$Script`" --daily --weekly --full" /SC WEEKLY /D MON /ST 07:00 /F
if ($LASTEXITCODE -ne 0) { throw "Echec creation KuroWeekly" }
Write-Host "Installe : KuroDaily 06:00 quotidien, KuroWeekly lundi 07:00 full."
schtasks /Query /TN "KuroDaily" | Select-Object -Last 3
schtasks /Query /TN "KuroWeekly" | Select-Object -Last 3
