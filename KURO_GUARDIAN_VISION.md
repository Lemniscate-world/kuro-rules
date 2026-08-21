# Kuro — Intelligence d'entreprise

Kuro n'est pas un outil : c'est le système nerveux de lambda-Section. Les règles
diront quoi, les composants vérifient, le portfolio expose la vérité.

## Composants (existants)

| Composant | Où | Rôle | État |
|---|---|---|---|
| **Kuro Normes** | `kuro-rules/` (ce repo) | 108 règles, AGENTS.md master, sync vers tous les repos | Actif |
| **Kuro Daemon** | `~/Documents/kuro` + `~/.kuro/kuro.db` | Surveillance locale 24/7 : sessions, alertes, mémoire (`memory_nodes`) | Actif — 22 projets, 107 sessions, 128 alertes |
| **Kuro Desk** | `dashboard/` + `run-dashboard.ps1` | GUI locale : lit kuro.db + scan repos, heatmap, règles | Actif |
| **Kuro (robot unique)** | `.github/workflows/kuro.yml` | UN workflow pour tout le cycle distant : scan CI multi-repos → vérité git → % réalistes → portfolio/mondes → blog → un commit par repo. Cron unique 05:00 UTC + déclenchement sur push d'Epingle. Scripts : `ci_guardian.py`, `audit_truth_daily.py`, `compute_progress.py`, `generate_portfolio.py`, `generate_blog.py`, `clone_repos_for_truth.py` | Actif |

Fusion du 2026-08-21 : les anciens workflows `truth-daily.yml`, `sync-portfolio.yml`
et `ci-guardian.yml` faisaient les mêmes choses en parallèle (3 robots, double cron,
collision sur `ci-status.json`). Un seul robot désormais ; le rapport design
Impeccable va dans `design-report.json` (plus de collision avec le statut CI).

## Cerveau (LLM)

Chaîne de moteurs (`scripts/kuro_llm.py`, zéro dépendance) :

| Ordre | Moteur | État |
|---|---|---|
| 1 | **Ollama cloud** — uniquement modèles `:cloud`, auto-sélection avec fallback (403 abonnement / 410 retirés sautés). Actuel : `minimax-m3:cloud` | ✅ Actif, gratuit sur le compte |
| 2 | OpenRouter `ox-alpha:free` — dormant, activable via `KURO_ENABLE_OPENROUTER=1` + `$OPENROUTER_API_KEY` | ⏸ Désactivé par défaut |

Consommateurs : Advisor du Radar (analyse signaux → projets), diagnostic IA des
issues Sentinel. Sans moteur disponible, tout reste déterministe (jamais de blocage).

**Limite connue** : le robot distant (GitHub-hosted runner) n'a pas accès au daemon
Ollama local -> il tourne en mode déterministe en CI. Pour un cerveau en CI :
self-hosted runner sur le PC, activation OpenRouter, ou API ollama.com.

## Composant à construire

### Kuro Radar — veille net & propositions
Le robot Kuro regarde nos repos ; le Radar regardera dehors.

- **Sources** : HN, Reddit, GitHub Trending, arXiv, X — via R69 (Intelligence Harvester) et R75 (Desk Research)
- **Sorties** :
  - signaux pertinents par section (AI, Quant, Biohacking…)
  - propositions de **nouveaux repos** (idées validées contre les règles R2/R64)
  - solutions candidates aux blockers ouverts dans les issues `ci-guardian` / SESSION_SUMMARY
- **Cadence** : hebdo, rapport dans TRUTH_DAILY.md + Discord webhook
- **Garde-fou** : toute proposition passe le Mom Test avant d'ouvrir un repo

## Règles anti-redondance (leçons 2026-08-21)

1. **Un seul robot distant** : tout le cycle CI/vérité/publication vit dans
   `kuro.yml`. Interdiction de créer un second workflow qui régénère une surface
   existante (leçon : 3 robots faisaient la même chose, double cron, collision
   sur `ci-status.json`).
2. **Un seul écrivain par fichier** : `ci-status.json` = santé CI ;
   `design-report.json` = rapport Impeccable ; le bloc CI du README = le robot ;
   les % du README = `generate_portfolio.sync_readme`.
3. **Un seul parser Epingle** : `generate_portfolio.parse_epingle`. Tout autre
   script importe ce parser, jamais de regex maison.
4. **Nommage** : « Guardian » désigne uniquement le daemon local. Le workflow
   distant s'appelle **Kuro**. Sur les surfaces publiques (portfolio, README),
   on affiche la fonction (« Intégration continue »), jamais le nom du robot.
5. **Le portfolio expose des faits**, pas de la mécanique interne.

## Feuille de route

| Phase | Contenu | Statut |
|---|---|---|
| 0 | Normes + robot Kuro unique + Daemon local + Desk | ✅ |
| 1 | Fusion Desk ↔ Daemon : le dashboard lit kuro.db en temps réel, alertes toast | À faire |
| 2 | Radar v1 : harvest hebdo + rapport signaux (R69/R75) | À faire |
| 3 | Radar v2 : propositions de repos/solutions auto-issues | À faire |
| 4 | API Kuro (REST local) pour que tout agent IA interroge l'état de l'entreprise | À faire |

---
**Mis à jour** : 2026-08-21 — remplace KURO_GUARDIAN_VISION.md (vision initiale,
le daemon visé y existe désormais).
