# KuroPulse — icône tray type Gitify pour l'intelligence d'entreprise Kuro
# PowerShell pur (WinForms), aucune dépendance à installer.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File KuroPulse.ps1            # boucle tray
#   powershell ... -TestMode                                          # test headless

param(
    [switch]$TestMode,
    [string]$ApiBase = "http://127.0.0.1:8767",
    [int]$IntervalMinutes = 5
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$script:kuroRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)  # apps/kuro-tray -> kuro-rules

function Get-KuroState {
    try {
        $status = Invoke-RestMethod -Uri "$ApiBase/api/status?ts=$(Get-Date -UFormat %s)" -TimeoutSec 5
        $robot = Invoke-RestMethod -Uri "$ApiBase/api/robot?ts=$(Get-Date -UFormat %s)" -TimeoutSec 5
        return @{
            ok = $true
            ci = if ($robot.ci_overall) { $robot.ci_overall } else { "unknown" }
            engine = if ($robot.llm_engine) { $robot.llm_engine } else { "deterministe" }
            daemon = if ($robot.daemon -and $robot.daemon.timestamp) { ([datetime]$robot.daemon.timestamp).ToString("dd/MM HH:mm") } else { "?" }
            alerts = if ($status.alerts_open -ne $null) { [int]$status.alerts_open } else { 0 }
        }
    } catch { return @{ ok = $false } }
}

function Ensure-Api {
    try {
        Invoke-RestMethod -Uri "$ApiBase/api/status" -TimeoutSec 3 | Out-Null
        return $true
    } catch {
        $apiScript = Join-Path $script:kuroRoot "scripts\kuro_api.py"
        if (Test-Path $apiScript) {
            Start-Process pythonw -ArgumentList "`"$apiScript`" --port 8767" -WindowStyle Hidden
            Start-Sleep -Seconds 4
            return $true
        }
        return $false
    }
}

function New-KuroIcon([string]$color) {
    $bmp = New-Object System.Drawing.Bitmap 16, 16
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.Clear([System.Drawing.Color]::Transparent)
    $brush = switch ($color) {
        "green" { [System.Drawing.Brushes]::LimeGreen }
        "red"   { [System.Drawing.Brushes]::Red }
        default { [System.Drawing.Brushes]::Gray }
    }
    $g.FillEllipse($brush, 2, 2, 12, 12)
    $g.Dispose()
    $icon = [System.Drawing.Icon]::FromHandle($bmp.GetHicon())
    $bmp.Dispose()
    return $icon
}

if ($TestMode) {
    [void](Ensure-Api)
    $s = Get-KuroState
    Write-Host ("STATE: ok={0} ci={1} engine={2} daemon={3} alerts={4}" -f $s.ok, $s.ci, $s.engine, $s.daemon, $s.alerts)
    exit 0
}

[void](Ensure-Api)

$form = New-Object System.Windows.Forms.Form
$form.ShowInTaskbar = $false
$form.WindowState = "Minimized"
$form.FormBorderStyle = "None"

$tray = New-Object System.Windows.Forms.NotifyIcon
$tray.Text = "KuroPulse : connexion..."
$tray.Visible = $true
$tray.Icon = New-KuroIcon "gray"

$menu = New-Object System.Windows.Forms.ContextMenuStrip
$menu.Items.Add("Ouvrir le Desk", $null, { param($s, $e) Start-Process "$ApiBase/" }).Name = "desk"
$menu.Items.Add("Journal des actions", $null, { param($s, $e) Start-Process notepad (Join-Path $script:kuroRoot "KURO_ACTIONS_LOG.md") })
$menu.Items.Add("GitHub Actions", $null, { param($s, $e) Start-Process "https://github.com/Lemniscate-world/kuro-rules/actions" })
$menu.Items.Add("-")
$menu.Items.Add("Rafraichir maintenant", $null, { param($s, $e) $script:lastCi = "__force"; Invoke-Poll })
$menu.Items.Add("Quitter", $null, { param($s, $e) $tray.Visible = $false; [System.Windows.Forms.Application]::Exit() })
$tray.ContextMenuStrip = $menu
$tray.DoubleClick = { Start-Process "$ApiBase/" }

function Invoke-Poll {
    $state = Get-KuroState
    if (-not $state.ok) {
        [void](Ensure-Api)
        $tray.Icon = New-KuroIcon "gray"
        $tray.Text = "KuroPulse : API injoignable"
        return
    }
    $dot = switch ($state.ci) { "green" { "green" } "red" { "red" } default { "gray" } }
    $tray.Icon = New-KuroIcon $dot
    $tray.Text = "CI: $($state.ci) | cerveau: $($state.engine) | daemon: $($state.daemon) | alertes: $($state.alerts)"

    if ($script:lastCi -and $script:lastCi -ne "__force" -and $script:lastCi -ne $state.ci) {
        $kind = if ($state.ci -eq "red") { [System.Windows.Forms.ToolTipIcon]::Warning } else { [System.Windows.Forms.ToolTipIcon]::Info }
        $msg = if ($state.ci -eq "red") { "Des checks CI sont passes en rouge. Ouvre le Desk pour les details." } else { "Tous les checks sont revenus au vert." }
        $tray.BalloonTipTitle = "KuroPulse - CI $($state.ci)"
        $tray.BalloonTipText = $msg
        $tray.ShowBalloonTip(8000)
    }
    $script:lastCi = $state.ci
}

Invoke-Poll
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = $IntervalMinutes * 60 * 1000
$timer.Add_Tick({ Invoke-Poll })
$timer.Start()

[System.GC]::KeepAlive($form)
[System.Windows.Forms.Application]::Run($form)
