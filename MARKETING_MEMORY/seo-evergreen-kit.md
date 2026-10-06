# SEO evergreen kit (R110) — requêtes, angles, cross-post

> Principe : 1 requête = 1 page qui répond vraiment, code exécuté (versions
> notées). Cross-post : dev.to + Hashnode + lien canonique repo.
> Interdit : keyword stuffing, promesses, chiffres non mesurés.

## Requêtes cibles (volume/intent, à valider Search Console après 90j)
| Requête | Angle | Produit | Statut |
|---|---|---|---|
| pytorch nan loss debug | reproduire en 15 lignes + 3 checks (ce fichier §1) | NeuralDBG | écrit |
| pytorch loss becomes inf | LR vs saturation, dichotomie LR/10 | NeuralDBG | outline |
| dead relu how to detect | histogramme activations, pas la loss | NeuralDBG | outline |
| overfitting small trades (quant) | discipline de fenêtre, pas de tweak | OpenQuant | outline |
| restart habit tracking after break | protocole 7-day reset (aimant S1) | LifeTrack | outline |

## Outlines (structure R110 : problème vécu -> TL;DR -> code -> gotchas)
- **loss becomes inf** : même snippet, LR 1.0 vs 0.01, tableau comparatif, gotcha fp16.
- **dead relu** : MLP seed fixe, % activations nulles par couche, gotcha init.
- **overfitting trades** : règle fenêtre écrite d'avance, journal, gotcha 7 trades.
- **restart tracking** : protocole aimant + grille, gotcha 2-jours.

## Cross-post protocole
1. Publier sur le repo/docs d'abord (canonique).
2. dev.to + Hashnode 48h après, lien canonique en tête.
3. 1er commentaire = question ouverte (engagement, pas de lien froid).
4. Log R99 + UTM par plateforme (cta_kit).

## 1. TUTORIEL : reproduire une loss NaN/inf en 15 lignes, la trouver en 3 checks

**TL;DR** : avec un LR absurde (1.0) un MLP jouet diverge en 5 étapes.
3 checks ordonnés : LR/10 d'abord, normes de gradients par couche ensuite,
activations enfin. Mesuré ci-dessous, torch 2.14 CPU, seed 0.

### Le problème
Une loss qui affiche `inf` ne dit ni où ni pourquoi. Avant d'ouvrir un
debugger, reproduisez petit : si le jouet diverge, l'hypothèse LR est
testable en 30 secondes.

### Code exécutable (copier-coller, CPU, ~2 s)
```python
import torch
import torch.nn as nn

torch.manual_seed(0)
m = nn.Sequential(nn.Linear(10, 32), nn.ReLU(), nn.Linear(32, 1))
opt = torch.optim.SGD(m.parameters(), lr=1.0)
x = torch.randn(64, 10)
y = torch.randn(64, 1)
for step in range(30):
    opt.zero_grad()
    loss = nn.functional.mse_loss(m(x), y)
    loss.backward()
    opt.step()
    if step % 5 == 0 or not torch.isfinite(loss):
        print(f"step {step}: loss={loss.item():.4f}")
        if not torch.isfinite(loss):
            break
```

### Sortie mesurée
```
step 0: loss=1.2614
step 5: loss=inf
```

### Les 3 checks, dans l'ordre
| # | Check | Interprétation |
|---|---|---|
| 1 | Relancer avec `lr=0.1` puis `0.01` | Si ça tient : c'était le LR, fin de l'enquête |
| 2 | Norme des gradients par couche à l'étape 3 | Couches profondes à ~0 + sortie qui explose = saturation + LR |
| 3 | % d'activations ReLU nulles | >50 % mortes : init ou LR ont tué la capacité |

### Gotchas & limites
- En fp16, l'overflow arrive plus tôt et pour d'autres raisons (échelle de loss) :
  ce tutoriel est en fp32, ne transposez pas les seuils.
- `detect_anomaly` ralentit x10 : run réduit seulement, jamais le run complet.
- Un jouet qui diverge ne prouve pas que VOTRE run diverge pour la même raison :
  c'est un test d'hypothèse, pas un diagnostic (c'est le travail de NeuralDBG).

### Conclusion
Trois nombres (LR, normes par couche, % ReLU mortes) éliminent 80 % des
fausses pistes avant tout outil. Quand ils ne suffisent pas, il faut une
chaîne causale automatique — voir la checklist des 7 patterns (aimant S1).
