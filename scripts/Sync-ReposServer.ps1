# Sync-ReposServer.ps1 — replique ~/Documents (repos git) vers ~/repos du serveur.
# Idempotent : saute les repos deja sains (git rev-parse OK cote serveur).
# Exclut le regenerable (target/, node_modules/, .venv/...) mais GARDE .git.
# Exclut kuro + kuro-rules (sources vivantes du daemon : sync via git, jamais ecrase).
# Cas speciaux automatises : Vault (.git fragile + dossiers Drive en lecture
# seule -> git bundle + attrib -r) et worktrees (.git fichier -> git worktree
# add cote serveur sur le depot parent).
#
# Usage :
#   powershell -ExecutionPolicy Bypass -File scripts\Sync-ReposServer.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\Sync-ReposServer.ps1 -Server gad@192.168.1.84 -DryRun
param(
  [string]$Server = "gad@192.168.1.84",
  [string]$DocsRoot = (Join-Path $HOME "Documents"),
  [string]$DestRoot = "~/repos",
  [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$Stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$Log = Join-Path $PSScriptRoot "sync-repos-server.log"

# Noms LOCAUX a ne jamais transferer (doublons insensibles a la casse geres :
# "Forma" existe deja comme "forma", "Horcruxe Labs" comme "Horcruxe-Labs").
$Skip = @("kuro", "kuro-rules", "Forma", "Horcruxe Labs", "LifeTrack",
  "NeuralDBG", "OpenQuant", "TokenWise")

function Log([string]$msg) {
  $line = "[$Stamp] $msg"
  Write-Host $line
  Add-Content -Path $Log -Value $line
}

function Invoke-Remote([string]$Script) {
  ssh -o ConnectTimeout=15 $Server $Script 2>&1
}

# Repos type Vault : .git fragile (hardlinks) + dossiers lecture seule
# (sync Drive). Strategie : attrib -r local, historique via git bundle,
# fichiers via tar sans .git.
$VaultNames = @("Vault")

function Sync-VaultRepo([string]$Name, [string]$LocalDir) {
  Log "VAULT $Name : debloque attributs lecture seule..."
  Get-ChildItem $LocalDir -Recurse -Directory -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Attributes -band [IO.FileAttributes]::ReadOnly } |
    ForEach-Object { $_.Attributes = $_.Attributes -band (-bnot [IO.FileAttributes]::ReadOnly) }
  $bundle = Join-Path ([IO.Path]::GetTempPath()) "$Name.bundle"
  cmd /c "git -C ""$LocalDir"" bundle create ""$bundle"" --all 2>NUL"
  scp -o ConnectTimeout=30 $bundle ($Server + ":/tmp/$Name.bundle") | Out-Null
  $remote = 'rm -rf ' + $DestRoot + '/' + $Name + ' && git clone -q /tmp/' + $Name +
    '.bundle ' + $DestRoot + '/' + $Name + ' && git -C ' + $DestRoot + '/' + $Name + ' log --oneline -1'
  $out = Invoke-Remote $remote
  Log "VAULT $Name clone : $out"
  cmd /c "tar --exclude=$Name/.git --exclude=*/.tmp.driveupload/* --exclude=*/.pytest_cache/* -cf - -C ""$DocsRoot"" ""$Name"" | ssh -o ConnectTimeout=10 $Server ""tar -xf - -C $DestRoot && chmod -R u+rwX $DestRoot/$Name && echo OK-$Name"""
  return $LASTEXITCODE -eq 0
}

# Worktree local (.git = fichier gitdir:) : recrée cote serveur via
# git worktree add sur le depot parent (jamais de copie du pointeur C:/...).
function Sync-WorktreeRepo([string]$Name, [string]$LocalDir) {
  $gitdir = (Get-Content (Join-Path $LocalDir ".git") -TotalCount 1) -replace "^gitdir:\s*", ""
  $parent = Split-Path (Split-Path $gitdir -Parent) -Parent | Split-Path -Leaf
  $branch = (cmd /c "git -C ""$LocalDir"" rev-parse --abbrev-ref HEAD 2>NUL").Trim()
  Log "WORKTREE $Name : parent=$parent branche=$branch"
  if (-not $parent -or -not $branch) { Log "WORKTREE $Name : parent/branche illisible, ignore."; return $false }
  $remote = 'git -C ' + $DestRoot + '/' + $parent + ' worktree prune 2>/dev/null; ' +
    'git -C ' + $DestRoot + '/' + $parent + ' worktree add ' + $DestRoot + '/' + $Name +
    ' ' + $branch + ' 2>&1 | tail -n 2'
  $out = Invoke-Remote $remote
  Log "WORKTREE $Name : $out"
  $check = Invoke-Remote ('git -C ' + $DestRoot + '/' + $Name + ' log --oneline -1 2>&1')
  return ($check -match "^[0-9a-f]{7} ")
}

$repos = Get-ChildItem $DocsRoot -Directory |
  Where-Object { (Test-Path (Join-Path $_.FullName ".git")) -and ($Skip -notcontains $_.Name) } |
  Sort-Object Name
Log "TOTAL locaux a sync (hors skips): $($repos.Count)"

# Etat serveur en UN appel (evite 50 handshakes) : "nom:hash" ou "nom:NO-GIT".
$remote = @{}
try {
  $RemoteCmd = 'for d in ' + $DestRoot + '/*/; do n=$(basename "$d"); ' +
    'if [ -d "$d/.git" ]; then echo "$n:$(git -C "$d" log --oneline -1 2>/dev/null || echo BROKEN)"; ' +
    'else echo "$n:NO-GIT"; fi; done'
  $out = ssh -o ConnectTimeout=10 $Server $RemoteCmd 2>&1
  foreach ($line in $out) {
    if ($line -match "^([^:]+):(.*)$") { $remote[$Matches[1]] = $Matches[2] }
  }
  Log "Etat serveur lu : $($remote.Count) dossiers."
} catch {
  Log "AVERTISSEMENT lecture etat serveur impossible ($_) : tout sera transfere."
}

$Excludes = @("--exclude=*/node_modules/*", "--exclude=*/.venv/*",
  "--exclude=*/venv/*", "--exclude=*/target/*", "--exclude=*/__pycache__/*",
  "--exclude=*/.pytest_cache/*", "--exclude=*/.mypy_cache/*",
  "--exclude=*/.next/*", "--exclude=*/dist/*", "--exclude=*/coverage/*",
  "--exclude=*/.hypothesis/*", "--exclude=*/.tmp.driveupload/*") -join " "

$done = 0; $failed = @()
foreach ($r in $repos) {
  $n = $r.Name
  # Worktree locale (.git = fichier gitdir:) : jamais transferee telle quelle
  # (le pointeur C:/... casserait le serveur). Gerer via git worktree add.
  $gitPath = Join-Path $r.FullName ".git"
  $isWorktree = (Test-Path $gitPath -PathType Leaf)
  if ($isWorktree) {
    if ($DryRun) { Log "DRYRUN worktree : $n"; continue }
    if (Sync-WorktreeRepo $n $r.FullName) { $done++; Log "OK $n (worktree)" }
    else { $failed += $n; Log "ECHEC $n (worktree)" }
    continue
  }
  if ($VaultNames -contains $n) {
    if ($DryRun) { Log "DRYRUN vault : $n"; continue }
    if (Sync-VaultRepo $n $r.FullName) { $done++; Log "OK $n (vault)" }
    else { $failed += $n; Log "ECHEC $n (vault)" }
    continue
  }
  if ($remote.ContainsKey($n) -and $remote[$n] -notmatch "^(NO-GIT|BROKEN|$)" -and -not $isWorktree) {
    Log "SKIP $n (sain : $($remote[$n]))"
    continue
  }
  if ($DryRun) { Log "DRYRUN transfererait : $n"; continue }
  $t0 = Get-Date
  # NOTE : le pipe tar|ssh passe par cmd (binaire propre : PowerShell corrompt
  # les pipes binaires ; 2>&1 sur tar corrompt aussi le flux).
  cmd /c "tar $Excludes -cf - -C ""$DocsRoot"" ""$n"" | ssh -o ConnectTimeout=10 $Server ""mkdir -p $DestRoot && tar -xf - -C $DestRoot && echo OK-$n"""
  if ($LASTEXITCODE -ne 0) {
    $failed += $n
    Log "ECHEC $n (exit $LASTEXITCODE)"
    continue
  }
  $check = ssh -o ConnectTimeout=10 $Server "git -C $DestRoot/$n log --oneline -1 2>&1"
  if ($LASTEXITCODE -ne 0 -and -not $isWorktree) {
    $failed += $n
    Log "ECHEC verif $n : $check"
    continue
  }
  $mins = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
  $done++
  Log "OK $n (${mins} min) <- $check"
}
Log "TERMINE : $done transferes, $($failed.Count) echecs$(if ($failed) { ' : ' + ($failed -join ', ') })."
if ($failed.Count -gt 0) { exit 1 }
