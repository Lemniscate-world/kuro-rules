# Kuro Guardian — Agent de Gestion de Projet Autonome 24/7

## Vision

Un agent IA autonome qui vit 24h/24h sur ton PC (Windows/Linux) pour :
- **Surveiller** tous les projets lambda-Section
- **Rappeler** les échéances, tâches, et validations en attente
- **Analyser** l'activité Git et les SESSION_SUMMARY pour détecter la progression
- **Générer** des rapports quotidiens/hebdomadaires
- **Prévenir** avant qu'un projet ne soit oublié ou ne dérive

## Architecture Technique

### Core Components

#### 1. Guardian Daemon (Rust/Python)
```
Processus resident 24/7 (service Windows / systemd Linux)
- Surveillance fichier: ~/Documents/*/SESSION_SUMMARY.md
- Git hooks: commits, branches, merges
- Timers: rappels échéances PLAN.md
```

#### 2. SQLite Database (Local)
```sql
projects (id, name, path, last_activity, progress_pct, status)
sessions (id, project_id, date, summary, progress_delta, editor)
reminders (id, project_id, message, trigger_date, priority)
activity_log (timestamp, event_type, project, details)
```

#### 3. GUI Dashboard (Tauri/React ou PyQt6)
- **Vue d'ensemble**: tous les projets, heatmap d'activité
- **Timeline**: commits et sessions par projet
- **Alertes**: projets inactifs > 7 jours, validations en retard
- **Stats**: nombre de sessions/semaine, progression moyenne
- **Actions**: générer SESSION_SUMMARY, rappel validation

#### 4. Notification System
- Windows: Toast notifications, system tray
- Linux: notify-send, indicator applet
- Sons: différents pour alertes critiques vs rappels

### Features MVP

#### Phase 1: Surveillance (Semaine 1-2)
- [ ] Scanner tous les repos ~/Documents toutes les heures
- [ ] Détecter nouveaux commits et SESSION_SUMMARY.md
- [ ] Parser SESSION_SUMMARY pour extraire:
  - Progress %
  - Éditeur (Windsurf, Cursor, etc.)
  - Tests pass/fail
  - Blockers
  - Prochaines étapes

#### Phase 2: Intelligence (Semaine 3-4)
- [ ] Détecter projets "orphelins" (pas de commit depuis 14 jours)
- [ ] Comparer Epingle_Projets.md vs activité réelle
- [ ] Alerte si écart > 20% entre déclaré et réel
- [ ] Rappel automatique des validations Mom Test en attente

#### Phase 3: Action (Semaine 5-6)
- [ ] Générer rapport hebdo: "Kuro Weekly Digest"
- [ ] Proposer agenda: "Projet X nécessite attention"
- [ ] Créer rappels calendrier (Outlook/Google)
- [ ] Suggérer prochaine tâche basée sur PLAN.md

#### Phase 4: Intégration (Semaine 7-8)
- [ ] API Linear: sync tâches et issues
- [ ] Webhook Discord: notifications channel #kuro-guardian
- [ ] Export CSV: stats pour analyse mensuelle

### Tech Stack Options

#### Option A: Rust + Tauri (Recommandé)
- **Daemon**: Rust + tokio + notify (file watching)
- **GUI**: Tauri + React + Tailwind
- **DB**: SQLite via sqlx
- **Avantage**: Performance, binaire natif, moderne

#### Option B: Python + PyQt6
- **Daemon**: Python + watchdog + schedule
- **GUI**: PyQt6 + matplotlib
- **DB**: SQLite via sqlite3
- **Avantage**: Prototypage rapide, EchoX déjà en PyQt6

#### Option C: Node.js + Electron
- **Daemon**: Node + chokidar + node-cron
- **GUI**: Electron + React
- **DB**: SQLite better-sqlite3
- **Avantage**: Web tech, facile à déployer

### Integration avec lambda-Section

#### R86: Kuro Guardian Protocol (Future Rule)
```
- Tout projet actif DOIT avoir un SESSION_SUMMARY < 7 jours
- Tout projet en validation DOIT avoir une landing page < 14 jours
- Guardian NOTIFIE si délais dépassés
- Guardian SUGGÈRE prochaines étapes basées sur PLAN.md
```

#### Data Sources
```
~/Documents/*/SESSION_SUMMARY.md  →  Activity + Progress
~/Documents/*/PLAN.md             →  Milestones + Deadlines
~/Documents/*/decision.md         →  Validation status
~/Documents/kuro-rules/Epingle_Projets.md  →  Portfolio truth
~/.git/*/logs/HEAD                →  Commit activity
```

### GUI Mockup

```
┌─────────────────────────────────────────────────────────┐
│  KURO GUARDIAN                                    [__]  │
├─────────────────────────────────────────────────────────┤
│  📊 OVERVIEW                    [Daily] [Weekly] [All]  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ 37 Projects │  │ 12 Active   │  │ 3 Alerts    │       │
│  │    Total    │  │  This Week  │  │  Attention  │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
├─────────────────────────────────────────────────────────┤
│  🚨 ALERTS (3)                                          │
│  • Charmed: 0 commits since 2026-02-27 (PIVOT ongoing)  │
│  • Dissect: Mom Test Gate blocking progress             │
│  • Hermes: Landing page deployment pending              │
├─────────────────────────────────────────────────────────┤
│  📈 ACTIVITY HEATMAP (Last 30 days)                     │
│      NeuralDBG ████████████████████  12 sessions      │
│      EchoX     ███████████████████░  10 sessions      │
│      OpenQuant ██████████████░░░░░░░   8 sessions      │
│      Helium    ██████████░░░░░░░░░░░   6 sessions      │
│      ...                                                │
├─────────────────────────────────────────────────────────┤
│  📋 UPCOMING MILESTONES                                 │
│  • EchoX: L3 Pilot-Ready (2026-05-15)                  │
│  • NeuralDBG: Beta Release (2026-05-20)                │
│  • Hermes: 20+ validation responses (2026-05-10)       │
└─────────────────────────────────────────────────────────┘
```

### Deployment

#### Windows (Primary)
```powershell
# Service Windows
sc create KuroGuardian binPath= "C:\KuroGuardian\daemon.exe"
sc start KuroGuardian

# GUI Autostart
shell:startup\KuroGuardian.lnk
```

#### Linux (Secondary)
```bash
# Systemd service
sudo systemctl enable kuro-guardian
sudo systemctl start kuro-guardian

# GUI Indicator
# ~/.config/autostart/kuro-guardian.desktop
```

### Future Enhancements

#### v2.0: AI Agent Integration
- Utiliser LLM local (Ollama) pour analyser SESSION_SUMMARY
- Générer suggestions: "Basé sur les patterns, NeuralDBG prêt pour beta"
- Chat interface: "Kuro, quel projet nécessite attention ?"

#### v3.0: Predictive Analytics
- Prédire completion date basée sur velocity
- Détecter projets "à risque" avant qu'ils ne stagnent
- Recommander ressources: "Ce projet a besoin d'un designer"

---

**Status**: Vision Document
**Next Step**: Créer projet KuroGuardian dans lambda-Section
**Section**: lambda-Section-9 (Network Euler - DevOps/Automation)
**Initial %**: 0% (Vision) → 5% (MVP Daemon)
