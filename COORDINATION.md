# COORDINATION — sessions IA simultanées sur kuro-rules

Plusieurs agents touchent ce repo en même temps (`tui.py` fait 1100+ lignes
et a déjà des auteurs multiples). Règles minimales :

1. **Avant de toucher un fichier partagé** (`src/kuro_dashboard/*`,
   `scripts/kuro_*.py`, `tests/test_kuro_*.py`), inscrire son chantier
   ci-dessous avec la date. Pas d'inscription = pas de Feather touch.
2. **Ne jamais reformater** un fichier qu'on ne fait pas évoluer
   fonctionnellement (bruit de diff = conflits).
3. **Tests de la zone touchée avant de finir** (`pytest tests/test_kuro_tui.py`
   pour le TUI, etc.). Les mocks hermétiques sont dans `tests/conftest.py`.
4. **Ne jamais commiter** les fichiers d'un autre chantier (voir Fix1 :
   `git add` toujours ciblé, jamais `git add -A`).

## Chantiers en cours

| Date | Chantier | Fichiers | État |
|---|---|---|---|
| 2026-10-04 | TUI ASCII btop-like (boxes, tri/filtre/sélection, compact) | `src/kuro_dashboard/tui.py`, `tests/test_kuro_tui.py` | actif |
| 2026-10-04 | TUI Textual (sidebar, panneaux, détail) | `tui_textual.py`, `kuro.tcss`, `tests/test_kuro_tui_textual.py` | actif |
| 2026-10-04 | Sync PC→serveur auto | `scripts/Sync-ReposServer.ps1`, `Install-KuroScheduledTask.ps1` | actif |
| 2026-10-04 | OpenClaw agents + couleurs + replica | `agents.py`, `tui.py` (sec_agents, MOOD_COLORS), `kuro_state.py` (replica) | vu en place, auteur autre session |
| 2026-10-04 | Perf TUI : timeout agents 20s→8s (1er refresh) | `agents.py: _openclaw_json` | micro-fix, cache 60 s inchange |

## Notes inter-sessions

- `watch()` est revenu monothread (la version threadee faisait crasher
  l interpreteur sous pytest : sleep global moque + boucle serree). Les perfs
  viennent des caches TTL, pas des threads.
