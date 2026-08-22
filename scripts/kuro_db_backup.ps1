# kuro_db_backup.ps1 — copie horodatée de kuro.db, garde les 14 dernières
$ErrorActionPreference = "Stop"

$src = Join-Path $env:USERPROFILE ".kuro\kuro.db"
if (-not (Test-Path $src)) {
    Write-Host "[kuro-backup] kuro.db introuvable"
    exit 0
}

$destDir = Join-Path $env:USERPROFILE "Documents\kuro-rules\SYNC_BACKUPS\kuro-db"
New-Item -ItemType Directory -Force -Path $destDir | Out-Null

$stamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$dest = Join-Path $destDir "kuro-$stamp.db"

# SQLite : copier après checkpoint pour cohérence
python -c "import sqlite3; sqlite3.connect(r'$src').execute('PRAGMA wal_checkpoint(TRUNCATE)')" 2>$null
Copy-Item -Path $src -Destination $dest -Force

# Purge : garder les 14 plus récents
Get-ChildItem $destDir -Filter "kuro-*.db" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 14 |
    Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "[kuro-backup] OK -> $dest"
