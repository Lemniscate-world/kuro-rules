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
# Quotidien 09:00: kuro_replies.py --gh --x --write (file R96/R121 + signaux X)
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
  # Le "2>nul" doit etre DU cote cmd.exe : en PowerShell 5.1, "2>&1" d'une
  # commande native transforme la sortie d'erreur en ErrorRecord, et $ErrorActionPreference
  # = "Stop" du script ABORT l'installateur (incident 24/10 : HeliumMarketing
  # absente -> 10 taches supprimees, 0 recreees). Suppression idempotente.
  cmd.exe /c "schtasks /Delete /TN `"$Name`" /F 2>nul" | Out-Null
}
function Set-TaskRobustness {
  # R116 : les parametres par defaut de schtasks font RATER des executions.
  # Incident 24/10 : KuroDbBackup ne tournait pas les jours de sommeil/PC eteint
  # a 12:00 ni sur batterie (dernier resultat 0x800710E0) -> doctor en FAIL.
  # Round-trip XML (meme technique que le fix) :
  #   - StartWhenAvailable : rattraper des que possible un creneau manque
  #   - batterie et nee permissives : la tache ne saute plus sur les cond.
  param([string]$Name)
  $tmp = Join-Path $env:TEMP "kuro-task-$Name.xml"
  $lines = cmd.exe /c "schtasks /Query /TN `"$Name`" /XML 2>nul"
  if ($LASTEXITCODE -ne 0 -or -not $lines) {
    Write-Host "  robustesse : XML indisponible pour $Name"
    return
  }
  $t = $lines -join "`r`n"
  if ($t -notlike '*StartWhenAvailable*') {
    $t = $t -replace '<Settings>', "<Settings>`r`n    <StartWhenAvailable>true</StartWhenAvailable>"
  }
  $t = $t -replace '<DisallowStartIfOnBatteries>true</DisallowStartIfOnBatteries>', '<DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>'
  $t = $t -replace '<StopIfGoingOnBatteries>true</StopIfGoingOnBatteries>', '<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>'
  $t = $t -replace '<StopOnIdleEnd>true</StopOnIdleEnd>', '<StopOnIdleEnd>false</StopOnIdleEnd>'
  [System.IO.File]::WriteAllText($tmp, $t, [System.Text.Encoding]::Unicode)
  cmd.exe /c "schtasks /Create /TN `"$Name`" /XML `"$tmp`" /F"
  $ok = $LASTEXITCODE -eq 0
  Remove-Item $tmp -Force -ErrorAction SilentlyContinue
  if ($ok) { Write-Host "  robustesse : $Name (rattrapage creneaux + batterie + nee)" }
  else { Write-Host "  robustesse : ECHEC $Name" }
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
$Watchdog = Join-Path $Root "scripts\kuro_watchdog_win.ps1"
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
  @{ N = "KuroReplies"; TR = (Write-PyLauncher "KuroReplies" $Replies "--gh --x --write" (Join-Path $Logs "kuro-replies.log")); SC = "DAILY"; At = "09:00" },
  @{ N = "KuroReplicaPush"; TR = (Write-PyLauncher "KuroReplicaPush" $Replica "" $ReplicaLog); SC = "MINUTE"; At = "00:00"; Mo = "5" },
  # NOTE 24/10 : la tache du watchdog reseau avait DISPARU (log fige au 02/10,
  # serveur 192.168.1.84 down sans aucune alerte). Elle appartient au perimetre
  # HIDDEN_TASKS de kuro_doctor : la recreer ici garantit qu'elle revient.
  @{ N = "KuroWatchdogWin"; TR = (Write-PsLauncher "KuroWatchdogWin" $Watchdog ""); SC = "MINUTE"; At = "00:00"; Mo = "15" }
)
foreach ($d in $Defs) {
  if ($d.TR.Length -gt $MaxTR) { throw "TR trop long pour $($d.N) ($($d.TR.Length) > $MaxTR)" }
}

# --- Suppression minimisee (APRES validation) -------------------------------
# PLUS DE SUPPRESSION COLLECTIVE : New-KuroTask passe /F, l'ecrasement suffit.
# Supprimer puis recrée = fenetre d'ouverture ou tout echec (TR, encodage)
# laisse des taches mortes — incident 19/10 (8 effacees) et 24/10 (10 effacees,
# 0 recreees, abort sur HeliumMarketing absente). On ne retire que l'heritage.
if ($Uninstall) {
  foreach ($name in ($Defs | ForEach-Object { $_.N }) + @("HeliumMarketing")) {
    Remove-KuroTask $name
  }
  Write-Host "Desinstalle."; exit 0
}
Remove-KuroTask "HeliumMarketing"

foreach ($d in $Defs) {
  $extra = @{}
  if ($d.Day) { $extra.Day = $d.Day }
  if ($d.Mo) { $extra.Mo = $d.Mo }
  New-KuroTask -Name $d.N -TR $d.TR -SC $d.SC -At $d.At @extra
  Set-TaskRobustness -Name $d.N
}

Write-Host "Installe (fenetres cachees) : KuroDaily 06:00, KuroWeekly lun 07:00, KuroSyncRepos dim 04:00,"
Write-Host "KuroFleetSync sam 05:00, KuroXDaily 20:00 (X unifie hub+Helium), KuroDbBackup 12:00,"
Write-Host "KuroOracle 08:00, KuroReplies 09:00, KuroReplicaPush /5min, KuroWatchdogWin /15min."
Write-Host "HeliumMarketing supprime (merge dans KuroXDaily). Robustesse : rattrapage creneaux + batterie."
