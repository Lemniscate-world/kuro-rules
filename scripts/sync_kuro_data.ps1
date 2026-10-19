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

$ok = 0; $skip = 0
foreach ($f in $files) {
    $src = Join-Path $LocalDir $f
    if (-not (Test-Path $src)) { Write-Warning "absent: $f"; $skip++; continue }
    scp @sshOpts $src "${Server}:${RemoteDir}/$f"
    if ($LASTEXITCODE -eq 0) { $ok++; Write-Host "ok: $f" }
    else { Write-Error "scp KO: $f" }
}

# Verrouillage des permissions cote serveur (defense en profondeur)
$remote = "chmod 600 $RemoteDir/* 2>/dev/null; ls -la $RemoteDir"
ssh @sshOpts $Server $remote | Out-Host

Write-Host "SYNC-DONE ok=$ok skip=$skip"
exit $(if ($ok -gt 0) { 0 } else { 1 })
