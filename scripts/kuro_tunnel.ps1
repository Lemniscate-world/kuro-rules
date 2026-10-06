#Requires -Version 5.1
<#
.SYNOPSIS
    Tunnel SSH vers le dashboard Kuro du serveur (demarre, arrete, verifie).
.DESCRIPTION
    Usage :
        .\scripts\kuro_tunnel.ps1 start   # ouvre http://localhost:18767
        .\scripts\kuro_tunnel.ps1 stop    # ferme le tunnel
        .\scripts\kuro_tunnel.ps1 status  # dit si ouvert + URL a ouvrir
    Port 18767 par defaut (le 8767 local est pris par l API du PC).
    ASCII uniquement, zero dependance (OpenSSH integre a Windows).
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("start", "stop", "status")]
    [string]$Action,
    [string]$Server = "gad@192.168.1.84",
    [int]$LocalPort = 18767,
    [int]$RemotePort = 8767
)

$ErrorActionPreference = "Stop"
$PidFile = Join-Path $env:TEMP "kuro-tunnel.pid"
$Url = "http://localhost:$LocalPort/"

function Get-TunnelProcess {
    if (-not (Test-Path -LiteralPath $PidFile)) { return $null }
    $pidSaved = (Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue |
        Select-Object -First 1).Trim()
    if (-not $pidSaved) { return $null }
    $proc = Get-Process -Id $pidSaved -ErrorAction SilentlyContinue
    if ($null -eq $proc) { return $null }
    if ($proc.ProcessName -ne "ssh") { return $null }
    return $proc
}

function Test-Port {
    param([int]$Port)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $result = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $ok = $result.AsyncWaitHandle.WaitOne(1500)
        $client.Close()
        return $ok
    } catch { return $false }
}

if ($Action -eq "status") {
    $proc = Get-TunnelProcess
    if ($null -ne $proc -and (Test-Port -Port $LocalPort)) {
        Write-Output "OPEN $Url (pid $($proc.Id))"
        exit 0
    }
    Write-Output "CLOSED (lance: .\scripts\kuro_tunnel.ps1 start)"
    exit 1
}

if ($Action -eq "stop") {
    $proc = Get-TunnelProcess
    if ($null -ne $proc) {
        Stop-Process -Id $proc.Id -Force
        Write-Output "tunnel ferme (pid $($proc.Id))"
    } else {
        Write-Output "aucun tunnel a fermer"
    }
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    exit 0
}

# start
$old = Get-TunnelProcess
if ($null -ne $old) {
    Write-Output "deja ouvert : $Url (pid $($old.Id))"
    exit 0
}
if (Test-Port -Port $LocalPort) {
    Write-Output "port local $LocalPort occupe par autre chose, abandon"
    exit 1
}
$sshArgs = "-N -o BatchMode=yes -o ConnectTimeout=15 -o ExitOnForwardFailure=yes " +
    "-L ${LocalPort}:localhost:${RemotePort} $Server"
$proc = Start-Process -FilePath "ssh.exe" -ArgumentList $sshArgs `
    -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 3
if ($proc.HasExited -or !(Test-Port -Port $LocalPort)) {
    Write-Output "echec ouverture tunnel (cle SSH ? serveur joignable ?)"
    try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
    exit 1
}
$proc.Id | Set-Content -LiteralPath $PidFile -Encoding ascii -NoNewline
Write-Output "OPEN $Url"
exit 0
