# kuro_watchdog_win.ps1 - external check of the Linux OpenClaw server
# Runs every 15 min via Scheduled Task. No accents (R93 cross-platform).
# Checks: ping + TCP 22 + SSH gateway probe. Logs to logs/kuro-watchdog-win.log
param(
  [string]$Server = "192.168.1.84",
  [string]$LogFile = (Join-Path $PSScriptRoot "..\logs\kuro-watchdog-win.log")
)
$ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$pingOk = $false
try {
  $p = Start-Process -FilePath "ping.exe" -ArgumentList @("-n","1","-w","1000",$Server) -NoNewWindow -Wait -PassThru
  $pingOk = ($p.ExitCode -eq 0)
} catch { $pingOk = $false }

$tcpOk = $false
try {
  $c = New-Object System.Net.Sockets.TcpClient
  $r = $c.BeginConnect($Server, 22, $null, $null)
  $tcpOk = $r.AsyncWaitHandle.WaitOne(2000)
  $c.Close()
} catch { $tcpOk = $false }

$gwOk = $false
$gwOut = ""
if ($tcpOk) {
  try {
    $gwOut = & ssh -o ConnectTimeout=8 -o BatchMode=yes "gad@$Server" "openclaw gateway probe" 2>&1 | Out-String
    $gwOk = ($gwOut -match "Connect:\s*ok" -or $gwOut -match "Reachable:\s*yes")
  } catch { $gwOk = $false }
}

$line = "$ts | ping=$pingOk tcp22=$tcpOk gateway=$gwOk"
Add-Content -LiteralPath $LogFile -Value $line -Encoding utf8
if (-not ($pingOk -and $gwOk)) {
  Add-Content -LiteralPath $LogFile -Value "$ts | ALERT server or gateway down (see above)" -Encoding utf8
  exit 1
}
exit 0
