# Structure des fichiers de planification — NeuralDBG

Pour éviter toute confusion, voici à quoi sert chaque fichier :

## À la racine

| Fichier | Contenu | Quand le lire |
|---|---|---|
| **PLAN.md** | Roadmap produit : phases 1 à 10, statut de chaque feature, vision écosystème | Avant chaque session pour savoir où on en est |
| **decision-memo.md** | Décision marché : L0→L4, wedge, buyer hypothesis, validation ladder | Avant chaque décision produit/marché |
| **CHANGELOG.md** | Historique des versions : features ajoutées, bugs fixés par version | Pour savoir ce qui a été livré |
| **LAUNCH_POSTS.md** | Contenu des posts : Show HN, X thread, Reddit, Discord, réponses types | Le jour du lancement |
| **SESSION_SUMMARY.md** | Résumé de session : ce qui a été fait, ce qui reste | Créé/mis à jour à chaque session |

## Dans docs/

| Fichier | Contenu | Quand le lire |
|---|---|---|
| **docs/launch_plan_neuraldbg.md** | Planning temporel : J-7 à J+30, check-list minute par minute | Avant et pendant le lancement |
| **docs/hn_feedback_log.md** | Log des retours HN après lancement | Après le Show HN |
| **docs/community_post_template.md** | Templates pour Reddit, Discord, X | Pendant l'amplification |
| **docs/launch_postmortem.md** | Analyse post-lancement (succès ou échec) | J+30 |
| **docs/verification_report_1.3.0_2026-05-18.md** | Rapport R98 : tests fonctionnels avant lancement | Avant le lancement (preuve) |
| **docs/desk_research_report.md** | Recherche desk (personas, compétiteurs, TAM, risques, gaps) | Pour comprendre le marché |
| **docs/failure_mode_table.md** | Tableau des risques techniques | Pour la maintenance |

## Dans scripts/

| Fichier | Contenu |
|---|---|
| **scripts/verify_neuraldbg.py** | Script de vérification R98 — test fonctionnel complet |

## Règle simple

- **PLAN.md** = "Quoi construire ?" (phases, features)
- **docs/launch_plan_neuraldbg.md** = "Quand et comment lancer ?" (timeline, actions)
- **decision-memo.md** = "Pourquoi et pour qui ?" (marché, wedge)
- **CHANGELOG.md** = "Qu'est-ce qui a été livré ?" (historique)