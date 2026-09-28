# run_daily.ps1 -- Tache quotidienne Kuro : drafts + posts X full-auto (R94-v2).
# Charge .env en memoire process uniquement (jamais affiche), puis post_policy --apply.
# Appele par le Planificateur Windows (tache KuroXDaily, 20:00). Zero dependance.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $root ".env"
if (Test-Path -LiteralPath $envFile) {
    Get-Content -LiteralPath $envFile | ForEach-Object {
        $line = $_.Trim()
        if (($line -eq "") -or $line.StartsWith("#") -or (-not $line.Contains("="))) { return }
        $k, $v = $line -split "=", 2
        [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim(), "Process")
    }
}
& python (Join-Path $root "scripts\post_policy.py") --apply --top 5 --annex Helium --discord --via buffer
exit $LASTEXITCODE
