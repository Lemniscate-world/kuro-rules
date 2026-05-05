# Desk Research Framework - Kuro Rules

**Version**: 1.0  
**Date**: 2026-04-05  
**Status**: Active  
**Project**: All projects (Astral, NeuralDBG, etc.)

---

## Philosophy

Le Desk Research est une méthode de validation alternative au Mom Test. Il utilise des sources vérifiables (forums, GitHub, articles, études) pour prouver l'existence d'un problème réel et la volonté des utilisateurs de payer.

**Principe fondamental**: Sources vérifiables > opinions. Comportement réel > intentions déclarées.

---

## Quand utiliser Desk Research

| Scénario | Méthode recommandée | Preuve requise |
|----------|---------------------|----------------|
| Startup avec temps limité | Desk Research (4h) + MVP Prototype (4h) | 10+ sources, 3+ preuves comportementales |
| Marché B2B difficile à joindre | Desk Research + 2-3 interviews | 10+ sources + 2 interviews |
| Problème technique spécifique | Desk Research approfondi | 15+ sources, 5+ preuves |
| Validation rapide avant pivot | Desk Research express (2h) | 5+ sources, verdict GO/NO-GO |

---

## Types de Sources Acceptables

### Tier 1 - Haute Confiance (prioritaire)
- GitHub issues avec +10 upvotes, récents
- Threads Reddit avec +50 votes, discussions actives
- Forums officiels (Cursor, Nx, etc.) avec réponses de l'équipe
- Études publiées (McKinsey, Stack Overflow Survey)
- Rapports d'entreprises reconnues

### Tier 2 - Confiance Moyenne (à vérifier)
- Articles de blog tech reconnus
- Tweets/threads de personnes identifiables
- Discord/Slack communities avec historique
- Podcasts tech avec transcripts

### Tier 3 - Faible Confiance (éviter ou contextualiser)
- Articles marketing sans données
- Tweets sans engagement
- Sources anonymes
- "J'ai entendu dire..."

---

## Types de Preuves Comportementales

### Preuve A: Démonstration de douleur
- Citations directes: "Je perds X heures par jour sur..."
- Nombre de votes/upvotes sur des plaintes
- Fréquence des posts sur un même problème

### Preuve B: Solutions de fortune
- "J'ai construit un script pour..."
- "On utilise un hack avec..."
- "Notre équipe a développé en interne..."

### Preuve C: Volonté de payer
- "Je paierais pour..."
- "Si seulement [outil X] existait..."
- Questions sur le pricing sur des alternatives

### Preuve D: Impact métier
- "On a retardé le release à cause de..."
- "On a perdu $X à cause de..."
- "Notre productivité a chuté de X%"

---

## Processus Desk Research (Standard)

### Phase 1: Cadrage (15 min)
1. Définir la question de recherche
2. Identifier les mots-clés principaux et secondaires
3. Choisir les canaux de recherche (Google, Reddit, GitHub, Twitter, etc.)

### Phase 2: Collecte (2-3h)
1. Recherche sur Google avec opérateurs avancés
2. Recherche sur Reddit (r/ExperiencedDevs, r/webdev, etc.)
3. Recherche sur GitHub (issues, discussions)
4. Recherche sur Twitter/X (threads, discussions)
5. Recherche sur forums officiels

### Phase 3: Analyse (1h)
1. Classer les sources par tier
2. Identifier les patterns récurrents
3. Compter les preuves comportementales
4. Évaluer la qualité des sources

### Phase 4: Synthèse (30 min)
1. Créer le fichier `validation_evidence.md`
2. Remplir la matrice de preuves
3. Rédiger le verdict GO/NO-GO/ADJUST
4. Proposer les prochaines étapes

---

## Outils et Opérateurs de Recherche

### Google Avancé
```
"monorepo" "AI" site:reddit.com after:2025-01-01
"Cursor" freeze OR crash OR slow site:forum.cursor.com
"cross-project" dependency impact filetype:pdf
intitle:"monorepo" pain OR problem OR challenge
```

### GitHub Search
```
is:issue monorepo "slow" OR "freeze" OR "crash" created:>2025-01-01
is:discussion "cross-project" dependencies
```

### Reddit Search
```
monorepo pain points
Cursor large codebase problem
AI coding monorepo limitations
```

---

## Template validation_evidence.md

```markdown
# Validation Evidence - [Project Name]

**Date**: YYYY-MM-DD  
**Researcher**: AI Agent  
**Time spent**: X hours  
**Sources found**: X  
**Behavioral proofs**: X  

## Executive Summary

**Verdict**: [ ] GO | [ ] NO-GO | [ ] ADJUST  
**Confidence**: [ ] High | [ ] Medium | [ ] Low  

**Summary**: 
[2-3 phrases sur la découverte principale]

## Sources Matrix

| # | Source | Date | Tier | Type | Signal | URL |
|---|--------|------|------|------|--------|-----|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |

## Behavioral Proofs

### Proof 1: [Type]
**Source**: 
**Quote**: 
**What it proves**: 

### Proof 2: [Type]
**Source**: 
**Quote**: 
**What it proves**: 

### Proof 3: [Type]
**Source**: 
**Quote**: 
**What it proves**: 

## Patterns Identified

1. **[Pattern name]**: [Description]
   - Evidence count: X
   - Source quality: [ ] High | [ ] Medium | [ ] Low

## Competitive Landscape

| Competitor | Strength | Weakness | Gap |
|------------|----------|----------|-----|
| | | | |

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| | | | |

## Decision

**GO if**: [Conditions]
**NO-GO if**: [Conditions]
**ADJUST if**: [Conditions]

**Recommended next step**: 

## Methodology Notes

- Search queries used: 
- Channels explored: 
- Limitations: 
```

---

## Checklist Qualité Desk Research

### Avant de commencer
- [ ] Question de recherche clairement définie
- [ ] Mots-clés principaux et secondaires identifiés
- [ ] Canaux de recherche sélectionnés
- [ ] Temps alloué décidé (2h, 4h, etc.)

### Pendant la recherche
- [ ] Minimum 10 sources collectées
- [ ] Sources de Tier 1 priorisées
- [ ] Dates vérifiées (2025-2026 prioritaires)
- [ ] URLs sauvegardées
- [ ] Citations directes extraites

### Analyse
- [ ] Minimum 3 preuves comportementales identifiées
- [ ] Patterns récurrents détectés
- [ ] Sources contradictoires notées
- [ ] Qualité des sources évaluée

### Synthèse
- [ ] Fichier validation_evidence.md créé
- [ ] Verdict GO/NO-GO/ADJUST rédigé
- [ ] Prochaines étapes recommandées
- [ ] Limitations de la recherche documentées

---

## Prompts Desk Research (Perplexity & Grok)

Voir fichiers:
- `prompts/desk_research_perplexity.md`
- `prompts/desk_research_grok.md`

---

## Équivalence avec Mom Test

| Desk Research | Équivalence Mom Test |
|---------------|----------------------|
| 10+ Tier 1 sources + 3+ preuves | 2 interviews |
| 15+ mixed sources + 5+ preuves | 3 interviews |
| 20+ sources + 8+ preuves + landing page | 5 interviews |

---

## Anti-Patterns (À Éviter)

1. **Cherry-picking** : Ne retenir que les sources qui confirment l'hypothèse
2. **Confirmation bias** : Ignorer les sources contradictoires
3. **Anecdata** : Generaliser à partir d'une seule anecdote
4. **Source tier 3** : Rely sur des sources non vérifiables
5. **No synthesis** : Accumuler des sources sans les analyser

---

## Sync Rules

**Quand mettre à jour ce fichier**:
1. Après chaque Desk Research majeur
2. Si de nouvelles sources types émergent
3. Si la méthodologie évolue

**Sync vers**: `~/Documents/kuro-rules/`

