# Réponses types — collaboration & support (R96 / R107 / R119 / R121)

> Objectif : répondre en moins de 24 h, aider d'abord, mentionner le produit
> au maximum en une phrase. Jamais de lien froid, jamais de DM non sollicité,
> jamais d'envoi automatique : validation humaine obligatoire (R120).
> Après envoi : ligne dans le tracker section 2 + échéance section 4 (R99).

## 0. Règles non négociables

1. Répondre à la question posée **avant** toute mention produit.
2. Une seule phrase produit par réponse, en contexte, jamais en conclusion publicitaire.
3. Aucune promesse de date, aucun chiffre non mesuré (`[mesure]` = à remplir ou à supprimer).
4. Aucun détail privé : pas de chemins locaux, pas de tokens, pas de données client (R41/R76).
5. Un seul ping de relance, à J+7, puis on archive.
6. Si la réponse demande un diff : validation humaine du diff avant envoi (R121).

---

## 1. GitHub — issues et PR

### 1.1 Aide technique sur une issue (R119)

````markdown
Thanks for the detailed report — I can reproduce the shape of it on [version].

What I observe:
- [symptom]
- [what rules out the obvious cause]

Most likely cause: [cause], not [alternative].

Two things to try, in order:
1. `[command]` — expected output: `[expected]`.
2. If that passes, `[next command]`.

Minimal repro I used:

```[lang]
[code]
```

If it still fails, paste the output of `[diagnostic command]`; that tells us
whether it is [A] or [B].
````

*Mention produit (optionnelle, une phrase) :* « I hit this while checking it
with [outil], which flagged [signal] on the same step. »

### 1.2 Description de PR (R121)

````markdown
## Problem

[One paragraph: observed behaviour, affected versions, who is impacted.]

## Reproduction

```[lang]
[minimal script]
```

Observed: `[output]`
Expected: `[output]`

## Root cause

[File:line] — [why it happens]. Not a symptom of [alternative].

## Fix

[What changed and why it is minimal/reversible.]

## Evidence

Before: `[tool output / metric]`
After: `[tool output / metric]`

## Tests

- [ ] `[test command]` passes
- [ ] Added regression test: `[path]`
````

### 1.3 Réponse à une demande de changement

```markdown
Thanks — agreed on [point]. Pushed [change] in [commit].

On [point 2], I kept [choice] because [reason]. Happy to switch if
[condition] — your call.

Re-ran [test command]: [result].
```

### 1.4 Relance à J+7 (une seule fois)

```markdown
Friendly ping — is there anything else you need on this one? Happy to adjust
the scope, or to close it if it is not useful.
```

Aucune mention produit dans une relance.

---

## 2. Show HN / Reddit — EN

### 2.1 « How is this different from X? »

```markdown
Fair question. X solves [problem] for [context]; this targets [different
context]. Concretely: [one mechanism], which means [observable difference].

Where X is better: [honest limit]. If that is your case, use X.
```

### 2.2 « Is it production-ready? »

```markdown
Not yet, and I would rather say it plainly. Current state: [what works],
tested on [scope]. Missing before production: [short list].

The repo has [tests/CI] so you can judge the gaps yourself: [link].
```

### 2.3 « Why not Kubernetes / Slurm / cloud? »

```markdown
If you already run a cluster, those are the right tools. This is for
[context: 2-3 machines, no admin, trusted peers]. The trade-off is
[limitation] in exchange for [benefit].
```

### 2.4 « Isn't P2P / remote execution risky? »

```markdown
Reasonable concern. The model is trust-first: only peers you explicitly add,
traffic inside WireGuard, workload in a Firecracker microVM, no inbound
service exposed by default. Remaining risk: [honest residual risk].

Threat model is documented here: [link]. If you need zero-trust multi-tenant,
this is not it.
```

### 2.5 « Open source? Pricing? »

```markdown
MIT, self-hosted, no account. [Optional: paid support/hosted version status —
only if true.] The repo is the product today: [link].
```

### 2.6 « It doesn't work on my machine »

```markdown
Thanks for trying it. Three quick checks so we do not guess:

1. `[command]` → expected `[output]`
2. `[command]` → expected `[output]`
3. OS/arch: [ ]

If those pass, the useful artifact is `[log/command output]`. Open an issue
with it and I will take a look: [issues link].
```

### 2.7 « This is self-promo »

```markdown
It is my project, so yes — disclosed. The reason I posted: [specific problem
discussed in the thread]. If the technical detail is not useful here, say so
and I will drop the link.
```

---

## 3. Discord FR — réponses courtes

### 3.1 Présentation dans #projets

```markdown
Bonjour — je travaille sur [projet] : [une phrase]. État actuel : [ce qui
marche], [ce qui manque]. Je cherche surtout [feedback précis], pas des
utilisateurs tout de suite. Le dépôt : [lien].
```

### 3.2 « Ça marche vraiment ? »

```markdown
Sur [périmètre] oui, vérifié par [test/mesure]. Sur [autre cas], non, et je
préfère le dire. Le détail est dans [doc/issue].
```

### 3.3 « Je peux tester ? »

```markdown
Oui. Prérequis : [OS/matériel]. Commande : `[commande]`. Si ça bloque,
envoie-moi la sortie de `[diagnostic]` — c'est ce qui me fait gagner du temps.
```

---

## 4. Propositions de collaboration reçues (mail / LinkedIn / DM)

### 4.1 Accusé de réception + qualification

```markdown
Bonjour [prénom],

Merci pour le message. Avant de vous répondre sur le fond, trois précisions
pour vérifier que c'est pertinent des deux côtés :

1. Quel problème concret voulez-vous résoudre, et pour qui ?
2. Quel périmètre : conseil, intégration, co-développement, distribution ?
3. Quel calendrier et quel modèle économique envisagez-vous ?

Je réponds sous [délai]. Si le sujet est hors de mon périmètre, je le dirai
clairement plutôt que de laisser traîner.
```

### 4.2 Refus poli

```markdown
Bonjour [prénom],

Merci d'avoir pensé à moi. Ce n'est pas le bon moment pour [raison courte et
factuelle]. Je préfère décliner plutôt que de m'engager à moitié.

Si [condition précise] devient vrai, revenez vers moi : [canal].
```

### 4.3 Go, avec périmètre explicite

```markdown
Bonjour [prénom],

D'accord pour avancer sur [périmètre exact]. Ce que je fournis : [livrable].
Ce que je ne fournis pas : [exclusions]. Échéance proposée : [date].

Deux conditions : [validation humaine des livrables], [propriété des données].
Si c'est aligné, je vous envoie un plan d'une page.
```

### 4.4 Relance après 5 jours ouvrés

```markdown
Bonjour [prénom],

Je reviens vers vous sur [sujet]. Si ce n'est plus d'actualité, aucun souci :
dites-le et je clôture. Sinon, il me manque juste [info] pour avancer.
```

---

## 5. Checklist avant envoi

- [ ] La question posée reçoit une réponse avant toute mention produit ?
- [ ] Une seule phrase produit maximum ?
- [ ] Aucune promesse de date ni chiffre non mesuré ?
- [ ] Aucune donnée privée ou chemin local (R41/R76) ?
- [ ] Le lien apporte quelque chose au lecteur (pas un lien froid) ?
- [ ] Un seul canal, un seul message (pas de cross-post identique) ?
- [ ] Tracker section 2 rempli + échéance section 4 posée ?
