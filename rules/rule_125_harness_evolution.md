# RULE 125: Harness Evolution — Évolution des Règles avec Évaluateur Figé

## Rule

Les règles kuro-rules sont un **harness** : elles conditionnent chaque
session d'agent. Leur amélioration suit le protocole HarnessPro
(arXiv:2610.26770) : évolution récursive guidée par un **évaluateur figé**
et une **sélection Pareto performance/coût**, jamais par jugement LLM direct.

## Principes (issus du papier)

1. **Évaluateur figé, jamais touché par l'évolution.**
   `evals/eval_rules.py` est scellé par hash (`evals/frozen_eval.lock.json`).
   L'agent qui propose des réécritures de règles ne peut pas modifier
   l'évaluateur : toute modification est refusée (exit 2) tant qu'un
   re-freeze explicite par l'humain n'a pas été fait. Un judge LLM ne
   détecte que ~42% des échecs (papier §4.3) : on exécute, on ne demande pas.
2. **Plafond de perf (performance floor).**
   Aucune variante de règles n'a le droit de descendre sous la baseline h0
   scellée dans le lock. `PR(h) >= PR(h0)` — cf. aussi R116 (regression
   guards : une erreur corrigée ne revient pas).
3. **Optimiser perf ET coût.**
   Coût = tokens estimés des règles injectées (chars/4). Perf = couverture
   des règles mandatory (poids 2) + optionnelles (poids 1) validées par
   l'évaluateur figé. On cherche le front de Pareto, pas un "meilleur" unique.
4. **Sortir un menu, pas un seul harness.**
   Trois operating points : `lite` (sessions courtes), `medium` (défaut),
   `heavy` (releases/launches). Générés par `scripts/gen_rule_packs.py`.
5. **Coreset DPP pour l'analyse.**
   Quand on analyse des règles ou sessions pour les réécrire, on n'analyse
   pas tout : `scripts/evolve_rules.py` choisit un coreset divers (DPP
   greedy sur similarité de contenu) et dense (règles longues = difficiles).

## Verification

```
AU DÉBUT de toute session d'évolution des règles :
  CHECK: python evals/eval_rules.py          # exit 0 requis
  CHECK: le lock frozen_eval.lock.json existe
  CHECK: python scripts/evolve_rules.py      # rapport de coreset + Pareto

  IF exit 2 de eval_rules.py :
    L'évaluateur a été modifié → DEMANDER un re-freeze explicite à l'humain
    AVANT toute proposition de réécriture.

PENDANT :
  Chaque candidat de réécriture est une branche/commits séparés, réversibles.
  Le candidat est évalué par eval_rules.py (figé) — jamais auto-évalué.

APRÈS :
  IF pass_rate < baseline h0 :
    REJETER le candidat (plafond violé)
  IF pass_rate >= baseline ET tokens réduits :
    CANDIDAT non-dominé → proposer à l'humain (menu lite/medium/heavy)
```

## Enforcement

- RECOMMENDED — le protocole s'active quand l'humain lance une session
  d'évolution des règles (task `evolve`).
- Un re-freeze de l'évaluateur (`eval_rules.py --freeze`) exige la
  validation humaine et doit être mentionné dans SESSION_SUMMARY.md.

## Fichiers associés

- `evals/eval_rules.py` — évaluateur figé (hash scellé)
- `evals/frozen_eval.lock.json` — verrou + baseline h0
- `scripts/gen_rule_packs.py` — générateur des packs lite/medium/heavy
- `scripts/evolve_rules.py` — coreset DPP + rapport Pareto des packs
- `packs/AGENTS_{lite,medium,heavy}.md` — les 3 menus de règles
- `reports/evolution_report_*.json` — rapports d'évolution datés

## Lessons Learned associées

- Copier UNE astuce ne suffit pas (papier §5.5 ablations : « RHO + budget
  hooks » baisse le coût mais casse la perf). C'est la combinaison
  (routing + compression + vérification préservée) qui avance le front.
- Baissier uniformément l'effort de raisonnement = catastrophe
  (80% → 62% de pass rate dans l'ablation « low reasoning effort »).

---

**Créée**: 2026-10-26
**Source**: HarnessPro, arXiv:2610.26770 (issue #30, WS4)
**Applies to**: sessions d'évolution des règles kuro-rules
**Enforcement**: RECOMMENDED
