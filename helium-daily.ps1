# DEPRECATED (2026-10-19, R125) — pipeline X unifié dans run_daily.ps1.
# L'annexe Helium est déjà couverte par KuroXDaily (20:00) via
#   post_policy.py --apply --top 5 --annex Helium
# Cette tâche HeliumMarketing (09:00) ne faisait qu'un DRY-RUN redondant.
# Stub sûr : journalise la dépréciation et sort (0) — une tâche stale ne
# doit pas planter, mais ne doit plus rien faire non plus.
Set-Location "C:\Users\Utilisateur\Documents\kuro-rules"
"=== $(Get-Date -Format 'yyyy-MM-dd HH:mm') === [DEPRECATED] helium-daily.ps1 remplacé par KuroXDaily (run_daily.ps1 --annex Helium). Rien à faire ici." |
    Out-File outputs/helium-auto.log -Append -Encoding utf8
exit 0
