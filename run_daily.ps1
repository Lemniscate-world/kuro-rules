# run_daily.ps1 -- Tache quotidienne Kuro : drafts + REVUE GLOBALE + posts X full-auto (R94-v2).
# Pipeline UNIQUE (R125 : helium-daily.ps1 déprécié, Helium via --annex).
# Charge .env en memoire process uniquement (jamais affiche), puis :
#   1. post_brain review-all --rewrite (raisonnement global : tous les drafts
#      du jour notés avec contexte partagé — recents + leçons + muselés) ;
#   2. post_policy --apply (gates + dedupe + posting Buffer/X + Discord).
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
& python (Join-Path $root "scripts\post_brain.py") review-all --rewrite
& python (Join-Path $root "scripts\post_policy.py") --apply --top 5 --annex Helium --discord --via buffer
exit $LASTEXITCODE
