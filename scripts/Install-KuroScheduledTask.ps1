# Install-KuroScheduledTask.ps1 — planifie Kuro en local (Windows, idempotent).
# v3 (R125) : TOUTES les taches en fenetre cachee via launchers courts.
#   - limite schtasks /TR = 261 caracteres → launchers scripts/task_launchers/*.ps1
#     (garde anti-regression : $MaxTR refuse tout TR trop long AVANT suppression).
#   - pipeline X unifie : KuroXDaily (run_daily.ps1 --annex Helium) est le
#     SEUL orchestrant X. HeliumMarketing est supprime (merge).
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

$LauncherDir = Join-Path $Root "scripts\task_launchers"

# --- Helpers ---------------------------------------------------------------
# Fenetre CACHEE : chaque tache appelle un launcher court (< 261 car pour
# schtasks /TR). Start-Process -NoNewWindow : aucune fenetre meme pour
# python.exe (le flag -WindowStyle Hidden seul de schtasks ne suffit pas :
# le planificateur re-affiche la console du process fils).
# Le launcher propage le code de sortie (garde R116 « Taches planifiees »).
$MaxTR = 250
function Write-PyLauncher {
  param([string]$Name, [string]$Script, [string]$ScriptArgs, [string]$LogFile)
  # Meme commande que l'installateur v2 (prouvee : KuroDaily s'est creee OK) :
  # powershell -WindowStyle Hidden herite sa console cachee au python fils,
  # *>> conserve les logs exactement comme avant, exit propage le code.
  $call = "& '$Py' '$Script'"
  if ($ScriptArgs) { $call += " $ScriptArgs" }
  $call += " *>> '$LogFile'"
  $content = $call + "`r`nexit `$LASTEXITCODE`r`n"
  $path = Join-Path $LauncherDir "$Name.ps1"
  Set-Content -Path $path -Value $content -Encoding UTF8
  return "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$path`""
}
function Write-PsLauncher {
  param([string]$Name, [string]$Ps1, [string]$LogFile)
  $call = "& powershell.exe -NoProfile -ExecutionPolicy Bypass -File '$Ps1'"
  if ($LogFile) { $call += " *>> '$LogFile'" }
  $content = $call + "`r`nexit `$LASTEXITCODE`r`n"
  $path = Join-Path $LauncherDir "$Name.ps1"
  Set-Content -Path $path -Value $content -Encoding UTF8
  return "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$path`""
}
function New-KuroTask {
  param([string]$Name, [string]$TR, [string]$SC, [string]$At, [string]$Day = "", [string]$Mo = "")
  # Garde anti-regression v3 : refuser AVANT suppression si le TR depasse
  # la limite schtasks (incident 19/10 : 8 taches effacees, 1 seule recreee).
  if ($TR.Length -gt $MaxTR) { throw "TR trop long pour $Name ($($TR.Length) > $MaxTR) : $TR" }
  # IMPORTANT : schtasks lance en interne via cmd.exe → les appels directs
  # "schtasks /Delete" DANS ce script heritent le bug d'encodage console de
  # l'agent (incident v4/v5). Deleguer a cmd.exe : appels fiables.
  $a = "/Create /TN `"$Name`" /TR `"$TR`" /SC $SC"
  if ($Mo) { $a += " /MO $Mo" }
  if ($Day) { $a += " /D $Day" }
  $a += " /ST $At /F"
  cmd.exe /c "schtasks $a"
  if ($LASTEXITCODE -ne 0) { throw "Echec creation $Name" }
}
function Remove-KuroTask {
  param([string]$Name)
  cmd.exe /c "schtasks /Delete /TN `"$Name`" /F" 2>&1 | Out-Null
  Write-Host "Supprime (ou absente) : $Name"
}

# --- (suppression idempotente : voir plus bas, APRES validation des TR) ---

# --- Recreation, toutes fenetres cachees -----------------------------------
$Automate = Join-Path $Root "scripts\kuro_automate.py"
$SyncScript = Join-Path $Root "scripts\Sync-ReposServer.ps1"
$FleetScript = Join-Path $Root "scripts\fleet_sync_scheduled.ps1"
$RunDaily = Join-Path $Root "run_daily.ps1"
$DbBackup = Join-Path $Root "scripts\kuro_db_backup.ps1"
$CoworkPick = Join-Path $Root "run-cowork-pick.ps1"
$Replica = Join-Path $Root "scripts\kuro_replica_push.py"
$Replies = Join-Path $Root "scripts\kuro_replies.py"
$ReplicaLog = Join-Path $env:USERPROFILE ".kuro\replica-push.log"

# Garde v3 : generer TOUS les launchers d'abord (la limite /TR est connue
# avant toute suppression → plus jamais 8 taches effacees pour 1 recreee).
$Defs = @(
  @{ N = "KuroDaily"; TR = (Write-PyLauncher "KuroDaily" $Automate "--daily" (Join-Path $Logs "kuro-daily.log")); SC = "DAILY"; At = "06:00" },
  @{ N = "KuroWeekly"; TR = (Write-PyLauncher "KuroWeekly" $Automate "--daily --weekly --full" (Join-Path $Logs "kuro-weekly.log")); SC = "WEEKLY"; At = "07:00"; Day = "MON" },
  @{ N = "KuroSyncRepos"; TR = (Write-PsLauncher "KuroSyncRepos" $SyncScript (Join-Path $Logs "sync-repos.log")); SC = "WEEKLY"; At = "04:00"; Day = "SUN" },
  @{ N = "KuroFleetSync"; TR = (Write-PsLauncher "KuroFleetSync" $FleetScript (Join-Path $Logs "fleet-sync.log")); SC = "WEEKLY"; At = "05:00"; Day = "SAT" },
  @{ N = "KuroXDaily"; TR = (Write-PsLauncher "KuroXDaily" $RunDaily (Join-Path $Root "outputs\x-daily.log")); SC = "DAILY"; At = "20:00" },
  @{ N = "KuroDbBackup"; TR = (Write-PsLauncher "KuroDbBackup" $DbBackup ""); SC = "DAILY"; At = "12:00" },
  @{ N = "KuroOracle"; TR = (Write-PsLauncher "KuroOracle" $CoworkPick ""); SC = "DAILY"; At = "08:00" },
  @{ N = "KuroReplies"; TR = (Write-PyLauncher "KuroReplies" $Replies "--gh --write" (Join-Path $Logs "kuro-replies.log")); SC = "DAILY"; At = "09:00" },
  @{ N = "KuroReplicaPush"; TR = (Write-PyLauncher "KuroReplicaPush" $Replica "" $ReplicaLog); SC = "MINUTE"; At = "00:00"; Mo = "5" }
)
foreach ($d in $Defs) {
  if ($d.TR.Length -gt $MaxTR) { throw "TR trop long pour $($d.N) ($($d.TR.Length) > $MaxTR)" }
}

# --- Suppression idempotente (APRES validation : plus jamais de suppression
# sans recreation derriere — inclut l'ancienne tache HeliumMarketing) -------
if ($Uninstall) {
  foreach ($name in ($Defs | ForEach-Object { $_.N }) + @("HeliumMarketing")) {
    Remove-KuroTask $name
  }
  Write-Host "Desinstalle."; exit 0
}
foreach ($name in ($Defs | ForEach-Object { $_.N }) + @("HeliumMarketing")) {
  Remove-KuroTask $name
}

foreach ($d in $Defs) {
  $extra = @{}
  if ($d.Day) { $extra.Day = $d.Day }
  if ($d.Mo) { $extra.Mo = $d.Mo }
  New-KuroTask -Name $d.N -TR $d.TR -SC $d.SC -At $d.At @extra
}

Write-Host "Installe (fenetres cachees) : KuroDaily 06:00, KuroWeekly lun 07:00, KuroSyncRepos dim 04:00,"
Write-Host "KuroFleetSync sam 05:00, KuroXDaily 20:00 (X unifie hub+Helium), KuroDbBackup 12:00,"
Write-Host "KuroOracle 08:00, KuroReplies 09:00, KuroReplicaPush /5min. HeliumMarketing supprime (merge dans KuroXDaily)."
