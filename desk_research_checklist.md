# Desk Research Tools — Validation Checklist

**Usage** : Copier cette checklist dans chaque rapport de desk research

---

## Pre-Research Setup

- [ ] Hypothese probleme clairement definie
- [ ] Segment cible identifie
- [ ] Duree max definie (2-4h)
- [ ] Template rapport pret
- [ ] **Regle verifications sources lue** (pas d'illusions)

---

## Section Critique : Verification Strict Sources — MANDATORY

### Definition "Illusion de Source"

Une "illusion de source" se produit quand :
- L'agent invente une URL qui n'existe pas
- L'agent cite une source sans jamais l'avoir verifiee
- L'agent resume un contenu sans l'avoir lu
- L'agent melange plusieurs sources en une "synthese" non verifiable

### Checklist Verification Avant Citation

Pour CHAQUE source citee, OBLIGATOIREMENT :

- [ ] **URL verifiee** — `search_web` ou `mcp1_fetch` a reussi
- [ ] **Contenu lu** — Resume fidele, pas d'invention
- [ ] **Citation verbatim** — Texte exact entre guillemets
- [ ] **Date incluse** — Quand la source a ete publiee
- [ ] **Accessibilite** — Pas de 404, pas de robots.txt bloquant

### Sources Acceptables vs Interdites

| Type | Acceptable ? | Condition |
|------|--------------|-----------|
| Reddit thread | Oui/NON | [ ] Fetch OK [ ] robots.txt bloque |
| StackOverflow | Oui | [ ] URL verifiee |
| Article blog | Oui | [ ] Fetch OK [ ] Date connue |
| Rapport PDF | Oui | [ ] URL directe [ ] Telechargeable |
| GitHub issue | Oui | [ ] URL verifiee |
| "J'ai lu que..." | **NON** | Jamais citer sans source |
| "Les gens disent..." | **NON** | Trop vague, pas verifiable |

### Tableau de Verification des Sources

| # | Source URL | Verifiee ? | Methode | Date | Citation Verbatim |
|---|------------|------------|---------|------|-------------------|
| 1 | | [ ] Oui [ ] Non | | | "..." |
| 2 | | [ ] Oui [ ] Non | | | "..." |
| 3 | | [ ] Oui [ ] Non | | | "..." |
| 4 | | [ ] Oui [ ] Non | | | "..." |
| 5 | | [ ] Oui [ ] Non | | | "..." |
| 6 | | [ ] Oui [ ] Non | | | "..." |
| 7 | | [ ] Oui [ ] Non | | | "..." |
| 8 | | [ ] Oui [ ] Non | | | "..." |
| 9 | | [ ] Oui [ ] Non | | | "..." |
| 10 | | [ ] Oui [ ] Non | | | "..." |

**Taux de sources verifiables** : __ / 10 minimum (80% requis)

### Interdiction Formelle

- **NE PAS** citer une source sans l'avoir verifiee avec `mcp1_fetch` ou `search_web`
- **NE PAS** inventer des citations — uniquement verbatim
- **NE PAS** melanger des sources en une "synthese" non verifiable
- **NE PAS** citer des sources > 2 ans sans justification
- **NE PAS** ignorer les robots.txt — documenter si bloque

### Si Source Non Verifiable

1. Chercher une source alternative accessible
2. Documenter pourquoi l'originale n'est pas citee
3. JAMAIS citer une source non verifiee

---

## Phase 1 : Concurrents (5+ sources) — 30min

### Direct Competitors
- [ ] **Bittensor (TAO)** — Decentralized AI compute
  - URL : https://bittensor.com
  - Status : [Existe / En beta / Dead]
  - Traction : [Users ? / Revenue ? / Growth ?]
  - Gap : [Ce qu'ils ne font pas]
  
- [ ] **Akash Network** — Decentralized cloud
  - URL : https://akash.network
  - Status : 
  - Traction :
  - Gap :
  
- [ ] **Golem Network** — P2P computing
  - URL : https://golem.network
  - Status :
  - Traction :
  - Gap :
  
- [ ] **iExec** — Decentralized marketplace
  - URL : https://iex.ec
  - Status :
  - Traction :
  - Gap :
  
- [ ] **RunPod** — GPU cloud
  - URL : https://runpod.io
  - Status :
  - Traction :
  - Gap :

### Indirect Competitors
- [ ] **Google Colab Pro** — Managed notebooks
  - Pain point they solve :
  - Pain point they create :
  
- [ ] **Vast.ai** — P2P GPU marketplace
  - Status :
  - Gap (trust-based sharing) :

### Synthese Concurrents
| Concurrent | Existe depuis | Traction | Notre differentiel |
|------------|---------------|----------|-------------------|
| [Nom] | [Annee] | [Users/Revenue] | [Diff] |

**Gap confirme ?** [ ] Oui [ ] Non

---

## Phase 2 : Communaute (5+ preuves) — 60min

### Reddit Threads
- [ ] **r/LocalLLaMA — Thread 1**
  - Titre : 
  - URL : 
  - Votes : 
  - Comments : 
  - Quote verbatim : "..."
  - Date : 
  - Preuve comportement ? [ ] Oui [ ] Non

- [ ] **r/LocalLLaMA — Thread 2**
  - Titre : 
  - URL : 
  - Quote : "..."
  - Preuve comportement ? [ ] Oui [ ] Non

- [ ] **r/MachineLearning — Thread**
  - Titre :
  - URL :
  - Quote : "..."
  - Preuve comportement ? [ ] Oui [ ] Non

### StackOverflow / Hacker News
- [ ] **Question 1**
  - URL :
  - Quote : "..."
  - Views/Answers :
  
- [ ] **Hacker News Thread**
  - URL :
  - Quote : "..."

### Discord / Forums
- [ ] **Communaute 1**
  - Nom :
  - Preuve : Screenshot ou quote
  - Date :

### Synthese Communaute
**Nombre de preuves comportementales** : __ / 5 minimum
**Mentions spontanees du probleme** : __ / 3 minimum
**Solution seekers identifies** : __ / 2 minimum

---

## Phase 3 : Marche (3+ sources) — 30min

### Taille du Marche
- [ ] **Source 1** : [Nom rapport]
  - TAM : 
  - SAM :
  - SOM :
  - URL :
  
- [ ] **Source 2** : [Nom rapport]
  - Marche GPU AI : 
  - CAGR :
  - URL :

### Segments Cibles
- [ ] **Segment 1** : [Nom]
  - Taille : 
  - Besoin : 
  - Budget :
  
- [ ] **Segment 2** : [Nom]
  - Taille :
  - Besoin :
  - Budget :

### Trends
- [ ] Trend 1 : [Description + source]
- [ ] Trend 2 : [Description + source]

### Synthese Marche
**Marche > $100M ?** [ ] Oui [ ] Non
**Croissance > 20% CAGR ?** [ ] Oui [ ] Non
**Segments clairs ?** [ ] Oui [ ] Non

---

## Phase 4 : Validation Finale — 15min

### Checklist Decision
- [ ] 10+ sources verifiees (concurrents + communaute + marche)
- [ ] 3+ preuves comportementales (discussions avec citations)
- [ ] Probleme mentionne spontanement (pas juste en reponse a une question)
- [ ] Marche existe et en croissance
- [ ] Gap identifie et confirmable

### Verdict
**GO** [ ] — Probleme valide, lancer Concierge MVP / Landing page
**NO-GO** [ ] — Pas de probleme documente, abandonner
**PIVOT** [ ] — Probleme similaire mais ajuster l'approche

### Si GO
**Prochaines etapes** :
1. 
2. 
3. 

### Si NO-GO
**Raisons** :
- 
- 

**Alternative suggeree** :
- 

### Si PIVOT
**Ajustements necessaires** :
- 
- 

---

## Post-Research

- [ ] Rapport complete et sauvegarde
- [ ] Sources verifiees et citees
- [ ] Preuves attachees (screenshots si pertinent)
- [ ] Decision documentee avec justification
- [ ] Mise a jour `validation_evidence.md`
- [ ] Mise a jour `decision-memo.md`

---

## Quality Check

Avant de considerer le desk research comme valide, verifier :

1. **Sources recentes** : > 80% des sources ont < 2 ans
2. **Sources primaires** : Pas juste des articles de blog, mais des discussions, rapports
3. **Quantification** : Chiffres, pourcentages, tailles de marche
4. **Comportement reel** : Pas juste des intentions, des preuves d'action
5. **Citation exacte** : Quotes verbatim, pas de paraphrase
6. **URLs accessibles** : Liens verifiables

---

## Section Critique : Risques d'Echec et Remedes — MANDATORY

### Analyse des Modes de Failures

Pour CHAQUE projet, documenter les 5 risques principaux qui pourraient causer l'echec :

#### Template d'Analyse Risque

| # | Risque | Probabilite | Impact | Evidence Contre | Remede |
|---|--------|-------------|--------|-----------------|--------|
| 1 | [Description] | Haute/Moyenne/Faible | Mortel/Grave/Mineur | [Preuves desk research] | [Action preventive] |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

### Risques Communs a Evaluer

#### 1. Risque Marche (Market Risk)
**Question** : Le probleme existe-t-il vraiment ?
- **Signes d'alerte** : Aucune discussion spontanee du probleme, solutions existantes satisfaisantes
- **Evidence requise** : 3+ mentions spontanees du probleme dans des sources primaires
- **Remede** : Pivot vers un probleme adjacent valide, ou abandon (NO-GO)

#### 2. Risque Concurrence (Competition Risk)
**Question** : Pourquoi nous vs. les autres ?
- **Signes d'alerte** : Leader etabli avec 50%+ de part de marche, differentiation faible
- **Evidence requise** : Gap reel identifie, pas juste "nous serons meilleurs"
- **Remede** : Pivot vers niche non couverte, ou adjacence (B2B vs B2C, vertical specifique)

#### 3. Risque Technique (Technical Risk)
**Question** : Peut-on vraiment le construire ?
- **Signes d'alerte** : Dependance technologique non mature (ex: blockchain non scalable)
- **Evidence requise** : Prototype MVP fonctionnel ou preuve de concept reussie
- **Remede** : Simplifier le scope MVP, ou pivot vers solution moins technique

#### 4. Risque Reglementaire (Regulatory Risk)
**Question** : Est-ce legal ? Y aura-t-il des restrictions ?
- **Signes d'alerte** : Domaine hautement reglemente (sante, finance, crypto), incertitude juridique
- **Evidence requise** : Consultation juridique ou precedent clair
- **Remede** : Jurisdiction pivot, ou model business compliant (ex: non-custodial)

#### 5. Risque Adoption (Adoption Risk)
**Question** : Les utilisateurs changeront-ils leurs habitudes ?
- **Signes d'alerte** : Changement de comportement majeur requis, friction elevee
- **Evidence requise** : Comportements similaires deja observes, ou pre-commandes
- **Remede** : Reduire friction (onboarding 1-click), ou pivot vers early adopters desesperes

### Matrix Decisionnelle Risques

**Cumul des risques** :
- **0-1 risques critiques** : GO — Proceder avec prudence
- **2 risques critiques** : ADJUST — Attenuer avant de lancer
- **3+ risques critiques** : NO-GO ou PIVOT majeur

### Verification Anti-Failure

Avant de conclure le desk research, verifier :

```
CHECK: Ai-je identifie les 5 risques principaux ?
CHECK: Ai-je trouve de l'evidence CONCRETE contre chaque risque ?
CHECK: Les remedes sont-ils actionnables et realistes ?
CHECK: Le cumul des risques permet-il un GO ?
```

### Interdictions

- **NE PAS** ignorer un risque critique parce qu'on "aimerait que ca marche"
- **NE PAS** sous-estimer la probabilite d'un risque (optimisme biaisé)
- **NE PAS** proposer un remede non testable (ex: "on verra plus tard")
- **NE PAS** continuer si 3+ risques critiques sans remedes solides

---

## Tools Utilises

Cocher les outils AI utilises :
- [ ] `search_web` — Recherche web
- [ ] `mcp1_fetch` — Extraction contenu
- [ ] Perplexity AI — Synthese multi-sources
- [ ] Exa AI — Recherche semantique
- [ ] Wayback Machine — Historique

---

## Time Tracking

| Phase | Temps prevu | Temps reel | Status |
|-------|-------------|------------|--------|
| Setup | 15min | | [ ] |
| Concurrents | 30min | | [ ] |
| Communaute | 60min | | [ ] |
| Marche | 30min | | [ ] |
| Validation | 15min | | [ ] |
| Documentation | 30min | | [ ] |
| **TOTAL** | **2h40** | | |

---

**Researcher** : [Nom AI Agent / User]
**Date** : YYYY-MM-DD
**Projet** : [Nom]
