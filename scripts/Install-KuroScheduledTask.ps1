# Install-KuroScheduledTask.ps1 — planifie Kuro en local (Windows, idempotent).
# Quotidien 06:00 : kuro_automate.py --daily
# Lundi 07:00    : kuro_automate.py --daily --weekly --full (Discord + ecritures)
# Usage (admin non requis, tache utilisateur) :
#   powershell -ExecutionPolicy Bypass -File scripts\Install-KuroScheduledTask.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\Install-KuroScheduledTask.ps1 -Uninstall
param([switch]$Uninstall)
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSCommandPath -Parent) -Parent
$Py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Py) { throw "python introuvable dans PATH" }
$Script = Join-Path $Root "scripts\kuro_automate.py"
foreach ($name in @("KuroDaily", "KuroWeekly")) {
  $t = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
  if ($t) { Unregister-ScheduledTask -TaskName $name -Confirm:$false; Write-Host "Supprime : $name" }
}
if ($Uninstall) { Write-Host "Desinstalle."; exit 0 }
$DailyArgs = "`"$Script`" --daily"
$WeeklyArgs = "`"$Script`" --daily --weekly --full"
$DailyAction = New-ScheduledTaskAction -Execute $Py -Argument $DailyArgs -WorkingDirectory $Root
$WeeklyAction = New-ScheduledTaskAction -Execute $Py -Argument $WeeklyArgs -WorkingDirectory $Root
$DailyTrigger = New-ScheduledTaskTrigger -Daily -At "06:00"
$WeeklyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "07:00"
Register-ScheduledTask -TaskName "KuroDaily" -Action $DailyAction -Trigger $DailyTrigger -Description "Kuro chaine quotidienne (lecture seule + publication locale)" | Out-Null
Register-ScheduledTask -TaskName "KuroWeekly" -Action $WeeklyAction -Trigger $WeeklyTrigger -Description "Kuro hebdo lundi (full + Discord)" | Out-Null
Write-Host "Installe : KuroDaily 06:00 quotidien, KuroWeekly lundi 07:00 full."
Write-Host "Verif : Get-ScheduledTask KuroDaily, KuroWeekly | Get-ScheduledTaskInfo"
