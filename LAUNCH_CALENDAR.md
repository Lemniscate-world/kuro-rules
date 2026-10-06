# LAUNCH_CALENDAR.md — spikes planifiés (R95 + R96 + R99)

> Règle : 1 spike/mois max par produit. Fenêtre : mar-jeu, 10h-12h ET (HN) / ~15h UTC (Reddit).
> Après chaque spike : réponses sous 24h + log R99 sous 5 min + JPM+7 bilan.

| Mois | Produit | Canal | Asset prêt | Statut |
|---|---|---|---|---|
| M1 | NeuralDBG | Show HN | draft §1 ci-dessous | draft |
| M1 | NeuralDBG | Reddit r/MachineLearning [Project] | adapter template R96 | à faire |
| M2 | LifeTrack | Show HN | à rédiger (angle N=1 local-first) | à faire |
| M2 | LifeTrack | BetaList / ProductHunt | page + screenshots | à faire |
| M3 | Portfolio dashboard | Show HN | launch plan existant (docs/) | à faire |
| M3 | Helium | Reddit r/rust + Discord FrancophonIA | posts R96 | à faire |

## Règles de tir
- Jamais deux spikes la même semaine (cannibalisation réponses).
- Chaque spike porte un aimant (S1) + UTM (cta_kit) : trafic -> capture, pas juste visites.
- Show HN : fondateur présent toute la journée, réponses à TOUS les commentaires.
- Si flop (< 10 points HN / 5 upvotes) : post-mortem `docs/launch_postmortem.md`, pas de repost avant 30j.

## 1. Draft Show HN — NeuralDBG (M1)

**Titre :**
```
Show HN: NeuralDBG – why your PyTorch run failed, in seconds
```

**Corps :**
```
Hi HN. Training failures (NaN loss, vanishing/exploding gradients) eat hours:
existing tools show WHEN it happens, not WHY.

NeuralDBG hooks the PyTorch loop and ranks causal hypotheses down to the
layer and step, e.g. "loss blew up at step 234, origin layer4.0.conv1 —
likely LR x saturated ReLU". MIT, pip install, 100% local, works with
torch.compile.

138 tests green across 6 architectures. The 7 failure patterns we see most:
[lien checklist aimant + UTM].

Built by lambda-Section. Happy to answer anything, especially where our
causal claims look shaky — that's where we learn most.
```
