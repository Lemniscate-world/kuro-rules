## RULE 124: REA Reverse-Engineering Trigger — quand et comment appeler REA — MANDATORY (conditionnel)

### Rule

Tout agent Kuro dont la tâche dépend d'un **binaire livré ou d'un paquet sans
source** doit passer par REA (MCP `rea` ou CLI `npx -y rea-agents@latest`)
AVANT toute hypothèse sur le comportement. Réf : https://github.com/morluto/rea

**Déclencheurs (un seul suffit) :**

- Chemins/extensions : `.asar`, `.apk`, `.dex`, `.exe`/`.dll`/`.so` sans
  source, firmware, captures `.har`, bytecode EVM explicite.
- Formulations : « comment [produit] fait X », « cloner le comportement de »,
  audit d'une app installée, comparaison de versions binaires, feature
  d'un concurrent à reproduire (R87 Ownership Intelligence, R69 Harvester).
- **Anti-déclencheur :** repo source complet → codebase-memory, jamais REA
  (le skill l'interdit : analyse source ordinaire = outils repo normaux).

**Routage — premier outil selon la cible :**

- ASAR / arbo Electron → `analyze_javascript_application` (résumé d'abord
  si taille inconnue ; ex. vérifié : Capacities 315 Mo = timeout en full →
  ciblé/extrait, pas full).
- APK → `inspect_android_package`, puis `search_android_classes` /
  `inspect_android_method` (moteur jadx-headless-mcp requis).
- Assembly PE/CLI managé → `inspect_managed_artifact` (zéro moteur externe).
- Page web (navigateur déjà ouvert) → `list_browser_targets` +
  `inspect_web_page` (Chrome `--remote-debugging-port=9222`).
- Natif (`.exe`/`.so`, Dart `libapp.so`, etc.) → `open_binary` + provider
  Ghidra/Hopper/IDA. `trace`/`decompile` natif refusent proprement sans
  provider : ne jamais les appeler sur un asar.
- Preuves : chaque conclusion cite ses Evidence IDs et ses limites
  (observations vs inférences vs inconnues) dans le finding ledger — entrée
  directe pour R115 Validation Pipeline. Runtime = jamais d'analyse statique
  présentée comme exécution observée.

**Prérequis machine principale (vérifiés 2026-10-11) :**

- ✅ Node 24 + MCP `rea` (`opencode.jsonc`, enabled) + skill
  `reverse-engineer-anything` v37.
- ✅ `REA_JADX_MCP_JAR` persisté (variable utilisateur) + jadx 1.5.6 +
  JDK 21 → APK OK sans autre install.
- ❌ Hopper, IDA MCP, `adb`, Wakaru (Linux-only, pas de `recover-javascript-sources` sur Windows).
- ✅ Ghidra 12.1.4 (scoop/extras, `GHIDRA_INSTALL_DIR` persisté) + JDK 21 →
  natif OK vérifié (`search` whoami.exe → `logonid` @ 0x14000e7b8).
- Session CDP Chrome : à la demande uniquement.

### Verification

```
ACTION: tâche à déclencheur REA :
VERIFY: 1. `rea doctor --target <cible>` d'abord (succès ou remédiation notée)
        2. conclusions liées à des Evidence IDs + limites explicites
        3. asar >100 Mo : résumé/ciblé, jamais full aveugle
        4. cible ambiguë (« mon app ») : question posée, pas d'app exemple choisie
```

### Enforcement

IF une conclusion porte sur un binaire livré sans Evidence ID REA :

- STOP, refaire via le routage ci-dessus, logger les preuves (R115)

IF `trace`/`decompile` échoue `capability_unavailable` sur un asar :

- STOP, c'est natif-only : basculer sur `analyze_javascript_application`

IF un provider manque (Ghidra/JADX/CDP) :

- noter la remédiation exacte du doctor, continuer le travail supporté,
  reprendre après réparation (pas de setup répété à l'aveugle)

---
