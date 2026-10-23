# Durcissement agents + protocole labo ARTEX (2026-10-11)

## Fait vérifié : ARTEX n'est pas ce qui était annoncé

- Repo unique : `BaaRai/ARTEX`, créé le 08/10/2026 (3 jours), **2 stars / 2 forks**,
  pas 2970. Langage Go, licence **AGPL-3.0**, description « English translation ».
- Statut : non audité, auteur inconnu, code offensif potentiel (pentest autonome).
- Décision : **ne pas cloner ni exécuter en l'état.** Un outil d'attaque non audité,
  c'est une porte d'entrée, pas un audit. Réévaluer quand : revue de code faite,
  historique et mainteneur établis, ou fork de confiance.
- Note licence : AGPL-3.0 = copyleft réseau. Ne pas intégrer de code ARTEX dans
  nos apps sans analyse juridique, même en interne exposé.

## Checklist durcissement agents (esprit « proactive assurance »)

Déjà couvert par `scripts/kuro_security.py` : Dependabot alerts + auto-fixes.
À appliquer sur chaque agent/projet exposé :

1. **Sandbox tool-calls** : allowlist d'outils, pas de shell brut depuis le modèle.
2. **Secrets** : jamais en prompt, jamais en log ; `.env` hors git (déjà en place).
3. **Revue humaine** : toute action irréversible (envoi, paiement, suppression)
   = ordre humain explicite après relecture (cf verrou 11/10 acquisition_tracker).
4. **Kill-switch** : garde ANTI-SALAD + passage en brouillons seuls, comme fait
   sur `prospects-daily` / `replies-watch`.
5. **Logs d'incidents** : chaque anomalie agent → entrée datée (modèle KURO_ACTIONS_LOG).
6. **Red-team manuel ciblé** (sans ARTEX) : sur COPIE jetable, tester
   prompt-injection, exfiltration de secrets, abus d'outils. Chaque finding →
   regression-guard (test qui échoue si la faille revient).

## Protocole labo (si un jour on teste un pentest IA)

- [ ] VM ou conteneur jetable isolé, snapshot avant, **jamais sur réseau prod/maison**.
- [ ] Cible = copie locale jetable de nos APIs (jamais prod, jamais tiers sans accord écrit).
- [ ] Audit du code source de l'outil AVANT exécution (Go lisible, ~10 Mo ici).
- [ ] Sortie = findings → regression-guards, pas d'exploitation.
- [ ] Destruction du labo après (snapshot + rapport suffisent).

## Verdict sandbox

- [x] Checklist applicable immédiatement, coût zéro.
- [ ] ARTEX : en attente de maturité/audit. Prochain jalon : re-vérifier stars,
  commits et revue de code dans 30 jours via `scripts/veille_outils.py`.
