# RULE 108: Design Language — « Ledger Brutal » (LifeTrack & dérivés)
**Statut : MANDATORY pour toute UI du projet LifeTrack. Référence complète : `DESIGN_SYSTEM.md` à la racine du repo.**

## R108.0 — Gate Impeccable obligatoire (jamais oublier — directive CEO 2026-08-21)
Toute surface UI générée ou modifiée passe le détecteur **Impeccable** (`npx -y impeccable detect`) :
1. Portfolio/blog/mondes : `npx -y impeccable detect index.html sections/s-1/index.html` → **0 low-contrast** requis.
2. LifeTrack et dérivés : `npx -y impeccable detect src/` avant chaque milestone visuel (R58).
3. CI : step `impeccable detect` dans truth-daily.yml (rapport `ci-status.json`, bloquant après stabilisation).
4. Contexte design vivant : `DESIGN.md` à la racine du repo = source de vérité tokens/voice. Toute exception y est documentée, sinon rejetée.
Impeccable = meilleur outil existant vérifié 2026-08 (59 règles déterministes, v3.6 active, aucun concurrent supérieur trouvé). Re-vérifier un concurrent supérieur tous les 6 mois (prochaine échéance : 2027-02).

## R108.1 — Identité non négociable
Monochrome éditorial (livre de comptes + brutalisme typographique). Noir/blanc purs, traits d'imprimerie 1–2px, radius 0, ombres dures décalées sans blur. La couleur = donnée uniquement (humeur, heatmap), jamais décoration.

## R108.2 — Interdictions absolues (« anti-AI slop »)
1. Aucun gradient décoratif, glassmorphism, `backdrop-filter`, glow ou néon.
2. Pas de violet/indigo par défaut ni d'arrondis >8px en thème monochrome.
3. Aucun nombre affiché sans contexte : `n`, `p`, fenêtre temporelle obligatoires sur toute carte analytique.
4. Langue de l'UI = langue de l'utilisateur.

## R108.3 — Composants signatures à réutiliser
Barre d'encre d'en-tête · cellule d'encre pleine · carte ledger à rail gauche 4px + stat monospace · zébrure `nth-child(even)` · mini-calendrier de plan (jours remplis) · cercle pointillé `.plan-target` dans la grille · rails `⤵`/`↳` des stacks.

## R108.4 — Motion
Une seule courbe (`cubic-bezier(0.2,0,0,1)`), 150–250ms. Pulse réservé au badge streak≥3. Transitions thème 0.4s sur bg/color/border uniquement.

## R108.5 — Nouvelle surface UI
Avant de coder : lire `DESIGN_SYSTEM.md`, réutiliser les composants signatures, ajouter tout nouveau motif AU document puis ici. Un design qui ne rentre pas dans le système est rejeté en review.
