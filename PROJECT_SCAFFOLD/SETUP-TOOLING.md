# Standard tooling — à activer à la création du projet (R112)

Ce template hérite des deux capacités standard de lambda-Section. À la
création du projet depuis ce scaffold :

## 1. Mémoire structurelle (codebase-memory-mcp)

```powershell
codebase-memory-mcp cli index_repository '{"repo_path": "<chemin du repo>", "project": "<nom du repo>"}'
```

- Auto-index actif sur la machine principale : l'index se crée aussi tout seul
  à la première connexion d'agent.
- Optionnel (équipe) : committer `.codebase-memory/graph.db.zst` pour que les
  co-équipiers sautent le réindex.
- Explorer via le graphe (`search_graph`, `trace_path`, `get_architecture`)
  avant tout grep massif.

## 2. Accès internet (Agent-Reach)

```powershell
agent-reach doctor
```

- Canaux zéro-config déjà actifs machine-wide : web (Jina), Exa, RSS,
  YouTube, GitHub, V2EX, Bilibili search.
- Toute veille/recherche (R69, R75) passe par ces canaux.
- Canaux à login : uniquement sur demande explicite + compte dédié.

## Vérification avant de commencer

- [ ] `codebase-memory-mcp cli index_status` → projet présent
- [ ] `agent-reach doctor` → ≥ 4 canaux verts
