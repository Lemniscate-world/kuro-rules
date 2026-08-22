# DESIGN — Cheat sheets par langage (R109.1)

Choisir UN langage par produit (matrice R109.1), le déclarer dans son DESIGN.md.

## GitHub Primer — devtools
- Audience : développeurs. Densité élevée, mono pour données/code.
- Tokens fonctionnels ; composants sobres, focus visible fort.
- Réf : https://primer.style

## IBM Carbon — data enterprise
- Grille 2x stricte, type fluid, densité maximale maîtrisée.
- A11y la plus profonde du marché (WCAG 2.2 documenté par composant, AAA sur variantes).
- 3 couches explicites : global (interne) → alias → composant.
- Réf : https://carbondesignsystem.com

## Apple HIG — natif grand public
- Clarity / Deference / Depth. SF Pro, Dynamic Type (Body 17pt, Large Title 34pt).
- Couleurs sémantiques système ADAPTATIVES (`systemBlue`) — jamais de hex figé.
- Cible 44pt, Liquid Glass (2025) si produit Apple-centrique.
- Réf : https://developer.apple.com/design/human-interface-guidelines

## Material 3 — mobile/web expressif
- Source color → 13 palettes tonales HCT générées algorithmiquement.
- Rôles garantis AA par construction. Material Theme Builder pour exporter.
- Motion : 4 courbes nommées par type d'interaction.
- Réf : https://m3.material.io

## Shopify Polaris — fintech/commerce
- Clarté marchande, flows de conversion, copywriting intégré au système.
- Réf : https://polaris.shopify.com

## Ledger Brutal (R108) — éditorial/marque forte lambda-Section
- Réservé LifeTrack & dérivés + vitrines éditoriales. Voir `rules/rule_108_design_language.md`.

## shadcn/Radix — implémentation React
- Code possédé dans le repo (`components/ui/`), pas de dépendance runtime.
- A11y comportementale vient de Radix : ne pas remplacer un Dialog par une div.
- Thème = CSS variables sur `:root/.dark` ; éditer les variables, pas les composants.
- Fork autorisé quand les variants ne couvrent pas ; wrapper interdit.
