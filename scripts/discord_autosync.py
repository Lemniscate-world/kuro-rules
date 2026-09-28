#!/usr/bin/env python3
"""discord_autosync.py — Alignement total auto, à chaque run (R80/R85/R105/R93).

Ce que ça fait (idempotent, jamais destructif par défaut) :
  1. MANQUANTS : crée catégories/salons PROD (Actif/Validation) + IDEA (Recherche/Prototypage
     non-archive/non-externe/non-labo) manquants. IDEA adopte le salon existant si slug match
     (#sybil, #thanatos...) au lieu de créer un doublon #idea-*.
  2. INCORRECTS : corrige topic/parent des salons gérés (merge par nom exact, comme sync).
  3. RENAMES : renomme UNIQUEMENT via kuro_discord_rename.local.json {old: new} explicite
     (ex: curly apostrophe, typo). Jamais de rename auto sans map. --apply-rename requis.
  4. DOUBLONS : liste les collisions (ex: #gs-solutions vs #proj-g-solutions) + garde
     EXISTANT non géré. Suppression seulement via retire-ours (SEC*/proj-* stale).
  5. CHAQUE FOIS : conçu pour kuro_automate.py --daily (dry-run) + --full (apply créations+fixes,
     jamais rename/delete sans flag explicite).

Usage :
  python scripts/discord_autosync.py --dry-run            # défaut, lecture seule
  python scripts/discord_autosync.py --apply              # crée manquants + fixe topics/parents
  python scripts/discord_autosync.py --apply-rename       # renomme selon rename map (+ dry-run d'abord)
  python scripts/discord_autosync.py --guild ID           # override DISCORD_GUILD_ID

Maps :
  kuro_discord_map.local.json      : adoption {Projet: #salon, Section: Cat} (ta structure gagne)
  kuro_discord_rename.local.json   : {vieux_nom_salon: nouveau_nom_salon} (sans #, slug Discord)

Zero dépendance, cross-platform. Secrets jamais loggés.
"""
import json
import os
import sys
import unicodedata
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = Path.home()
DOCS = Path(os.environ.get("DOCS_DIR", str(HOME / "Documents")))
KURORULES = Path(os.environ.get("KURO_RULES_DIR", str(DOCS / "kuro-rules")))
SCRIPTS = KURORULES / "scripts"
EPINGLE = KURORULES / "Epingle_Projets.md"
MAP_FILE = KURORULES / "kuro_discord_map.local.json"
RENAME_FILE = KURORULES / "kuro_discord_rename.local.json"

sys.path.insert(0, str(SCRIPTS.resolve()))
import kuro_discord as kd

IDEA_STATUS = ("recherche", "prototypage")
SKIP_IDEA = ("archive", "externe", "outil")


def load_rename():
    try:
        d = json.loads(RENAME_FILE.read_text(encoding="utf-8"))
        if not isinstance(d, dict):
            return {}
        return {k: v for k, v in d.items() if not k.startswith("_")}
    except Exception:
        return {}


def idea_desired(all_projects, struct_map):
    """[(cat, chan, topic, projet)] pour idées : adopte l'existant via map, sinon idea-<slug>."""
    out = []
    for p in all_projects or []:
        st = (p.get("status") or "").lower()
        if st not in IDEA_STATUS:
            continue
        if p.get("external_section"):
            continue
        name = p.get("name", "")
        # Labo pur : reste dans le hub, jamais de salon par recherche
        sl = kd.slug(name)
        from auto_place import find_labo_by_slug  # local, zero dep circulaire ok (même dossier)
        try:
            if find_labo_by_slug(sl):
                continue
        except Exception:
            pass
        # Adopté d'abord (#sybil, #thanatos si mappé ou slug exact connu plus tard)
        chan = kd.channel_name(name, struct_map) if st in ("actif", "validation") else None
        adopted = (struct_map.get("channels", {}) or {}).get(name)
        if adopted:
            chan = adopted.lstrip("#")
        else:
            chan = "idea-" + sl[:90]
        # Catégorie adoptée
        cat = kd.category_name(p.get("section", ""), 0, struct_map)
        topic = ("IDEA %d%% %s — %s" % (p.get("pct", 0), p.get("status"), p.get("desc")))[:1024]
        out.append((cat, chan, topic, name))
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Alignement Discord total (manquants+fixes+renames)")
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--apply", action="store_true", help="Crée manquants + fixe topics/parents (ni rename ni delete)")
    ap.add_argument("--apply-rename", action="store_true", help="Renomme selon kuro_discord_rename.local.json")
    ap.add_argument("--guild", default=os.environ.get("DISCORD_GUILD_ID", ""))
    ap.add_argument("--epingle", default=str(EPINGLE))
    args = ap.parse_args(argv)
    if args.apply:
        args.dry_run = False
    do_rename = bool(args.apply_rename)

    token = os.environ.get("DISCORD_BOT_TOKEN", "")
    if not token or not args.guild:
        print("[ERR] DISCORD_BOT_TOKEN / DISCORD_GUILD_ID requis (.env).")
        return 2
    struct_map = kd.load_struct_map()
    try:
        all_projs = kd.load_projects(args.epingle)
    except Exception as exc:
        print(f"[ERR] Epingle illisible: {exc}")
        return 2
    prod_plan = kd.build_plan(all_projs, struct_map)
    idea_list = idea_desired(all_projs, struct_map)

    status, live = kd.api_call("GET", f"/guilds/{args.guild}/channels", token)
    if status != 200:
        print(f"[ERR] lecture serveur: {status} {live}")
        return 1
    by_name = {c.get("name", ""): c for c in live if isinstance(c, dict)}
    by_id = {c.get("id"): c for c in live if isinstance(c, dict)}

    # --- 1. MANQUANTS (PROD + IDEA), avec adoption anti-doublon ---
    actions = []
    for cat, chans in prod_plan:
        if cat not in [c.get("name") for c in live if c.get("type") == 4]:
            actions.append(("cat+", cat, ""))
        for chan, topic, proj in chans:
            if chan not in by_name:
                actions.append(("create", chan, proj))
    # IDEA : n'adopte que si le chan désiré manque ET aucun slug-équivalent existant
    existing_slugs = {n for n in by_name}
    for cat, chan, topic, proj in idea_list:
        if chan in by_name:
            continue
        # Anti-doublon : si #sybil existe et désiré = idea-sybil mais map dit #sybil -> déjà géré ci-dessus.
        # Ici désiré non mappé : vérifie slug nu existant (ex: #thanatos vs idea-thanatos)
        bare = kd.slug(proj)
        if bare in existing_slugs and chan == f"idea-{bare}":
            actions.append(("adopt-suggest", chan, f"{proj} : existe #{bare}, ajoute \"{proj}\": \"#{bare}\" à la map au lieu de créer #{chan}"))
        else:
            actions.append(("create-idea", chan, proj))

    # --- 2. DOUBLONS probables (même slug, préfixes différents) ---
    names = list(by_name)
    dups = []
    for n in names:
        base = n.removeprefix("proj-").removeprefix("idea-")
        for m in names:
            if m != n and m.removeprefix("proj-").removeprefix("idea-") == base:
                pair = tuple(sorted((n, m)))
                if pair not in dups:
                    dups.append(pair)

    # --- 3. RENAMES proposés (incorrects détectés, jamais appliqués sans map) ---
    rename_map = load_rename()
    proposed = []
    for c in live:
        if not isinstance(c, dict) or c.get("type") != 0:
            continue
        n = c.get("name", "")
        # Curly apostrophe / majuscules / espaces : Discord impose minuscules-tirets
        norm = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode("ascii")
        if n != norm.lower().replace("_", "-").replace(" ", "-") and "--" not in n:
            if n not in rename_map and n not in [v for v in rename_map.values()]:
                # Heuristique douce : propose seulement cas évidents (apostrophe typographique, underscore)
                if "’" in n or "'" in n or "_" in n or " " in n:
                    proposed.append(n)

    print("=== discord autosync (manquants + fixes + renames) ===")
    print(f"  PROD désirés: {sum(len(c) for _, c in prod_plan)} | IDEA désirées: {len(idea_list)} | live: {len(live)}")
    if actions:
        print("  -- MANQUANTS --")
        for kind, chan, proj in actions:
            print(f"    [{kind}] #{chan} <- {proj}")
    else:
        print("  -- MANQUANTS : aucun --")
    if dups:
        print("  -- DOUBLONS (garder 1, supprimer l'autre à la main / retire-ours si SEC*/proj-*) --")
        for a, b in sorted(dups)[:20]:
            print(f"    [DUP] #{a} vs #{b}")
    if proposed:
        print("  -- RENAMES proposés (ajoute à kuro_discord_rename.local.json, jamais auto) --")
        for n in sorted(set(proposed))[:20]:
            print(f"    [RENAME?] #{n}")
    if rename_map:
        print(f"  -- RENAME map ({len(rename_map)}) --")
        for old, new in sorted(rename_map.items()):
            print(f"    [MAP] #{old} -> #{new}")

    mode_apply = bool(args.apply)
    # Exécute créations+fixes via sync existant (PROD uniquement ; IDEA créées explicitement ci-dessous)
    stats = kd.sync_guild(args.guild, token, prod_plan, dry=not mode_apply)
    print(f"  sync PROD stats: {stats}")
    if mode_apply:
        # Crée IDEA manquantes pures (pas les adopt-suggest)
        to_create = [(c, t, p) for k, c, p in actions if k == "create-idea" for (cc, t, pp) in [(None, None, None)]]
        # Re-dérive topics IDEA
        idea_by_chan = {chan: (cat, topic) for cat, chan, topic, proj in idea_list}
        cats_live = {c.get("name"): c.get("id") for c in live if isinstance(c, dict) and c.get("type") == 4}
        for kind, chan, proj in actions:
            if kind != "create-idea":
                continue
            cat, topic = idea_by_chan.get(chan, ("", ""))
            cat_id = cats_live.get(cat)
            if cat_id is None:
                print(f"  [SKIP] #{chan} : catégorie parente '{cat}' absente (crée-la d'abord ou mappe-la)")
                continue
            st, created = kd.api_call("POST", f"/guilds/{args.guild}/channels", token,
                                      {"name": chan, "type": 0, "parent_id": cat_id, "topic": topic})
            print(f"  [{'OK' if st in (200, 201) else 'ERR'}] crée #{chan} ({proj}): HTTP {st}")
    # Renames explicites
    if do_rename:
        if not rename_map:
            print("  [RENAME] map vide : rien à renommer.")
        else:
            for old, new in rename_map.items():
                cur = by_name.get(old)
                if not cur:
                    print(f"  [SKIP] #{old} introuvable.")
                    continue
                if new in by_name:
                    print(f"  [SKIP] #{new} existe déjà (doublon : supprime à la main d'abord).")
                    continue
                st, _ = kd.api_call("PATCH", f"/channels/{cur.get('id')}", token, {"name": new})
                print(f"  [{'OK' if st == 200 else 'ERR'}] rename #{old} -> #{new}: HTTP {st}")
    elif rename_map:
        print("  [DRY] renames mappés : relance avec --apply-rename pour exécuter.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
