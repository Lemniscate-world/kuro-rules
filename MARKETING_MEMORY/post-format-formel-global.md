# Format Post Formel - Global, tous repos (2026-09-20)
Source : dérivé de `helium-post-format-formel.md`, généralisé à la demande utilisateur.

## Langue et ton (tous projets)
- Français formel uniquement, vouvoiement.
- Proscrire slang, familiarités, promesses de dates, hype.
- Phrases courtes, factuelles.

## Structure obligatoire pour tout post projet
1. **Présentation du projet** (3 lignes max)
   - Définition en 1 phrase : ce que fait le projet, pour qui.
   - Section / périmètre : partie du projet concernée, position dans l'écosystème.
   - Objectif : problème résolu, alternative apportée.
2. **Travaux réalisés aujourd'hui** (liste numérotée)
   - Composant + version si applicable.
   - Livrables concrets vérifiés (code, script, doc, test).
   - Aucun détail propriétaire sensible.
3. **Prochaine étape** (1 phrase).
4. **Caption** courte prête à copier-coller.

## Intelligence attendue pour tout repo
Quand l'utilisateur demande "post", "post du jour", "aide pour un post" :
1. Détecter le repo courant via le répertoire de travail.
2. Vérifier automatiquement : `git log --oneline -5`, `git status --short`, fichiers modifiés du jour.
3. Rappeler la définition du projet depuis README / ROADMAP / PLAN sans redemander.
4. Si Glances / captures évoquées, laisser un placeholder [métrique à compléter].
5. Proposer directement la version formelle. Ne proposer de version familière que sur demande explicite.
6. Ce modèle s'applique à tous les repos listés dans `projects.txt`, pas uniquement Helium.
