# DESIGN — Socle universel (R109.2) — condensé opérationnel

Source de vérité : `rules/rule_109_adaptive_design.md`. Ce fichier est la version
de consultation rapide vendue localement (agents hors-ligne inclus).

## Les 10 règles non négociables

1. **Tokens 3 tiers** : primitives (`blue-500`) → sémantiques (`color.action.primary`) → composant (rare).
   Composants = uniquement sémantique. Format W3C DTCG version datée.
2. **Zéro hex brut dans un composant.** Jamais.
3. **Paires sémantiques** (`primary/on-primary`, `surface/on-surface`) : le contraste
   se vérifie PAR PAIRE, pas par couleur isolée.
4. **WCAG 2.2 AA en CI** : 4.5:1 texte · 3:1 large/non-texte — par thème indépendamment
   (une paire OK en light peut échouer en dark).
5. **Thèmes frères** : light/dark/high-contrast = mêmes clés, valeurs différentes.
   Honorer `prefers-color-scheme`, `prefers-contrast`, `forced-colors` (déférence système).
6. **Motion tokenisée** : courbes nommées + durées ; variante `prefers-reduced-motion`
   générée automatiquement. Une seule famille d'easing par produit.
7. **Cible tactile ≥ 44px** mobile.
8. **A11y en CI** (modèle Carbon) : chaque contribution passe les checks automatiques,
   pas d'audit de fin de projet.
9. **Anti-slop** : gradient décoratif, glassmorphism, glow, violet-par-défaut,
   emoji déco = interdits SAUF si définis par le langage choisi du produit.
10. **DESIGN.md obligatoire** à la racine du produit avant toute UI : langage choisi
    (matrice R109.1), raison, tokens racines.

## Naming tokens (évite les guerres)

- Primitives = valeur : `blue-500`, `space-4`, `radius-md`
- Sémantiques = rôle : `action-primary`, `text-muted`, `border-subtle`
- États en suffixe : `action-primary-hover`
- Interdits : `main`, `default`, `base`, préfixes plateforme

## Contraste : la matrice qui sauve

Tester en CI les paires sémantiques connues :
`text-primary/surface`, `text-on-action/action-primary`, `text-muted/surface-raised`…
Échec build si < 4.5:1 (corps) ou < 3:1 (large/UI). ~1 régression captée par trimestre.
