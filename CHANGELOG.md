# Changelog — kuro-rules

Format: `[MAJOR.MINOR.PATCH]` + git tag `vMAJOR.MINOR.PATCH-kuro` (R19).
`pyproject.toml` version and CHANGELOG entry must match (R91).

## [1.3.0](https://github.com/Lemniscate-world/kuro-rules/compare/v1.2.0...v1.3.0) (2026-10-29)


### Features

* Add Linear integration requirement for tasks to multiple rule documents. ([a9db4dc](https://github.com/Lemniscate-world/kuro-rules/commit/a9db4dc6edd3b8e8444bf61f61be02cd8af0d39c))
* Add milestone checks and versioning scripts ([4fdee28](https://github.com/Lemniscate-world/kuro-rules/commit/4fdee284f11df2bcfc02640a49e89bd506054cfd))
* Add official Linear issue labels and introduce Rule 31 for mandatory codebase context in Linear issues. ([e471520](https://github.com/Lemniscate-world/kuro-rules/commit/e4715203deca7449e27cbae71e493ea42e6b66e9))
* Add project scaffolding, a rules audit workflow, and generate numerous system backup files while updating existing configurations. ([1957ff0](https://github.com/Lemniscate-world/kuro-rules/commit/1957ff0c11aa5fd7f99c076931d6849da13a14c0))
* Add Rule 32 detailing the mandatory team stack, onboarding checklist, and enforcement procedures. ([e894715](https://github.com/Lemniscate-world/kuro-rules/commit/e894715374366f53a0895246f8abcbd7b1ba98b5))
* add rule_103 — Profile README Sync (LambdaSection + Lemniscate-world) ([77c1cf3](https://github.com/Lemniscate-world/kuro-rules/commit/77c1cf3a929f01fbeb219d03501289a526bb0e9a))
* add rules 102, 106, 107 + update AGENTS.md index ([3836063](https://github.com/Lemniscate-world/kuro-rules/commit/38360635756842201daf2d9de859d59734cc0363))
* Add scripts for fixing mojibake and creating mass Google Docs, and update sync log with recent changes. ([4e2c00f](https://github.com/Lemniscate-world/kuro-rules/commit/4e2c00f2a364ea404e4b45e531b9c691b3f3186b))
* added Rules 89, 91, and 93 for NeuralDBG hardening ([a1c5844](https://github.com/Lemniscate-world/kuro-rules/commit/a1c584460280757e4784d95560868dae992364bc))
* auto truth complete - realistic % + mondes + blogs + quotidien ([6115f6d](https://github.com/Lemniscate-world/kuro-rules/commit/6115f6df075718f82780e1a6649e06dd1585b29d))
* auto-generate portfolio HTML from Epingle_Projets.md ([4df05fe](https://github.com/Lemniscate-world/kuro-rules/commit/4df05fea91eadae772368f406032510c4b3fb86c))
* auto-sync README from Epingle (R51/R80) - header + arch + focus line-based ([ec3f6ec](https://github.com/Lemniscate-world/kuro-rules/commit/ec3f6ec82d6d97f62a84a794dd99939bee17c051))
* cerveau LLM Kuro - Ollama cloud uniquement (minimax-m3), OpenRouter dormant ([2bcbd5c](https://github.com/Lemniscate-world/kuro-rules/commit/2bcbd5c81fd57687b2a60caf2d970c439f34b81f))
* **cerveau:** prix versionnes, budgets, P50/P95 ([31d4272](https://github.com/Lemniscate-world/kuro-rules/commit/31d4272bec69e12e51929812f312b5a6ed8a614d))
* CI compliance checker (R30/R76/R101/R39/R64/R91/R85) + unbypassable pre-push hooks installer ([97d137d](https://github.com/Lemniscate-world/kuro-rules/commit/97d137d95d583612789b676ffa97e11eb4b0cd15))
* **ci:** enforcement automatique des regles - garde central quotidien + workflow compliance par repo (R76/R106/R30 + drift manifest) ([129dd17](https://github.com/Lemniscate-world/kuro-rules/commit/129dd1788aca965327d5241618f95692eae8d1ac))
* **dashboard:** TUI btop-like + sync auto PC-serveur + packaging ([281f1d6](https://github.com/Lemniscate-world/kuro-rules/commit/281f1d61f89c40642d42aee63eafb740649b9684))
* **design:** logo lambda genere, titre sombre natif, cartes stats, lignes repos cliquables - R109 applique a KuroPulse ([62c07fb](https://github.com/Lemniscate-world/kuro-rules/commit/62c07fb1f25504f3b0178e975b6cd77773d2c599))
* **design:** panneau KuroPulse redessine - controles custom dessines (R109 Primer) ([ae13745](https://github.com/Lemniscate-world/kuro-rules/commit/ae1374561a3fd30bd6d4d01ba3051c1aa2b27064))
* durcissement Kuro - divergence DB/Epingle, alerte cerveau, ack alertes, pytest ([99b7454](https://github.com/Lemniscate-world/kuro-rules/commit/99b7454a640e871b3583d495fdf9787b55242e8f))
* **finance:** donnees financieres 100% locales R111 - burn/runway/MRR/CAC-LTV (kuro_finance.py) + lead time/velocite/CI/pivots (kuro_metrics.py), endpoints /api/finance + /api/metrics, panneau KuroPulse repare (Dock=Fill, rangees immunisees Recenter, DPI aware, cache icones, re-render conditionnel), section finance desk web, historique ~/.kuro/finance_history.jsonl, anti double-bind API, 27 tests verts ([84a1b89](https://github.com/Lemniscate-world/kuro-rules/commit/84a1b89c8e8fdb12c2d4dbe419433b3988ca5a77))
* **guardian:** auto-diagnostic des echecs par signatures (secret manquant, sous-module fantome, asserts, bandit, lint/formatage, dependances) + auto-reparation des classes sures derriere KURO_AUTO_FIX=1 (format black/isort epingles au repo, fichiers proteges R76), 9 tests ([a3be271](https://github.com/Lemniscate-world/kuro-rules/commit/a3be271aa58f1dab105e4a5d00b977fea8c9a357))
* implement 'Extreme Rigueur' progress tracking system in AGENTS.md ([6b3838c](https://github.com/Lemniscate-world/kuro-rules/commit/6b3838c940570294f1f839fe4bff910944913220))
* implement Rule 30/33 authority and naming conventions (ceo/ scope) ([53a08ab](https://github.com/Lemniscate-world/kuro-rules/commit/53a08ab1bd7c6a8f07ee46c891aa64f2d40a9083))
* implement smart redirector, UTF-8 standard, and pre-commit validation ([2fc0462](https://github.com/Lemniscate-world/kuro-rules/commit/2fc0462499b9df8ddd3e87c0320589c3d707753d))
* Introduce persona-specific rule scopes and an infrastructure progress grid to AGENTS.md. ([edc2db8](https://github.com/Lemniscate-world/kuro-rules/commit/edc2db8c9086831329674d0809de73ea05a1d7c7))
* introduce project classification to conditionally apply the Mom Test and update its enforcement. ([3c2c05b](https://github.com/Lemniscate-world/kuro-rules/commit/3c2c05badf37633ffe7d033b10ba5a5311f062b5))
* Introduce strict project isolation rule and expand `.gitignore` to include reflection and brainstorming files. ([09648c2](https://github.com/Lemniscate-world/kuro-rules/commit/09648c2fad73ffdd4f44bfc1cd91125d9aa81ed3))
* journal des auto-actions Kuro (KURO_ACTIONS_LOG.md) ([ab583d7](https://github.com/Lemniscate-world/kuro-rules/commit/ab583d78fb00d48deca98e40ca8de4d500feead2))
* Kuro intelligence architecture — Sentinel renommé, panneau CI neutre sur portfolio, retrait sync_profile.py redondant ([e455bf6](https://github.com/Lemniscate-world/kuro-rules/commit/e455bf65607b6d63ebefba61ed36544ded235901))
* Kuro Ops global — repair automation + harden SonarCloud (PR [#25](https://github.com/Lemniscate-world/kuro-rules/issues/25)) ([49876c6](https://github.com/Lemniscate-world/kuro-rules/commit/49876c6cee49ddfaaeca8fa82fefbb1a8179e958))
* kuro_doctor - verification sante 9 composants en une commande ([e0974f3](https://github.com/Lemniscate-world/kuro-rules/commit/e0974f30c35e9a203209f33f7a5f752d11314fdd))
* KuroPulse - vraie app desktop native (exe WinForms sombre style gitify) ([b62c1b2](https://github.com/Lemniscate-world/kuro-rules/commit/b62c1b2f8d9809aaac8634a3465ac165ab5bbd77))
* KuroPulse tray app + digest investisseurs + CodeQL 15/15 + skills design vendés ([2de163b](https://github.com/Lemniscate-world/kuro-rules/commit/2de163b4c8baba7ccb03fea434c232561e230db7))
* KuroPulse v1.2 - confort, infos, actions rapides, design fin ([b7d1bb2](https://github.com/Lemniscate-world/kuro-rules/commit/b7d1bb275e6e7e3abbf18345c29c57f1b02adacc))
* **kuro:** sweep securite portfolio (CodeQL+Sonar, forks/archives exclus) ([018aae0](https://github.com/Lemniscate-world/kuro-rules/commit/018aae0a4ecdb5b11055721de41b067152557ee1))
* **omnigraph:** export Epingle-&gt;JSONL + harvest branches (phases 1+2) ([b6e4403](https://github.com/Lemniscate-world/kuro-rules/commit/b6e44039dbb16969ab2a8e838a2ca9b4f6d96567))
* **Phase 1:** alertes Discord + rapport hebdo consolidé ([27e720e](https://github.com/Lemniscate-world/kuro-rules/commit/27e720e89f512937601a6367580ce8a6bbfab92a))
* **Phase 2:** Kuro Radar v1 - veille net hebdo ([9a1388b](https://github.com/Lemniscate-world/kuro-rules/commit/9a1388ba35b708c4ed84030f67111bc3134d675a))
* **Phase 3:** Kuro Advisor - recommandations signaux -&gt; projets ([ba42efb](https://github.com/Lemniscate-world/kuro-rules/commit/ba42efb04c820bc2370d0ef0a0ca481faa0b8461))
* **Phase 4:** API REST Kuro sur kuro.db ([6e2605d](https://github.com/Lemniscate-world/kuro-rules/commit/6e2605d814154d57b496e19ddaaa6ae775e6131d))
* **Phase 5:** Desk temps réel servi par l'API Kuro ([a61b382](https://github.com/Lemniscate-world/kuro-rules/commit/a61b3823057c7b8e801af87b3794c21719b15e27))
* **pilotage:** P-ID + label kuro-auto + commandes / + automerge garde + watchdog + budgets + vacances + token prive ([0d9ac69](https://github.com/Lemniscate-world/kuro-rules/commit/0d9ac6956e67ace2466ef042d6240e57daec81b8))
* portfolio automation — GitHub Action (auto-sync on push), pre-commit hook, post-session checker with --fix ([ecfec50](https://github.com/Lemniscate-world/kuro-rules/commit/ecfec503d0c071e7c6ddc336980389c8e506b2bd))
* **pr-agent:** lit les revues bots, applique les suggestions (label kuro-auto), explique sur Discord ([935f13c](https://github.com/Lemniscate-world/kuro-rules/commit/935f13c9edbcf3882c51122cb506c0a9be28c70e))
* **projects:** add Flow-Regulator, OpenMind, Prompt2Model to portfolio (R80) ([59e3c13](https://github.com/Lemniscate-world/kuro-rules/commit/59e3c138ed6be1ae9abf99b462ca1d937a41e2f5))
* **R102:** pyramide tests 70/20/10 + hermetic + 0% bloquant ([8d55788](https://github.com/Lemniscate-world/kuro-rules/commit/8d557885b13ce5d951bd027c508983d73901f912))
* **R13b:** 2-Year Sub-Plan on Improvement mandatory ([7a89445](https://github.com/Lemniscate-world/kuro-rules/commit/7a89445541bda0346acb42b0e48e79b61354a08d))
* **R2:** explicit open-source utility / build useful first -&gt; R2 N/A ([ad87c39](https://github.com/Lemniscate-world/kuro-rules/commit/ad87c390c1d0967ffdeabebb4037eb12168c6209))
* R5 70%/80% + pyramide hermetic + anti-death robot ([5a1dadf](https://github.com/Lemniscate-world/kuro-rules/commit/5a1dadf5d71c89e5543eb5cd50b2c790b0e91659))
* **R69/R75:** add Continuous Tech Scout mandatory for HIGH Technical risk ([7630f02](https://github.com/Lemniscate-world/kuro-rules/commit/7630f02185e25a3b1dc22c1a3f8f310942e213bd))
* **R72/R108:** Impeccable gate permanent - detect obligatoire toute UI, CI step, re-eval concurrent 2027-02 ([94a35bd](https://github.com/Lemniscate-world/kuro-rules/commit/94a35bd86131f465a1c997aa18661af48c385ee4))
* **radar:** source Exa - veille semantique web via Agent Reach/mcporter quand disponible localement, fallback silencieux en CI (mcporter .CMD via shell, parse stdout sans exiger exit code) ([d9e0437](https://github.com/Lemniscate-world/kuro-rules/commit/d9e04372f97f647d590978f4dc8a4e3270d7d477))
* resolve git corruption, update sync-rules redirector generation, update rule_93, add rule_101, and sync AGENTS.md across 43 projects ([a2b9719](https://github.com/Lemniscate-world/kuro-rules/commit/a2b971960e2c8bb6ea09a78c0ead2cbd7f1e6a98))
* RULE 110 Blogging (verite d'abord, structure, distribution) + Three.js dans R109 + skills vendés BLOGGING ([6b6ab6d](https://github.com/Lemniscate-world/kuro-rules/commit/6b6ab6d209eb89d004b0b866702031ff818322b2))
* **rules:** add R105 multi-repo & monorepo governance, harden sync script for R87 ([0447150](https://github.com/Lemniscate-world/kuro-rules/commit/04471501b85a9952697a773601716f3bb6d3caa5))
* **rules:** add R113 GitHub Discovery Protocol (audit 2026-09-17: 9 repos metadata, release v1.3.2, traffic baseline) ([0a19538](https://github.com/Lemniscate-world/kuro-rules/commit/0a1953831807e70c23e8e39da41db5927e570fc6))
* **rules:** add R85 portfolio completeness verification - prevents missing projects in Epingle_Projets.md ([108c63b](https://github.com/Lemniscate-world/kuro-rules/commit/108c63b0da22cedd827e473d3f4afc2036a8e9a4))
* **rules:** R112 standard tooling - Agent-Reach + codebase-memory-mcp obligatoires sur chaque nouveau projet, ancre physique dans PROJECT_SCAFFOLD ([28d1284](https://github.com/Lemniscate-world/kuro-rules/commit/28d1284ed58c07a83cf698d1c85ce08c5fdbc667))
* **rules:** R86 Kuro Guardian Protocol + deep portfolio analysis - SESSION_SUMMARY parsed, 37 projects updated with real data, KuroGuardian project created ([d6dfd56](https://github.com/Lemniscate-world/kuro-rules/commit/d6dfd56d5642ecfc0d35f3e8ef477d2b64e3e25f))
* **S1b:** inject_analytics GoatCounter conditionnel (analytics.txt a la racine repo) - 17 pages testees, 0 trace si absent ([2c62f79](https://github.com/Lemniscate-world/kuro-rules/commit/2c62f79d52b826c67a749645ff45239423503ae2))
* **S1:** og:image Pillow + sitemap/robots + RSS + quickstart utilitaires + fix contraste AA (muted 4.2-&gt;5.1) ([34a39c7](https://github.com/Lemniscate-world/kuro-rules/commit/34a39c7d2bf612ee2d980d698b6c86b611892876))
* securite auto (Dependabot 15/15 repos), robot 24/7, R109 design adaptatif, apercu robot dans Desk ([4623b3c](https://github.com/Lemniscate-world/kuro-rules/commit/4623b3ce87cfa9eeb899ef32fdba5935655f6376))
* **skills:** detect_git_repositories accepte un docs_dir parametrable (requis pour CI /home/runner/Documents) ([720b74c](https://github.com/Lemniscate-world/kuro-rules/commit/720b74c2320f0f80f634a2ff0df2b0d6dbf80e2d))
* **skills:** skills verifies par preuves - detection auto (langages + technos via manifests/workflows), score volume/penetration/activite/profondeur CI+tests, bloc README entre marqueurs, skills.json piste d'audit, etape robot kuro.yml, 10 tests ([cd13bd1](https://github.com/Lemniscate-world/kuro-rules/commit/cd13bd199e728505b944b759bbbd8e8afc11f647))
* **strategy:** couche strategique - digest hebdo fusionnant finance+execution+OKR+pipeline avec decisions deterministes (R2/R111 liees), suivi concurrents dans le radar, endpoint /api/strategy, ThreeUI Community comme standard design web dans le scaffold, 10 tests ([47cfd6a](https://github.com/Lemniscate-world/kuro-rules/commit/47cfd6a8c06d1f50b1144a35d4eee015ff89b6b7))
* sync Discord -&gt; Epingle helper (messages par projet) + guide export ([aff114c](https://github.com/Lemniscate-world/kuro-rules/commit/aff114ca9cb867fa21dfece8ce674d614b981375))
* sync Rule 33 to master rules ([2f7d088](https://github.com/Lemniscate-world/kuro-rules/commit/2f7d088e0e2c79977521b34e8976d5e6a31bd7d2))
* sync Rules 25-32 (Linear automation, labels, branch convention, codebase context, team stack) to master rules ([0bf081b](https://github.com/Lemniscate-world/kuro-rules/commit/0bf081b84a2ad2c041e55083569f0d653a207dbd))
* **sync:** deploiement workflow compliance + manifest par repo a chaque synchro ([6cc7e36](https://github.com/Lemniscate-world/kuro-rules/commit/6cc7e365397e662e54bfb6c36960b9658f886e7f))
* truth daily - audit factuel + portfolio enrichi git + cron 05:00 UTC + Windows Task ([c36bada](https://github.com/Lemniscate-world/kuro-rules/commit/c36bada5b6d1e77521d849957e5eb5a196694c30))
* un seul robot Kuro — fusion truth-daily + sync-portfolio + ci-guardian ([b3ed37a](https://github.com/Lemniscate-world/kuro-rules/commit/b3ed37a4d90ca0d21dd1b84b997c21fc0776cc73))
* update rules for portfolio auto-sync — R80 (+generate_portfolio workflow), R103 (+dashboard URL), R85 (+HTML verification), Epingle liens ([ba8aafa](https://github.com/Lemniscate-world/kuro-rules/commit/ba8aafa95bc9ef66efd045f13394a9ef3e4337a0))
* **validation:** add R84 template package for all projects - formulas, dashboard, analytics, docs ([199bda5](https://github.com/Lemniscate-world/kuro-rules/commit/199bda5b5a0d47224a569e21e858fa0014d8b16b))
* workflow kuro.yml + doc architecture à jour ([a56a662](https://github.com/Lemniscate-world/kuro-rules/commit/a56a662f6157c6cbe595939a7b46a7ee1fddfd08))
* **xenon:** box 7 SEO + digest STRAT/SEO en compact (garde 26 rangs) ([818c935](https://github.com/Lemniscate-world/kuro-rules/commit/818c9359a39960f67d8a6f895cebac1a9112b263))
* **xenon:** boxes 8 FINANCE + 9 COMPUTE + digests compact ([b147cd0](https://github.com/Lemniscate-world/kuro-rules/commit/b147cd0d17149235015559e7809200fd1b108010))
* **xenon:** boxes 8 FINANCE + 9 COMPUTE + digests compact (cerveau/marketing) ([a5695d1](https://github.com/Lemniscate-world/kuro-rules/commit/a5695d179ad08610f1c7bbdcfa9b6ea6461a3fe4))
* **xenon:** cerveau serveur vivant via miroir gateway ([b6e158d](https://github.com/Lemniscate-world/kuro-rules/commit/b6e158dc26dfb6eabb78021d408088e124add1eb))
* **xenon:** cerveau serveur vivant via miroir gateway + shims env ([7b1774f](https://github.com/Lemniscate-world/kuro-rules/commit/7b1774f911619356189f01fc7b9565ca29f178c9))
* **xenon:** compact voit tout (digests agents/finance/compute, budget 31) ([6d32137](https://github.com/Lemniscate-world/kuro-rules/commit/6d3213762162428c0bd898cfd0f33f845a901b99))
* **xenon:** compact voit tout (digests agents/finance/compute) ([64a063d](https://github.com/Lemniscate-world/kuro-rules/commit/64a063d4bc54f10e07fbe789d05ac277d0bbcad0))
* **xenon:** compact voit tout + non-bloquant (agents fond) ([ceba335](https://github.com/Lemniscate-world/kuro-rules/commit/ceba3356b473cbb1a2ff7f908ae4cc578a29fe32))
* **xenon:** methode USE + box strategie mensuelle ([460cef5](https://github.com/Lemniscate-world/kuro-rules/commit/460cef52f9308147f14b3b6ef74911bb06c862cd))
* **xenon:** methode USE + box strategie mensuelle ([2f07eea](https://github.com/Lemniscate-world/kuro-rules/commit/2f07eea00e67c0996b1296c53598ae1fcb6af475))
* **xenon:** vague2 cerveau + vague3 ops (doctor, legs-watch, stats, plugins) ([d29fd02](https://github.com/Lemniscate-world/kuro-rules/commit/d29fd02cd89790e85dd657f4ce0b00236c766603))
* **xenon:** vue complete &lt;=48 lignes (console 170x48) ([42ab134](https://github.com/Lemniscate-world/kuro-rules/commit/42ab1348c4cd906f06cf936e121b4c4a473cce07))
* **xenon:** vue complete &lt;=48 lignes (finance 1 ligne, shrink PROC) ([7fac955](https://github.com/Lemniscate-world/kuro-rules/commit/7fac9557e4c9bffac26fcea77e5997311418bdaf))


### Bug Fixes

* argument token manquant sur comment_issue ([5678540](https://github.com/Lemniscate-world/kuro-rules/commit/5678540dc849f38aa86bb23f1fb037aae01f2281))
* chemin tests dans kuro.yml (checkout en sous-dossier) ([0a0a185](https://github.com/Lemniscate-world/kuro-rules/commit/0a0a18535f77203b7935738b54f4c7c417926e8c))
* chemins env CI + formule convergente (cible absolue, pas borne) ([7848ca8](https://github.com/Lemniscate-world/kuro-rules/commit/7848ca86db3665f3a8ebbab22631131beb7c0413))
* CI Guardian robot + repair 3 CI failures (R84/R86) ([c10c8b5](https://github.com/Lemniscate-world/kuro-rules/commit/c10c8b52593d6a92c4f7ef3360cd24f9d60f8150))
* CI truth reel - clone repos + blog parse unique (60) ([be5ba07](https://github.com/Lemniscate-world/kuro-rules/commit/be5ba07be05fea13ebeece236574986490939ce5))
* ci_guardian escalade en issue quand le rerun est impossible ([43d07a0](https://github.com/Lemniscate-world/kuro-rules/commit/43d07a0a659cb61680cc7537005895aaba5bbae0))
* **ci:** R76 protected file check using grep pattern (resolves false-positive in kuro-rules) ([e32c88d](https://github.com/Lemniscate-world/kuro-rules/commit/e32c88d855d541b3c73367411c5d0e1401252c1e))
* **ci:** reparer Rules Spec + Kuro — artefacts vers branche kuro-audit ([aaa2438](https://github.com/Lemniscate-world/kuro-rules/commit/aaa2438a6aee0286f992dfe044067a951f9bf684))
* **ci:** tests portables Linux + R39 sans faux positifs ([5136bc0](https://github.com/Lemniscate-world/kuro-rules/commit/5136bc0243a152029decf9cda0246de0b08df450))
* **codeql:** HMAC-SHA1 via hmac.digest (octets OAuth identiques) ([d976406](https://github.com/Lemniscate-world/kuro-rules/commit/d976406dc5e0e036172f360445dfbe3847308bb0))
* **design:** panneau colonne centree 430px type gitify - ordre Dock inverse corrige, lignes owner-drawn, statut CI fraiche via kuro-rules/ci-status.json ([4d6dc0f](https://github.com/Lemniscate-world/kuro-rules/commit/4d6dc0f8bbb3dd2a25259b355f11b21e1374a5e3))
* **discord:** anti-spam sentinelle (dédup échecs inchangés) + .env.example documenté ([161669b](https://github.com/Lemniscate-world/kuro-rules/commit/161669bba95a81bf316e66ce2a3fc8fcd95ae4fd))
* escape sequence in pre-push hook script ([d24d9df](https://github.com/Lemniscate-world/kuro-rules/commit/d24d9dfc688526ba8df6c5933abf48307297d32a))
* generate_blog 7j dynamic + slug commit date ([1df95eb](https://github.com/Lemniscate-world/kuro-rules/commit/1df95eb99f50a8fb688c8849d896bc13d2922486))
* generate_portfolio - dynamic section count + full FR month translation (R80) ([5f83de5](https://github.com/Lemniscate-world/kuro-rules/commit/5f83de5ab245b06e7a8264c619d4adafb9b6bd94))
* generate_portfolio truth_enrich skip quand DOCS_DIR absent (CI) ([5263b7b](https://github.com/Lemniscate-world/kuro-rules/commit/5263b7bb1dc4806d6cba8ac449429072b42020b1))
* **gui:** supprimer les fenetres console fantomes - CREATE_NO_WINDOW sur tous les subprocess git lances sous pythonw (api metrics ~130 appels/5min, dashboard ~90/min), powershell EnsureApi cache ([fc4ab04](https://github.com/Lemniscate-world/kuro-rules/commit/fc4ab04237f2e47febddad1a57495cfc9c611c31))
* **hooks:** template pre-push smart stack-detect + installer consolide (fini Oblivion copie-collee R89) ([439ad84](https://github.com/Lemniscate-world/kuro-rules/commit/439ad849b70a401a235c3b83f5e523e88cfa9370))
* modele OpenRouter stealth/ox-alpha + parsing raisonnement (content null si tokens epuises) ([008ab35](https://github.com/Lemniscate-world/kuro-rules/commit/008ab35f3f1caf121c56083544bfb7062b57c8a3))
* ordre du cerveau - OpenRouter principal, Ollama cloud en fallback ([130c85f](https://github.com/Lemniscate-world/kuro-rules/commit/130c85f2a34cfb07c1accbb7dadff8fe32c18125))
* portfolio generator audit - 60 projets, external section, liens, SEO, nav, filtre, stats 7 cats, per-section Epure, discord ([5e369bc](https://github.com/Lemniscate-world/kuro-rules/commit/5e369bc553406de57a0092ed04047f53a472c74f))
* pushes du robot resilients (pull --rebase avant push) ([60b9550](https://github.com/Lemniscate-world/kuro-rules/commit/60b95503c455bab3bb076685d9a2d057f978ccf7))
* **R76:** untrack protected files (SESSION_SUMMARY, acquisition_tracker, decision-memo) + add to .gitignore ([033a8fa](https://github.com/Lemniscate-world/kuro-rules/commit/033a8faa849492103992310ad6efc314d34c694e))
* raw string chemin git.exe (SyntaxWarning) ([0dfc3df](https://github.com/Lemniscate-world/kuro-rules/commit/0dfc3df6bfd235895035ef62f01f4e7ad2437a28))
* realistic pct auto - 16 corrections factuelles (R3) ([e77bc8d](https://github.com/Lemniscate-world/kuro-rules/commit/e77bc8d8869d81d7f1e1fc9292003f880c9509b9))
* **release:** release-please ne casse plus CI a chaque release ([4d91eee](https://github.com/Lemniscate-world/kuro-rules/commit/4d91eee1e5a5f066ed0f8b4501e3a3f7e0535f07))
* remove SYNC_BACKUPS from tracking ([a57bbd4](https://github.com/Lemniscate-world/kuro-rules/commit/a57bbd446e1f2709d9fb3961ea4fdfbe69f10ffa))
* **rules:** expand R76 with comprehensive protected file patterns ([5630af9](https://github.com/Lemniscate-world/kuro-rules/commit/5630af9816dc4ae77c2ebab5a72bcdbf69739387))
* **rules:** trailing newline masters (end-of-file-fixer churn guard) ([64e583d](https://github.com/Lemniscate-world/kuro-rules/commit/64e583d8c222a16b08f8833271950378a97d50ec))
* **sec:** confine les chemins CLI sous le repo (S8707 vague A) ([a8b75cb](https://github.com/Lemniscate-world/kuro-rules/commit/a8b75cb2ceae5b482bc5a2e99f71328ea39b7786))
* Sentinel ignore les runs fantômes (&gt;45j) - logs expirés ou workflows supprimés ne sont plus comptés en échec ([77759b5](https://github.com/Lemniscate-world/kuro-rules/commit/77759b5a99be49bc0cd78b8c0a49ca7d1f94cb99))
* **server:** epingle URL parse strict + promote tolerant sans systemd ([fa2c131](https://github.com/Lemniscate-world/kuro-rules/commit/fa2c131a24e048d9c625e604b18ada34e1409186))
* **sonar:** 10 issues PR[#5](https://github.com/Lemniscate-world/kuro-rules/issues/5) (complexite, constantes, NOSONAR chemin constant, codes retour) ([4bcae2d](https://github.com/Lemniscate-world/kuro-rules/commit/4bcae2d44ee5ae21cee3241f808a280bf4fdef86))
* **sonar:** 11 bugs fiabilite (promises, mort, labels) ([ab887c9](https://github.com/Lemniscate-world/kuro-rules/commit/ab887c953be55693dff3db01ecde07e8d2a8a262))
* **sonar:** NOSONAR valide, contrainte nom rapport, pip only-binary, asserts separes ([aaf38a0](https://github.com/Lemniscate-world/kuro-rules/commit/aaf38a0350a65839fbe81315dc5b559a3a8bdc81))
* support --epingle param for CI, fix GitHub Action paths ([7d1e29b](https://github.com/Lemniscate-world/kuro-rules/commit/7d1e29b3046349574ef23abdad4b836072ee4a55))
* **sync:** honor projects.txt as sync authority ([9b0a70c](https://github.com/Lemniscate-world/kuro-rules/commit/9b0a70ce29f86c710610f27bbefea016f7ec5e1a))
* **sync:** newline final du manifest (end-of-file-fixer cassait Pre-commit a chaque synchro) ([#4](https://github.com/Lemniscate-world/kuro-rules/issues/4)) ([f41d0ac](https://github.com/Lemniscate-world/kuro-rules/commit/f41d0ac47bc4c1d1ff7334fa404d3942af25049c))
* truth-daily CI paths via env overrides (KURO_RULES_DIR/LEMNISCATE_DIR) ([ce6f755](https://github.com/Lemniscate-world/kuro-rules/commit/ce6f755f9a747bc411194ce8722273c3172dc962))
* User-Agent navigateur pour webhooks Discord (403 python-urllib) ([f0b1fdd](https://github.com/Lemniscate-world/kuro-rules/commit/f0b1fddcfc3414e38584c9059badbb10a15af790))
* **xenon:** cerveau honnête + TUI 100% coverage ([14a5ac9](https://github.com/Lemniscate-world/kuro-rules/commit/14a5ac95b64c1718ae571c3563880f1cf7fd2c11))
* **xenon:** cerveau honnête + TUI 100%% coverage (local OK, coûts, cache, TOP amorcé) ([aa09db5](https://github.com/Lemniscate-world/kuro-rules/commit/aa09db522a919676a5d119be615ac93bcfa70ce7))
* **xenon:** compact non-bloquant (agents en fond, import shutil restaure) ([7db2e84](https://github.com/Lemniscate-world/kuro-rules/commit/7db2e84d7ce601402d259acd6388141637339ff3))
* **xenon:** finitions TUI (panneaux Textual 6/7, note 1er snapshot) ([7419122](https://github.com/Lemniscate-world/kuro-rules/commit/7419122131f91e94294b79f484656f86c4b64a00))
* **xenon:** parse la date **Date**: du cron SEO serveur ([3d0fa3d](https://github.com/Lemniscate-world/kuro-rules/commit/3d0fa3de89f04125501272c2e51971d71703aeea))
* **xenon:** retire le web, 100% TUI (revert panneau Strategie/SEO + /api/seo + CSS fluide) ([41872f3](https://github.com/Lemniscate-world/kuro-rules/commit/41872f38f67b30517977b3f55de384fab11cd0b5))
* **xenon:** shrink large+empile (titres numerotes, sections sidebar) ([848cc33](https://github.com/Lemniscate-world/kuro-rules/commit/848cc33f6225baeaed9c5379337671ba2f729636))
* **xenon:** shrink large+empile pour console 48 lignes ([bf737bb](https://github.com/Lemniscate-world/kuro-rules/commit/bf737bbc11eca8f7b0bd614445f38c59ed97b829))
* **xenon:** timeout OpenClaw 6s-&gt;12s + garde R116 ([9336466](https://github.com/Lemniscate-world/kuro-rules/commit/933646696d8a55f6f012e7a5109fefea05bab707))
* **xenon:** timeout OpenClaw 6s-&gt;12s + garde R116 ([4052d1c](https://github.com/Lemniscate-world/kuro-rules/commit/4052d1cca259d2f2f934dcef3af6661b42ee9c18))

## [1.2.0] — 2026-10-13

### Added — recurrence guards (nothing relies on memory)
- `templates/git-hooks/commit-msg.sh` : conventional-commits hook (warn by
  default, `CONVENTIONAL_STRICT=1` to block). release-please depends on it.
- `scripts/install_hooks.py` : deploys `pre-push` + `commit-msg`, `--upgrade`
  replaces kuro-owned hooks only (8 foreign customs left untouched fleet-wide).
- kuro-rules dogfoods release-please (`release-please-config.json` generic /
  `VERSION`, manifest, workflow).
- `scripts/fleet_sync_scheduled.ps1` + `KuroFleetSync` Saturdays 05:00 :
  regenerate + sync + hooks upgrade + snapshot refresh, logged.
- `VERSIONING.md §4b` : guard table.
- Fleet deploy executed: 4663 file syncs, release workflows 5 → 35 OWNED
  repos (17 remaining are EXTERNAL/UNKNOWN forks, correctly excluded per R87).

### Tests
- `test_versioning.py` extended (hooks marker, dogfood, automation wiring).

## [1.1.0] — 2026-10-13

### Added
- `VERSIONING.md` : fleet version governance (one version source per product,
  CHANGELOG mandatory, release-please standard, enforcement ladder).
- `templates/release-please{,-config-node,-config-python,-config-rust,-config-generic}.yml/json`
  + `templates/release-please.yml` : fleet release automation templates.
- `sync-rules.ps1` : deploys release-please workflow (always-on) + config and
  manifest (only if missing, type auto-detected, manifest seeded from current
  version) to OWNED repos.
- `templates/kuro-compliance.yml` : R91-fleet job (warning, `VERSIONING_STRICT=1`
  to fail).
- `scripts/inventory_versions.py` : read-only fleet audit (`--csv`,
  `--markdown`), `FLEET_VERSIONS.md` tracked snapshot (52 tracked, 29 no
  version, 45 no CHANGELOG, 47 no release workflow, 41 zero `v*` tags).
- `VERSION_TEMPLATE` retired (pointer to `VERSIONING.md`).

### Tests
- `test_versioning.py` (7) — configs, workflow, compliance job, snapshot.

## [1.0.0] — 2026-10-13

### Added
- `scripts/generate_targets.py` : canonical generator (`--dry-run` by default,
  `--check` for CI, `--apply` to write). Replaces symlink-only distribution.
- Multi-format targets from `rules/rule_*.md` : `AGENTS.md`, `CLAUDE.md`,
  `GEMINI.md`, `.cursorrules`, `.windsurfrules`, `AI_GUIDELINES.md`,
  `copilot-instructions.md`, `.cursor/rules/*.mdc`, `.agents/rules/*.md`,
  `.cursor-plugin/marketplace.json`.
- `rules/_metadata.yaml` : per-rule `scope` (company/team/service),
  `priority`, `status` (active/draft/deprecated), `trigger` (always/auto/manual),
  `paths`/`globs`, `description`. Inheritance `company -> team -> service`.
- `VERSION` : single version source, embedded in generated headers.
- `SPEC.md` : rules vs runbooks vs memories contract (+ validation rules,
  memory frontmatter, migration path). `runbooks/` (with `sync-rules.md`),
  `memories/` (with template + first lesson).
- `scripts/check_rule_spec.py` : hard errors on metadata/runbooks/memories,
  migration warnings on legacy rules.
- `.agents/SCOPING.md` + `.agents/local/` (gitignored personal overrides).
- `scripts/bench_rules.py` : 10/10 controlled mini-benchmark, offline.
- `.github/workflows/kuro-rules-spec.yml` : blocking CI (drift + spec + bench).
- `sync-rules.ps1` : deploys `CLAUDE.md`/`GEMINI.md` + `.cursor/rules`,
  `.agents/rules`, `.cursor-plugin`; step 1 delegates to the generator.
- `install.sh` / `install.ps1` : copy generated targets (no symlinks by
  default), regenerate first, convert legacy symlinks.

### Tests
- `test_generate_targets.py` (9), `test_rule_spec.py` (7),
  `test_scoping.py` (5), `test_bench_rules.py` (2) — 23 new, all green.
- `audit-rules.py --mode repo` green; `ruff` clean on touched files.
