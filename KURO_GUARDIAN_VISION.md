# Kuro — Intelligence d'entreprise

Kuro n'est pas un outil : c'est le système nerveux de lambda-Section. Les règles
diront quoi, les composants vérifient, le portfolio expose la vérité.

## Composants (existants)

| Composant | Où | Rôle | État |
|---|---|---|---|
| **Kuro Normes** | `kuro-rules/` (ce repo) | 108 règles, AGENTS.md master, sync vers tous les repos | Actif |
| **Kuro Daemon** | `~/Documents/kuro` + `~/.kuro/kuro.db` | Surveillance locale 24/7 : sessions, alertes, mémoire (`memory_nodes`) | Actif — 22 projets, 107 sessions, 128 alertes |
| **Kuro Desk** | `dashboard/` + `run-dashboard.ps1` | GUI locale : lit kuro.db + scan repos, heatmap, règles | Actif |
| **Kuro Sentinel** | `.github/workflows/ci-guardian.yml` + `scripts/ci_guardian.py` | Veille CI remote multi-repos : rerun auto au 1er échec, issue si persistant, statut → portfolio + README profil | Actif — cron 30 min |
| **Pipeline Vérité** | `scripts/audit_truth_daily.py`, `compute_progress.py`, `generate_portfolio.py`, `generate_blog.py` | Faits git → Epingle → portfolio/blog quotidiens | Actif — cron 05:00/05:20 UTC |

## Composant à construire

### Kuro Radar — veille net & propositions
Le Sentinel regarde nos repos ; le Radar regarde dehors.

- **Sources** : HN, Reddit, GitHub Trending, arXiv, X — via R69 (Intelligence Harvester) et R75 (Desk Research)
- **Sorties** :
  - signaux pertinents par section (AI, Quant, Biohacking…)
  - propositions de **nouveaux repos** (idées validées contre les règles R2/R64)
  - solutions candidates aux blockers ouverts dans les issues `ci-guardian` / SESSION_SUMMARY
- **Cadence** : hebdo, rapport dans TRUTH_DAILY.md + Discord webhook
- **Garde-fou** : toute proposition passe le Mom Test avant d'ouvrir un repo

## Règles anti-redondance (leçons 2026-08-21)

1. **Un seul écrivain par surface** : le bloc CI du README profil appartient au
   Sentinel ; les % du README appartiennent à `generate_portfolio.sync_readme`.
   Aucun autre script n'écrit ces zones (sync_profile.py supprimé pour ça).
2. **Un seul parser Epingle** : `generate_portfolio.parse_epingle`. Tout autre
   script importe ce parser, jamais de regex maison.
3. **Nommage** : « Guardian » désigne uniquement le daemon local. Le robot CI
   s'appelle **Sentinel**. Sur les surfaces publiques (portfolio, README), on
   affiche la fonction (« Intégration continue »), jamais le nom du robot.
4. **Le portfolio expose des faits**, pas de la mécanique interne.

## Feuille de route

| Phase | Contenu | Statut |
|---|---|---|
| 0 | Normes + Sentinel + Pipeline Vérité + Daemon local | ✅ |
| 1 | Fusion Desk ↔ Daemon : le dashboard lit kuro.db en temps réel, alertes toast | À faire |
| 2 | Radar v1 : harvest hebdo + rapport signaux | À faire |
| 3 | Radar v2 : propositions de repos/solutions auto-issues | À faire |
| 4 | API Kuro (REST local) pour que tout agent IA interroge l'état de l'entreprise | À faire |

---
**Mis à jour** : 2026-08-21 — remplace KURO_GUARDIAN_VISION.md (vision initiale,
le daemon visé y existe désormais).
