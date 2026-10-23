<#
.SYNOPSIS
    Sync kuro-data: pousse les fichiers de pilotage locaux (gitignores)
    vers le serveur Kuro via SSH/SCP (transport chiffre + chmod 600).
.DESCRIPTION
    Fichiers synchronises :
      - pipeline.local.json  (suivi interviews)
      - finances.local.json  (depenses/recettes)
      - strategy.local.json  (objectifs, focus trimestre, concurrents)
      - TRUTH_DAILY.md       (verite du jour)
    Destinations : /home/gad/kuro-data/ (mode 600, dossier 700)
    Non versionnes localement (gitignores) et non versionnes distants.
#>
param(
    [string]$Server = 'gad@192.168.1.84',
    [string]$LocalDir = 'C:\Users\Utilisateur\Documents\kuro-rules',
    [string]$RemoteDir = '/home/gad/kuro-data',
    [int]$TimeoutSec = 25
)

$ErrorActionPreference = 'Stop'
$files = @('pipeline.local.json', 'finances.local.json', 'strategy.local.json', 'TRUTH_DAILY.md')
$sshOpts = @('-o', "ConnectTimeout=$TimeoutSec", '-o', 'BatchMode=yes')
$MaxAttempts = 3   # R116 : SSH ephemere (timeout 07:00) ne doit plus tuer la synchro

$ok = 0; $skip = 0; $fail = 0
foreach ($f in $files) {
    $src = Join-Path $LocalDir $f
    if (-not (Test-Path $src)) { Write-Warning "absent: $f"; $skip++; continue }
    $sent = $false
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        scp @sshOpts $src "${Server}:${RemoteDir}/$f"
        if ($LASTEXITCODE -eq 0) { $sent = $true; break }
        Write-Warning "scp KO: $f (tentative $attempt/$MaxAttempts)"
        if ($attempt -lt $MaxAttempts) { Start-Sleep -Seconds 5 }
    }
    if ($sent) { $ok++; Write-Host "ok: $f" }
    else { $fail++; Write-Warning "scp abandonne apres $MaxAttempts essais: $f" }
}

# Verrouillage des permissions cote serveur (defense en profondeur) —
# non bloquant : si le serveur est down, la synchro partielle reste valable.
if ($ok -gt 0) {
    $remote = "chmod 600 $RemoteDir/* 2>/dev/null; ls -la $RemoteDir"
    ssh @sshOpts $Server $remote | Out-Host
}

Write-Host "SYNC-DONE ok=$ok skip=$skip fail=$fail"
exit $(if ($fail -eq 0 -and $ok -gt 0) { 0 } else { 1 })
