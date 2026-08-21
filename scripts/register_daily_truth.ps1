# register_daily_truth.ps1 — Enregistre une tache planifiee Windows qui tourne chaque jour 06:00
# et qui genere le rapport truth + portfolio factuel.

$TaskName = "lambda-Section-Truth-Daily"
$ScriptPath = "$HOME\Documents\kuro-rules\scripts\audit_truth_daily.py"
$Python = "python"
$Arguments = "`"$ScriptPath`" --dry-run"
$WorkingDir = "$HOME\Documents\kuro-rules"

# Verifie que le script existe
if (-not (Test-Path $ScriptPath)) {
    Write-Error "Script not found: $ScriptPath"
    exit 1
}

$Action = New-ScheduledTaskAction -Execute $Python -Argument $Arguments -WorkingDirectory $WorkingDir
$Trigger = New-ScheduledTaskTrigger -Daily -At 06:00
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Highest

try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force | Out-Null
    Write-Host "Tache planifiee '$TaskName' enregistree: quotidienne 06:00 -> $Python $Arguments"
    Write-Host "Verifie: Get-ScheduledTask -TaskName $TaskName"
    Write-Host "Lance manuellement: Start-ScheduledTask -TaskName $TaskName"
    Write-Host "Logs: $HOME\Documents\kuro-rules\TRUTH_DAILY.md + Lemniscate-world\index.html"
} catch {
    Write-Error "Echec enregistrement: $_"
    Write-Host "Alternative manuelle: Task Scheduler -> Create Task -> Trigger Daily 06:00 -> Action: $Python $Arguments"
}
