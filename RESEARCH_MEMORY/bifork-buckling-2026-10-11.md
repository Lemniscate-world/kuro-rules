# Bi-FORK — démo buckling-beam (2026-10-11)

Source papier : arXiv:2610.12449 (08/10/2026). Code officiel : https://github.com/ml-jku/Bi-FORK
(antécédent léger : FHendriks11/bifurcationML, torch + pytorch-geometric).

## Ce que montre la démo locale

`python scripts/buckling_demo.py --out outputs/buckling` (numpy/scipy/matplotlib uniquement).
Modèle : barre rigide + ressort torsion, équilibre λ·sin θ − θ = 0.

- λ < 1 : une solution, θ = 0 (poutre droite).
- λ > 1 : θ = 0 instable + 2 branches ±θ (flambe à gauche OU à droite).
- À λ = 2.0 : branches ±1.895 rad, écart 3.791.
- Artefacts : `outputs/buckling/buckling.png` (fourche + 2 déformées), `bifurcation.csv`.

## Pourquoi c'est le problème de Bi-FORK

Un surrogate déterministe minimise l'erreur moyenne → prédit la moyenne des
branches = 0 = poutre droite sous charge supercritique. Physiquement faux,
c'est le mode collapse. Bi-FORK génère les trajectoires complètes en latent
(flow matching) et sépare les branches en une passe (repulsion-guided
sampling, analogue parallèle de la déflation classique). Évalué sur poutres,
métamatériaux et Allen-Cahn jusqu'à 260 000 points.

## Verdict sandbox

- [x] Concept reproduit en classique, 2/2 branches distinctes.
- [ ] Modèle Bi-FORK réel hors scope machines actuelles (GPU + datasets haute résolution).
- Analogie finance : même choc macro → 2 régimes (panique/absorption). Un modèle
  qui prédit la moyenne des régimes prédit un régime qui n'existe pas.
- Règle : sur tout système à bifurcation, exiger la couverture des branches
  (Jensen-Shannon par orbite de symétrie, cf papier), jamais une prédiction unique.
