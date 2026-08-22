# install-kurupulse.ps1 — compile KuroPulse.cs en exe natif avec logo, et l'installe
# (compilateur C# inclus dans Windows, aucune dépendance à installer)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$kuroRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # apps/kuro-pulse -> kuro-rules
$src = Join-Path $PSScriptRoot "KuroPulse.cs"
$destDir = Join-Path $env:LOCALAPPDATA "KuroPulse"

$csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) {
    $csc = Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe"
}
if (-not (Test-Path $csc)) { throw "csc.exe introuvable" }

New-Item -ItemType Directory -Force -Path $destDir | Out-Null

# Remplacement propre de l'instance AVANT compilation (sinon fichier verrouille)
Get-Process KuroPulse -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 600

# ---------- 0. Logo : carre sombre arrondi + lambda accent ----------
$icoPath = Join-Path $PSScriptRoot "kuro.ico"
$bmp = New-Object System.Drawing.Bitmap 128, 128
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$g.Clear([System.Drawing.Color]::Transparent)

$bgBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(13, 17, 23))
$path = New-Object System.Drawing.Drawing2D.GraphicsPath
$r = 28
$path.AddArc(0, 0, $r, $r, 180, 90)
$path.AddArc(128 - $r, 0, $r, $r, 270, 90)
$path.AddArc(128 - $r, 128 - $r, $r, $r, 0, 90)
$path.AddArc(0, 128 - $r, $r, $r, 90, 90)
$path.CloseFigure()
$g.FillPath($bgBrush, $path)

$borderPen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(48, 54, 61)), 3
$g.DrawPath($borderPen, $path)

$font = New-Object System.Drawing.Font ("Segoe UI Symbol", 66, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$accent = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(88, 166, 255))
$fmt = New-Object System.Drawing.StringFormat
$fmt.Alignment = [System.Drawing.StringAlignment]::Center
$fmt.LineAlignment = [System.Drawing.StringAlignment]::Center
$g.DrawString([char]0x03BB, $font, $accent, (New-Object System.Drawing.RectangleF 0, -6, 128, 134), $fmt)

$dotBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(63, 185, 80))
$g.FillEllipse($dotBrush, 92, 92, 26, 26)

$g.Dispose()
$icon = [System.Drawing.Icon]::FromHandle($bmp.GetHicon())
$fs = [System.IO.File]::Create($icoPath)
$icon.Save($fs)
$fs.Close()
$bmp.Dispose()
Write-Host "[KuroPulse] logo genere: $icoPath"

# ---------- 1. Compilation ----------
& $csc /nologo /target:winexe /optimize+ `
    /win32icon:"$icoPath" `
    /out:"$destDir\KuroPulse.exe" `
    /r:System.Web.Extensions.dll `
    $src
if ($LASTEXITCODE -ne 0) { throw "echec compilation" }
Copy-Item $icoPath "$destDir\kuro.ico" -Force

$oldBat = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\KuroPulse.bat"
if (Test-Path $oldBat) { Remove-Item $oldBat -Force }

# ---------- 3. Raccourcis ----------
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut((Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\KuroPulse.lnk"))
$lnk.TargetPath = "$destDir\KuroPulse.exe"
$lnk.WorkingDirectory = $destDir
$lnk.Description = "KuroPulse - intelligence d'entreprise lambda-Section"
$lnk.Save()
$deskLnk = $ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "KuroPulse.lnk"))
$deskLnk.TargetPath = "$destDir\KuroPulse.exe"
$deskLnk.WorkingDirectory = $destDir
$deskLnk.Save()

Write-Host "[KuroPulse] installe: $destDir\KuroPulse.exe"
Start-Process "$destDir\KuroPulse.exe"
Write-Host "[KuroPulse] lance."
