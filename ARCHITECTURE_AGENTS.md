# Architecture agents — OpenClaw / OpenCMO / Kuro (référence durable)

> Mis à jour : 2026-09-28. Source de vérité vérifiée en direct sur gad@192.168.1.84.
> Règle d'or : **OpenClaw CHERCHE, DRAFTE et DIFFUSE (auto), Kuro PROTÈGE.**
> OpenCMO archivé le 2026-09-28 (Epingle) : ses features (audit SEO/GEO, stratégie)
> sont reprises par le cron serveur `strategy-monthly`. Dossier local conservé, sans remote.
> Jamais de double-post : un seul émetteur par canal (voir §4).

## 1. Les trois systèmes et leurs liens

```
                        +------------------+
                        |     OpenCMO      |  STRATÈGE (cerveau marketing maison)
                        |  FastAPI + PG    |  - analyse site + repo
                        |  (frontend TBD)  |  - propose SEO/GEO/contenus
                        +--------+---------+  - humain valide AVANT action (audit log)
                                 | décide QUOI dire
                                 v
+------------------+   +------------------+   +------------------+
|       KURO       |<->|     OPENCLAW     |<->|  CANAUX / LEADS  |
|  GARDE-FOUS      |   |  OPÉRATEUR 24/7  |   |  WhatsApp (live) |
|  (Windows, local)|   |  (serveur Linux) |   |  Discord (à bran)|
+------------------+   +------------------+   +------------------+
| scripts/*.py     |   | gateway :18789   |   | X via Buffer     |
| post_policy      |   | agents (ci-dessous)| | Reddit/Discord   |
| post_brain       |   | crons (ci-dessous)|  |                  |
| R94/R96/R99/R110 |   | ~/repos (clones) |   |                  |
| Epingle/tracker  |   | ~/leads/*.md     |   |                  |
+------------------+   +------------------+   +------------------+
  Fichiers partagés = contrat : Epingle_Projets.md, acquisition_tracker.md,
  TRUTH_DAILY.md, leads.local.json, ~/leads/PRODUCTS.md
```

- **OpenCMO** ne poste jamais, n'écrit jamais dans les repos : il propose, l'humain valide.
- **OpenClaw** ne publie jamais en public en direct : il drafte et notifie (WhatsApp DM opérateur).
  La publication passe par les pipelines Kuro existants (post_policy, Buffer, webhooks).
- **Kuro** (scripts + règles) reste l'autorité : gates, anti-leak (R94 §1, stratégies par projet),
  logging R99 sous 5 min, données 100 % locales (R111).

## 2. Tout ce que fait OpenClaw (état live 2026-09-28)

Serveur : OpenClaw 2026.9.6 stable, Node 24.21, systemd actif, gateway loopback :18789.
Cerveau : deepseek-v4-pro (main), deepseek-flash (tâches routinières). Réalité proxy 2026-10-09 : clé DeepSeek HS donc les 2 alias servent groq `gpt-oss-120b` (2 s/réponse testé) + 11 fallbacks derrière. Flash n'est donc PAS un modèle distinct moins cher.
Clé Ollama cloud épuisée (402) : ne plus compter dessus sans crédits.
Clé DeepSeek HS depuis 2026-10-09 (401 `Authentication Fails` sur `/user/balance`). Alias basculés sur groq, backup serveur `litellm-config.yaml.bak-20261009-deepseek-dead`. Restauration après rachat : recopier les 3 blocs depuis le `.bak` + `systemctl --user restart litellm-proxy`.
2026-10-11 : têtes `deepseek-v4-pro` + `deepseek-flash` basculées groq→gemini/gemini-3.8-flash (groq 150-600s + `tool_use_failed` sur flash ; gemini vérifié 28s/9,5s). Backup retour : `~/.openclaw/litellm-config.yaml.bak-20261011-flash-gemini`.

### Agents
| Agent | Modèle | Workspace | Rôle effectif |
|---|---|---|---|
| main (défaut, identité Kuro) | deepseek-v4-pro | ~/.openclaw/workspace | Dialogue WhatsApp, code mobile (exec), pilotage |
| leads-radar | deepseek-flash | ~/kuro-rules (clone) | Recherche + drafts, agit via crons uniquement (aucun binding chat) |

### Automations (cron)
| Job | Horaire | Cible | Livraison |
|---|---|---|---|
| leads-radar-daily | 07:00 Europe/Paris | digest veille ML/quant (HN/Reddit/GitHub/arXiv) | WhatsApp opérateur (vérifié : delivered) |
| prospects-daily | 08:00 lun-ven Europe/Paris | prospection 3 cibles + BROUILLONS seuls (envoi auto révoqué 2026-10-11, validation humaine obligatoire) — ÉTAPE 0 inbox IMAP obligatoire depuis 2026-10-08 | WhatsApp opérateur |
| replies-watch | 12:00 + 18:00 7j/7 Europe/Paris (lun-ven avant 2026-10-11 → angle mort week-end : 2 replies manquées 10-11/10, Panos + stop Kristjan) | garde inbox : détecte les `Re:` non traités, statut + suivi auto (créé 2026-10-08 après incident 4 replies sans suivi 29/09→03/10) | WhatsApp opérateur si nouvelle reply, sinon NO_REPLY |
| repos-refresh-monthly | le 1er, 08:00 | pull + commits/28j par repo, propose ajouts/retraits | WhatsApp opérateur |
| heartbeat (main) | toutes les 30 min | présence/relances — réveille la session directe main, répond WhatsApp si relance utile sinon NO_REPLY/skip (skip auto si run en cours) | job système non désactivable via cron ; incident 2026-10-09 : contexte 72k + DeepSeek lent 8-10 min = salad multilingue spammé → fix = compactage session + alias vers groq. 2026-10-10 : 2 timeouts 600s côté gateway (proxy jamais touché, groq 1 s en direct) + 1 envoi WhatsApp post-timeout 09:03 → restart gateway, test pong OK 63 s. 2026-10-11 : session main 67k → stall 599s + 6x timeouts WhatsApp + salad multilingue (pattern 09/10) → truncate 200 lignes + têtes v4-pro/flash vers gemini (pong 28s/9,5s OK). `timeoutSeconds` volontairement inchangé (600s défaut). |
| memory dreaming | 03:00 | consolidation mémoire | interne |

### Canaux
| Canal | État | Politique |
|---|---|---|
| WhatsApp | lié, sain, DM allowlist = seul numéro opérateur (22870782358) | DMs : allowlist stricte. Groupes : mention uniquement (défaut). L'agent parle AVEC votre numéro (appareil lié) |
| Discord | plugin chargé, **compte non configuré** | Reste : `openclaw channels add` guidé (TTY) + Message Content Intent au portail |

### Repos sur serveur (~/repos, lecture seule, règle = top vélocité)
Horcruxe-Labs, LifeTrack, NeuralDBG (+ ~/kuro-rules clone complet).
Non clonables sans auth : OpenQuant, forma (privés). Oblivion (aucun remote local).

### Capacités activées (plugins officiels uniquement, zéro skill ClawHub)
Exécution shell (exec), lecture/écriture fichiers, browser automation, web search/fetch
(Tavily dispo), mémoire persistante, Canvas/médias, voix, 40+ providers modèles configurables
(OpenRouter présent mais sans clé ; DeepSeek actif).

## 3. Automation progressive (politique 2026-10-01, décision utilisateur)

### Niveau 1 — ACTIF (safe, via pipelines Kuro existants)
- Posts publics via `post_policy --apply` + Buffer (gates R94-v2 inchangés : lint, dedupe, sanitization, thread auto).
- Push Git sur branches `openclaw/*` + PR auto + **merge humain obligatoire** (jamais de push direct sur main/master).
- Dépôt prioritaire : Helium (soft-launch + Show HN).

### Niveau 2 — SUSPENDU 2026-10-11 (drafts seuls, envoi = validation humaine)
- Envois mails auto RÉVOQUÉS le 2026-10-11 (révocation du full-auto du 2026-09-28) : leads-radar = brouillons + statuts uniquement, envoi sur ordre humain explicite après relecture. Cause : modèle dégradé depuis DeepSeek down 09/10 (salad multilingue 09/10 18h, angle mort week-end 10-11/10, "no web-access tool" intermittent).
- Règle inbox-first (durcie 2026-10-08 après 4 replies sans suivi 29/09→03/10) : aucun premier mail ni relance J+7 sans lecture IMAP préalable (`~/.openclaw/gmail.env`, select readonly, croisé avec `~/leads/SENT.md`). Statuts `repondu/stop/lost/suivi-envoye` = jamais relancés. Procédure dans `~/leads/GMAIL.md`.
- Réponses auto aux commentaires (HN/Reddit/Discord) : templates R95/R96 uniquement,
  max 1 réponse/thread sans validation, escalade WhatsApp opérateur si question hors template.
- DMs UNIQUEMENT en suivi opt-in (personne ayant commenté/DM en premier, ou inscrite waitlist).
  Jamais de cold DM : risque ban plateformes.

### Niveau 3 — INTERDIT (maintenu)
- Cold DMs commerciaux non sollicités.
- Push direct sur main/master.
- Skills communautaires sans audit (ClawHavoc/AMOS actif — R38 : CodeQL/Sonar verts exigés, un par un).
- Post avec lien sortant sans thread/reply (anti-déclassement algo R94-v2).
- Pas de données finance/santé hors salons privés (R111, stratégies anti-leak R94).

## 4. Qui émet où (anti doublon)
| Canal | Émetteur unique | Via |
|---|---|---|
| WhatsApp opérateur | OpenClaw (digests, rapports) | cron -> announce explicite |
| WhatsApp dialogue | main (réponses DM) | allowlist |
| X | post_policy/Buffer | OpenClaw poste auto (Niveau 1), gates inchangées |
| Discord salons | kuro_automate webhooks / kuro_bot | bot `!` après intent ON |
| Reddit/communautés | OpenClaw (posts via pipeline + réponses templates R96, max 1/thread) | posts initiaux relus 1x puis auto |

## 5. Commandes de contrôle (depuis Windows, sans secret affiché)
```
ssh gad@192.168.1.84 "openclaw gateway probe"          # gateway UP ?
ssh gad@192.168.1.84 "openclaw cron list"              # jobs + statuts
ssh gad@192.168.1.84 "openclaw agents list"            # agents + modèles
ssh gad@192.168.1.84 "openclaw channels status --probe" # canaux vivants ?
ssh gad@192.168.1.84 "openclaw agent --agent main -m '...'"  # ordre direct
```

## 6. Reste à faire (dans l'ordre)
1. `openclaw channels add` guidé (TTY Termius) + Message Content Intent portail.
2. PAT GitHub fin (Termius) — REQUIS maintenant (PRs auto `openclaw/*` Niveau 1).
3. Définir 1 offre vendable (reco : accès beta NeuralDBG) + capture S1.
4. Merge PR #6 kuro-rules (verte 12/12) quand revue humaine OK.
