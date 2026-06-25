# Épinglé Projets — Portfolio lambda-Section

> **Dernière mise à jour** : 2026-06-25 (GitHub Action auto-sync activé)  
> **Source** : `~/Documents/kuro-rules/Epingle_Projets.md`  
> **Méthode** : Audit live — 54 projets scannés, git log + tests vérifiés (R85 + R86)

---

## ⚡ Livrables Mensuels — Ne Jamais Oublier (R90)

> Ces projets ont des engagements récurrents. Tout agent IA DOIT vérifier leur statut
> à chaque session portfolio ou session sur l'un de ces projets.
> Voir `rules/rule_90_livrables_mensuels.md`.

| Projet | Section | Livrable | Fréquence | Partie prenante |
|--------|---------|----------|-----------|-----------------|
| **OpenQuant** | λ-2 | Modèle de trading (backtest validé) | ~1 tous les 2 mois (5/an) | Interne |
| **DevDemeterDAO** | Externe | Governance report / release | Mensuel | Demeter Labs |
| **Constant_Yield** | Externe | Protocol milestone / audit | Mensuel | Demeter Labs |
| **XP_Farming_System** | Externe | Contribution tracking release | Mensuel | Demeter Labs |
| **Hermes** | λ-4 | Validation terrain update | Mensuel | Commerçants Lomé |
| **Sagittarius** | λ-9 | MLOps validation deliverable | Mensuel | Externe (B2B) |

---

## Liens

- **🌐 Portfolio Dashboard** : [lemniscate-world.github.io/Lemniscate-world](https://lemniscate-world.github.io/Lemniscate-world/) (auto-généré depuis ce fichier)
- **Liste Google Doc** : [Google Doc](https://docs.google.com/document/d/1PGyC-3tWttGNy-hpDLSWdRqEa1CKrsEAj1TkmdL7iRw/edit) (miroir manuel)
- **Organisation GitHub** : [LambdaSection](https://github.com/LambdaSection)
- **Work Calendar Team** : [Google Doc](https://docs.google.com/document/d/15kyBC9w7NM5bIHkEw5qQv7zLRulgfcyj9iIoFUVkXds/edit)

---

## λ-Section-1 — User Lambda Enter Real AI

> AI, Réseaux de Neurones

| Projet | Progression | Statut | Description |
|--------|-------------|--------|-------------|
| **NeuralDBG** | 87% | Actif | Debugger causal pour PyTorch. 309 tests (92.6% coverage), 10 bugs catalogués, 3 PRs upstream (BUG-002 varlen_attn, BUG-006 svdvals, BUG-008 normalize). PR Gate system déployé (6 gates). v1.3.2 sur PyPI. Engine 45 tests. Neural-Agent pipeline CPU validé. Merge rate upstream: 0% — objectif: 1ère PR mergée. |
| **NeuralDBG-Engine** | 80% | Actif | Moteur causal propriétaire. v1.0.0 packagé (GitHub Packages). 45 tests (API contract, gradient, activation, data, coupling, full pipeline). Drop-in upgrade pour NeuralDBG. |
| **Neural-Agent** | 15% | Actif | Agent auto-correcteur pour entraînement RN. 87 tests, pipeline CPU validé (tiny-gpt2 + LoRA, 5 steps). Règle MHA wired. Modèle pas encore entraîné (Kaggle notebook prêt). Boucle fermée : NeuralDBG → Diagnostic → Fix. |
| **Aladin** | 40% | Actif | Architecture Transformer & recherche LLM. |
| **Astral** | 15% | Actif | Multi-repo intelligence avec client Hindsight. Data Gravity moat implémenté, Next.js MVP. |
| **DataLint** | 15% | Actif | Gouvernance kuro-rules + validation ML. 4 tests. Alignement sync-rules.ps1 avec projects.txt, workspace audit. R105 (Multi-Repo) + R87 (Ownership) déployées. 54 projets scannés. |
| **Odin** | 10% | Actif | Fork/customisation d'Open Interpreter — exécution locale de code (Python, JS, Shell) via LLM. 1 test. Dernier merge upstream: PR #1686. |
| **NeuroDose** | 5% | Actif | Cognitive Supplement Tracker & Visualizer. Optimisation santé cognitive via modélisation pharmacocinétique. |
| **Aquarium** | 5% | Prototypage | IDE visuel (Tauri) pour NeuralDBG. MVP livré, dormant. Export JSON + 14 tests Aquarium. |
| **Damon** | 0% | Nouveau | OS Amélioré basé sur Arch Linux. |
| **Metatron** | 0% | Prototypage | Multi-language debugger with abductive reasoning. Motto : « Buy time ». |
| **TokenWise** | 0% | Prototypage | Analyse et réduction du coût par tokens utilisés. Phase validation Mom Test. |
| **Prompt2Model** | 0% | Validation | Génération automatique de modèles ML à partir de descriptions textuelles. Phase validation Mom Test. |
| **Automatons** | 0% | Prototypage | Agent orchestration and automation framework. |
| **Onlook** | 0% | Prototypage | Visual monitoring / observability tool. |
| **Verbose** | 0% | Prototypage | Logging / communication tool. |
| Vault | — | Outil | Base de connaissances personnelle (Obsidian). |
| Neural-Again | 10% | Archive | DSL pour réseaux de neurones. Obsolète, remplacé par Keras/PyTorch + code gen. |
| Neural-Research | 5% | Archive | Recherches avancées sur les architectures neuronales. |
| NeuralDSL | 0% | Archive | Domain Specific Language for neural networks. |
| NeuralPaper | 0% | Archive | Drafts and research for neural network papers. |

---

## λ-Section-2 — Quant-Search

> Trading Algorithmique, Modélisation Mathématique de Marchés

| Projet | Progression | Statut | Description |
|--------|-------------|--------|-------------|
| **OpenQuant** | 15% | Actif | Trading quantitatif avec MiroFish (swarm LLM). 17 fichiers de test, backtest CL/F -10.96%, NewsAPI intégré. Robot autonome livré (Avril 2026). |
| Console | 0% | Prototypage | Environnement de développement d'outils de trading quantitatifs et algorithmiques. |

**Objectif 2026 — 5 modèles/an :**
1. Transformer Probabiliste pour Prédiction de Prix
2. Machine Learning pour prédiction des prix d'actifs
3. Modèle de Markov pour détection de changements de régimes

---

## λ-Section-3 — Hackin Life

> Biohacking, Nootropiques, Sport, Discipline par Biologie

| Projet | Progression | Statut | Description |
|--------|-------------|--------|-------------|
| **EchoX** | 65% | Actif | SRS avec forgetting curves (PyQt6). Validation L1 complète ($23.9B marché), GUI desktop opérationnelle. 6 tests. Structure Tauri initialisée. |
| **Flow-Regulator** | 5% | Actif | Environnement de productivité premium avec Pomodoro adaptatif, binaural beats, contrôle Philips Hue et focus mode. |
| Charmed | 5% | Pivot | Projet réveil Spotify ARRÊTÉ (viabilité remise en cause). Phase recherche nouveau problème. |
| Thanatos | 0% | Prototypage | Application mobile mixant entraînements arts martiaux et callisthénie. |
| **LifeTrack** | 15% | Actif | Desktop habit tracker (Tauri v2 + React + TypeScript + Vite). Grille mensuelle, pastel UI, objectifs configurables. Natif Windows via WebView2. |

> **Note** : NeuroDose est listé dans λ-Section-1 (AI). Son axe biohacking est couvert par le même projet.

---

## λ-Section-4 — G&S Solutions

> Fintech

| Projet | Progression | Statut | Description |
|--------|-------------|--------|-------------|
| **Hermes** | 12% | Validation | Outil de coordination des livraisons pour commerçants du Grand Lomé, Togo. Landing page + pipeline automation (R84). Branch: validation/landing-deploy. |
| G&S Solutions | 6% | Actif | Fintech en phase de mindmapping. |
| Iroko | 0% | Prototypage | Fintech. |
| Kapok | 0% | Prototypage | Insurtech. |
| SOGEXCO | 0% | Prototypage | Accounting/Business solution pour client SOGEXCO. |
| **Epure** | 20% | Actif | Cabinet d'Ingénierie Hybride IA (Togo, West Africa). Services de conception augmentés par IA. Frontend + backend + CAD service + Electron. Stack: React, TypeScript, Python, FreeCAD. |

---

## λ-Section-5 — Eclipse

> Ingénierie Informatique Aérospatiale

| Projet | Progression | Statut | Description |
|--------|-------------|--------|-------------|
| Bad Bunny | 0% | Prototypage | Bibliothèque pour simulation de propulseurs de fusées en Rust. |

---

## λ-Section-6 — Paranoid

> Développement de jeux vidéo expérimentaux

*(En cours de définition)*

---

## λ-Section-7 — Helium Chain

> Blockchain, Crypto, Finance Décentralisée

| Projet | Progression | Statut | Description |
|--------|-------------|--------|-------------|
| **Helium** | 28% | Actif | Blockchain Rust avec 4 crates (libp2p, WireGuard, Firecracker). Architecture MVP complète, POC scripts prêts. Recherches stratégiques intégrées. |
| POFS | 0% | Prototypage | Proof of Stake / File System research. |

---

## λ-Section-8 — AI8 (Algorithmic Intelligence 8)

> Algorithmes, Structures de Données

| Projet | Progression | Statut | Description |
|--------|-------------|--------|-------------|
| **Dissect** | 10% | Actif | Outil d'audit et de visualisation de l'orchestration des agents IA. 9 tests, branch: main. |
| BloomDB | 5% | Prototypage | Base de données pour stockage et gestion de données probabilistes. |
| Algoritmi | 0% | Prototypage | Dérivé de Dissect, centré sur la visualisation des algorithmes. |

---

## λ-Section-9 — Network Euler

> Gestion d'entreprise, Automatisations, DevOps

| Projet | Progression | Statut | Description |
|--------|-------------|--------|-------------|
| **Sagittarius** | 20% | Validation | MLOps & AI Agent Assistant for DevOps. Validation L2 complète (40 jobs scrapés, burnout 60%). Branch active: Jacques-Gad-Sagittarius. |
| **KuroGuardian** | 8% | Actif | Daemon MVP fonctionnel (Python + watchdog + SQLite). Surveillance 24/7 SESSION_SUMMARY.md, parser auto, alertes inactivité, 21 projets indexés. Branch: master, commit récent: project health alerting. |
| lambda-ESN | 0% | Prototypage | Réseau social d'entreprise privé, Slack personnalisé. |

---

## λ-Section-10 — QuSolve

> Recherches et Applications en Mécanique Quantique

- Étude de systèmes non hermitiens.

---

## λ-Section-11 — SaaS X

> Création Automatisée et Rapide avec Gestion de SaaS

| Projet | Progression | Statut | Description |
|--------|-------------|--------|-------------|
| SaasX | 0% | Recherche | Recherches et implémentations en cours. |

---

## λ-Section-12 — Hypatia

> Recherches Avancées en Physique & Mathématiques

| Projet | Progression | Statut | Description |
|--------|-------------|--------|-------------|
| **AEther** | 7% | Actif | Minkowski Space-Time Visualizer, orienté exploration d'autres espaces-temps. 1 test. Branch: feat/setup-kuro-rules. |
| Logical Calculus | 0% | Recherche | Nouveau système de calcul infinitésimal basé sur la logique et le calcul de Newton. Formalisation en cours. |
| Math. Theorization of Linguistics | 0% | Recherche | Mathématisation du langage par théorie de Shannon, espaces de probabilités linguistiques. |
| Project-Dirac | 0% | Prototypage | Physics-inspired computational model. |

---

## λ-Section-13 — Dexter.pwn

> Hacking Éthique, CTFs, Découverte de Failles Zero Day

| Projet | Progression | Statut | Description |
|--------|-------------|--------|-------------|
| Sybil | 0% | Recherche | Exploration des failles de réseaux de neurones. |

---

## λ-Section-14 — Charles

> BeatMaking, Art, Poésie, NFTs, Expériences Audio-Visuelles

| Projet | Progression | Statut | Description |
|--------|-------------|--------|-------------|
| **OpenMind** | 15% | Actif | Application de journaling Windows (WinUI 3) avec analyse IA via Ollama, exports multiples et packaging MSIX. |
| Audio Room Visualizer | 0% | Prototypage | Visualiser la musique dans l'espace, en 3D/2D/projections. |
| Interpoem | 0% | Prototypage | Plateforme d'immersion du lecteur dans un poème (musique, 3D, VR, art digital). |
| Charles | 0% | Prototypage | Production musicale par code et électronique avancée (SuperCollider, plugins FL Studio). |
| Journaux | 0% | Archive | Archive of personal journaling / log system. |

---

## λ-Section-15 — XCAD

> CAD, Génie Civil et Électromécanique

| Projet | Progression | Statut | Description |
|--------|-------------|--------|-------------|
| Epure | 0% | Prototypage | — |
| Mori | 0% | Prototypage | Architecture biomimétique. |

---

## Projets Tiers / Externes (Non-Propriétaire)

| Projet | Progression | Statut | Description |
|--------|-------------|--------|-------------|
| **DevDemeterDAO** | 35% | Actif | Governance framework pour Demeter Labs. Sécurité hardened (EOA→multisig, VeVotingPowerCondition). |
| **XP_Farming_System** | 20% | Actif | Gamified contribution tracking pour Demeter Labs. |
| **Constant_Yield** | 18% | Actif | DeFi protocol pour Demeter Labs. Audit sécurité et ModularYieldTokenizer en cours. |
| Nwt | — | Externe | nw_wrld Modules Workspace (Third-party). |

---

## Projets en Réflexion

- Semantica · Robust Lambda · Mathematical Spaces Study · CodeBase As Math
- Intelligent Autonomous Laboratory (IAL) — Domotique
- Embeddings Visualizer · Spotipom · Open-Source Heptabase · Logos
- Urge Surfing App · SERVERIA (Hyper Evolutive Connected Server)
- Open-Source AI Accounting · Fo Nu NLP · Level Up Habit Tracking
- Startup : Agriculture (Togo/Afrique)
- Startup : Transports
- Startup : Personnes à faible agency
- Startup : Recherche scientifique / papiers de recherche
- Startup : Protection contre IA défaillantes (Police IA)
- YC Startups Requests
- BioX