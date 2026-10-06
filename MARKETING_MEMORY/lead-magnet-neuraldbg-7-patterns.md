# Lead magnet : 7 silent PyTorch failure patterns (checklist)

> Format : PDF 2 pages + repo exemple. Promise : la checklist qui aurait
> sauvé vos 3 derniers trainings. Tout point ci-dessous est un fait établi
> de la pratique PyTorch (R110.1 : rien d'inventé).

## Les 7 patterns

1. **NaN loss d'apparition brutale** — une seule opération instable (division,
   log(0), softmax en fp16) contamine tout le graphe en une étape.
   Check : `torch.autograd.set_detect_anomaly(True)` sur un run réduit.
2. **LR trop élevé + activation saturée** — la perte explose en escalier dès
   les premières étapes, pas en dérive lente.
   Check : diviser le LR par 10 sur 50 étapes ; si ça tient, c'était lui.
3. **Gradients qui s'évanouissent en profondeur** — couches profondes figées,
   seules les dernières bougent (vanishing, typique RNN / très profond).
   Check : norme des gradients par couche à l'étape 100.
4. **ReLU morts en masse** — >50 % d'activations à zéro après init ou gros LR.
   Check : histogramme des activations, pas seulement de la loss.
5. **Oubli de model.train() / model.eval()** — dropout/BatchNorm en mode
   inverse entre train et validation : écart fantôme.
   Check : comparer une forward en train() puis eval() sur le même batch.
6. **Seed et non-déterminisme** — deux runs, deux destins, zéro conclusion.
   Check : fixer `torch.manual_seed` + `PYTHONHASHSEED`, noter les versions.
7. **Données corrompues en silence** — labels décalés, normalisation oubliée,
   fuite train/test : le modèle apprend, mais pas ce que vous croyez.
   Check : visualiser 1 batch réel avant chaque run sérieux.

## CTA
Le debug manuel ci-dessus prend des heures. NeuralDBG l'automatise :
branche PyTorch, hypothèses causales classées par couche et par étape.
Repo : https://github.com/LambdaSection/NeuralDBG — MIT, pip install.
