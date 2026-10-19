# Install-KuroScheduledTask.ps1 — planifie Kuro en local (Windows, idempotent).
# v2 (R125) : TOUTES les taches en fenetre cachee (plus de fenetres CMD) +
#             pipeline X unifie : KuroXDaily (run_daily.ps1 --annex Helium)
#             est le SEUL orchestrant X. HeliumMarketing est supprime (merge).
# Utilise schtasks.exe (les cmdlets ScheduledTasks echouent si WMI est corrompu).
# Quotidien 06:00 : kuro_automate.py --daily            -> logs\kuro-daily.log
# Lundi 07:00    : kuro_automate.py --daily --weekly --full -> logs\kuro-weekly.log
# Dimanche 04:00 : Sync-ReposServer.ps1 (miroir ~/Documents -> serveur ~/repos)
# Samedi 05:00   : fleet_sync_scheduled.ps1
# Quotidien 20:00: run_daily.ps1 (X : hub + annexe Helium, R94/R120)
# Quotidien 12:00: kuro_db_backup.ps1
# Quotidien 08:00: run-cowork-pick.ps1 (Oracle Discord)
# Quotidien 09:00: kuro_replies.py --gh --write (file de réponses R96/R121)
# Toutes 5 min   : kuro_replica_push.py (RPO <= 10 min)
# Usage (tache utilisateur, admin non requis) :
#   powershell -ExecutionPolicy Bypass -File scripts\Install-KuroScheduledTask.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\Install-KuroScheduledTask.ps1 -Uninstall
param([switch]$Uninstall)
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSCommandPath -Parent) -Parent
$Py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Py) { throw "python introuvable dans PATH" }
$Logs = Join-Path $Root "logs"
if (-not (Test-Path $Logs)) { New-Item -ItemType Directory -Path $Logs | Out-Null }
$ReplicaLog = Join-Path $env:USERPROFILE ".kuro\replica-push.log"

# --- Helpers ---------------------------------------------------------------
# Tache via powershell cache + redirection vers un log : la fenetre console
# n'apparait JAMAIS, et $LASTEXITCODE est propage (garde R125 doctor).
function Get-HiddenPyTR {
  param([string]$Script, [string]$ScriptArgs, [string]$LogFile)
  $inner = "& '$Py' '$Script'"
  if ($ScriptArgs) { $inner += " $ScriptArgs" }
  $inner += " *>> '$LogFile'; exit `$LASTEXITCODE"
  # PS 5.1 mange les guillemets internes : il faut les echapper en \" sinon
  # schtasks recoit ''C:\...python.exe'' et refuse la tache.
  return 'powershell.exe -NoProfile -WindowStyle Hidden -Command \"' + $inner + '\"'
}
function Get-HiddenPsTR {
  param([string]$Ps1)
  return 'powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File \"' + $Ps1 + '\"'
}
function New-KuroTask {
  param([string]$Name, [string]$TR, [string]$SC, [string]$At, [string]$Day = "", [string]$Mo = "")
  $a = @("/Create", "/TN", $Name, "/TR", $TR, "/SC", $SC)
  if ($Mo) { $a += @("/MO", $Mo) }
  if ($Day) { $a += @("/D", $Day) }
  $a += @("/ST", $At, "/F")
  & schtasks.exe @a
  if ($LASTEXITCODE -ne 0) { throw "Echec creation $Name" }
}

# --- Suppression idempotente (inclut l'ancienne tache HeliumMarketing) -----
$TaskNames = @("KuroDaily", "KuroWeekly", "KuroSyncRepos", "KuroFleetSync",
  "KuroXDaily", "KuroDbBackup", "KuroOracle", "KuroReplies", "KuroReplicaPush",
  "HeliumMarketing")
foreach ($name in $TaskNames) {
  schtasks /Delete /TN $name /F 2>&1 | Out-Null
  Write-Host "Supprime (ou absente) : $name"
}
if ($Uninstall) { Write-Host "Desinstalle."; exit 0 }

# --- Recreation, toutes fenetres cachees -----------------------------------
$Automate = Join-Path $Root "scripts\kuro_automate.py"
$SyncScript = Join-Path $Root "scripts\Sync-ReposServer.ps1"
$FleetScript = Join-Path $Root "scripts\fleet_sync_scheduled.ps1"
$RunDaily = Join-Path $Root "run_daily.ps1"
$DbBackup = Join-Path $Root "scripts\kuro_db_backup.ps1"
$CoworkPick = Join-Path $Root "run-cowork-pick.ps1"
$Replica = Join-Path $Root "scripts\kuro_replica_push.py"
$Replies = Join-Path $Root "scripts\kuro_replies.py"

New-KuroTask -Name "KuroDaily" -TR (Get-HiddenPyTR $Automate "--daily" (Join-Path $Logs "kuro-daily.log")) -SC DAILY -At "06:00"
New-KuroTask -Name "KuroWeekly" -TR (Get-HiddenPyTR $Automate "--daily --weekly --full" (Join-Path $Logs "kuro-weekly.log")) -SC WEEKLY -At "07:00" -Day "MON"
New-KuroTask -Name "KuroSyncRepos" -TR (Get-HiddenPsTR $SyncScript) -SC WEEKLY -At "04:00" -Day "SUN"
New-KuroTask -Name "KuroFleetSync" -TR (Get-HiddenPsTR $FleetScript) -SC WEEKLY -At "05:00" -Day "SAT"
New-KuroTask -Name "KuroXDaily" -TR (Get-HiddenPsTR $RunDaily) -SC DAILY -At "20:00"
New-KuroTask -Name "KuroDbBackup" -TR (Get-HiddenPsTR $DbBackup) -SC DAILY -At "12:00"
New-KuroTask -Name "KuroOracle" -TR (Get-HiddenPsTR $CoworkPick) -SC DAILY -At "08:00"
New-KuroTask -Name "KuroReplies" -TR (Get-HiddenPyTR $Replies "--gh --write" (Join-Path $Logs "kuro-replies.log")) -SC DAILY -At "09:00"
New-KuroTask -Name "KuroReplicaPush" -TR (Get-HiddenPyTR $Replica "" $ReplicaLog) -SC MINUTE -At "00:00" -Mo "5"

Write-Host "Installe (fenetres cachees) : KuroDaily 06:00, KuroWeekly lun 07:00, KuroSyncRepos dim 04:00,"
Write-Host "KuroFleetSync sam 05:00, KuroXDaily 20:00 (X unifie hub+Helium), KuroDbBackup 12:00,"
Write-Host "KuroOracle 08:00, KuroReplies 09:00, KuroReplicaPush /5min. HeliumMarketing supprime (merge dans KuroXDaily)."
