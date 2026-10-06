# HeliumMarketing daily runner — drafts + policy decision, no human needed.
# Scheduled via Windows Task Scheduler (daily 09:00). Appends to outputs/helium-auto.log
Set-Location "C:\Users\Utilisateur\Documents\kuro-rules"
"=== $(Get-Date -Format 'yyyy-MM-dd HH:mm') ===" | Out-File outputs/helium-auto.log -Append -Encoding utf8
python scripts/gen_x_posts.py --apply --only Helium 2>&1 | Out-File outputs/helium-auto.log -Append -Encoding utf8
python scripts/post_policy.py --dry-run --top 5 --annex Helium 2>&1 | Out-File outputs/helium-auto.log -Append -Encoding utf8
