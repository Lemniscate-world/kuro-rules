# install-kurupulse.ps1 — compile KuroPulse.cs en exe natif et l'installe
# (compilateur C# inclus dans Windows, aucune dépendance à installer)

$ErrorActionPreference = "Stop"

$kuroRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # apps/kuro-pulse -> kuro-rules
$src = Join-Path $PSScriptRoot "KuroPulse.cs"
$destDir = Join-Path $env:LOCALAPPDATA "KuroPulse"

$csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) {
    $csc = Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe"
}
if (-not (Test-Path $csc)) { throw "csc.exe introuvable" }

New-Item -ItemType Directory -Force -Path $destDir | Out-Null

Write-Host "[KuroPulse] compilation..."
& $csc /nologo /target:winexe /optimize+ `
    /out:"$destDir\KuroPulse.exe" `
    /r:System.Web.Extensions.dll `
    $src
if ($LASTEXITCODE -ne 0) { throw "echec compilation" }

# Retirer l'ancien lanceur PowerShell du tray (remplace par l'exe)
$oldBat = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\KuroPulse.bat"
if (Test-Path $oldBat) { Remove-Item $oldBat -Force }

# Raccourci demarrage automatique
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut((Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\KuroPulse.lnk"))
$lnk.TargetPath = "$destDir\KuroPulse.exe"
$lnk.WorkingDirectory = $destDir
$lnk.Description = "KuroPulse - intelligence d'entreprise lambda-Section"
$lnk.Save()

# Raccourci Bureau aussi
$deskLnk = $ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "KuroPulse.lnk"))
$deskLnk.TargetPath = "$destDir\KuroPulse.exe"
$deskLnk.WorkingDirectory = $destDir
$deskLnk.Save()

Write-Host "[KuroPulse] installe: $destDir\KuroPulse.exe"
Write-Host "[KuroPulse] auto-start au login + racourci Bureau"

Start-Process "$destDir\KuroPulse.exe"
Write-Host "[KuroPulse] lance."
