#!/usr/bin/env python3
"""sync_discord_to_epingle.py — Importe tes messages Discord par projet vers Epingle_Projets.md.

Usage:
  1. Exporte ton serveur Discord avec DiscordChatExporter (GUI ou CLI):
     DiscordChatExporter.Cli.exe export --channel <id> --format Json --output discord_export.json
     Ou exporte manuellement: chaque salon = un projet (ex: #neuraldbg, #lifetrack)

  2. Structure attendue:
     discord_export.json ou dossier exports/ avec un .json par salon:
       {
         "channel": {"name": "neuraldbg", "category": "S-1"},
         "messages": [{"content": "...", "timestamp": "...", "author": "..."}]
       }

  3. Lance:
     python scripts/sync_discord_to_epingle.py --export discord_export.json --dry-run
     python scripts/sync_discord_to_epingle.py --export exports/ --apply

Le script:
  - mappe channel name -> projet Epingle (neuraldbg -> NeuralDBG)
  - extrait le dernier message significatif par projet
  - propose une mise a jour de la colonne Description dans Epingle_Projets.md
  - ne touche pas aux % / statuts (tu gardes le controle)

Voir aussi: generate_portfolio.py qui sync ensuite Epingle -> portfolio + README
"""
import json, re, sys
from pathlib import Path

LOCAL_EPINGLE = Path.home() / "Documents" / "kuro-rules" / "Epingle_Projets.md"

CHANNEL_TO_PROJECT = {
    # S-1
    "neuraldbg": "NeuralDBG",
    "neuraldbg-engine": "NeuralDBG-Engine",
    "neural-agent": "Neural-Agent",
    "aladin": "Aladin",
    "astral": "Astral",
    "datalint": "DataLint",
    "odin": "Odin",
    "aquarium": "Aquarium",
    # S-2
    "openquant": "OpenQuant",
    "console": "Console",
    # S-3
    "echox": "EchoX",
    "lifetrack": "LifeTrack",
    "charmed": "Charmed",
    "flow-regulator": "Flow-Regulator",
    # S-4
    "hermes": "Hermes",
    "epure": "Epure",
    # S-7
    "helium": "Helium",
    # S-8
    "dissect": "Dissect",
    # S-9
    "sagittarius": "Sagittarius",
    # S-12
    "aether": "AEther",
    # S-14
    "openmind": "OpenMind",
}

def load_exports(export_path: Path):
    messages_by_project = {}
    files = [export_path] if export_path.is_file() else list(export_path.glob("*.json"))
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  skip {f.name}: {e}")
            continue
        # DiscordChatExporter format: {"channel": {"name": "..."}, "messages": [...]}
        # ou simple liste
        channel_name = ""
        msgs = []
        if isinstance(data, dict):
            channel_name = data.get("channel", {}).get("name", f.stem) if isinstance(data.get("channel"), dict) else f.stem
            msgs = data.get("messages", data.get("Messages", []))
        elif isinstance(data, list):
            channel_name = f.stem
            msgs = data
        key = channel_name.lower().replace(" ", "-").replace("_", "-")
        project = CHANNEL_TO_PROJECT.get(key)
        if not project:
            # try direct match
            for proj in CHANNEL_TO_PROJECT.values():
                if proj.lower() == key:
                    project = proj
                    break
        if not project:
            # keep raw channel as project candidate
            project = channel_name
        # keep last 3 meaningful messages (not empty, not bot)
        meaningful = [m.get("content","").strip() for m in msgs if m.get("content","").strip() and len(m.get("content","").strip()) > 10]
        if meaningful:
            messages_by_project[project] = meaningful[-3:]
    return messages_by_project

def propose_updates(messages_by_project):
    epingle = LOCAL_EPINGLE.read_text(encoding="utf-8")
    for project, msgs in messages_by_project.items():
        snippet = msgs[-1][:120].replace("\n", " ")
        # Find line in Epingle
        pattern = re.compile(rf'^\|\s*\*\*{re.escape(project)}\*\*\s*\|.*$', re.MULTILINE | re.IGNORECASE)
        m = pattern.search(epingle)
        if m:
            print(f"\n[{project}] {len(msgs)} messages Discord -> proposition:")
            print(f"  dernier: {snippet}...")
            print(f"  ligne Epingle: {m.group(0)[:100]}...")
            print(f"  -> tu peux copier ce snippet dans la colonne Description de {project} dans Epingle")
        else:
            # try without **
            pattern2 = re.compile(rf'^\|\s*{re.escape(project)}\s*\|.*$', re.MULTILINE | re.IGNORECASE)
            m2 = pattern2.search(epingle)
            if m2:
                print(f"\n[{project}] (sans **): {snippet[:80]}...")
            else:
                print(f"\n[{project}] pas trouve dans Epingle -> a ajouter manuellement")
                print(f"  snippet: {snippet[:100]}")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True, help="fichier .json ou dossier d'exports Discord")
    ap.add_argument("--dry-run", action="store_true", help="affiche seulement les propositions")
    ap.add_argument("--apply", action="store_true", help="applique (pour l'instant dry-run seulement)")
    args = ap.parse_args()

    p = Path(args.export).expanduser()
    if not p.exists():
        print(f"ERROR: {p} not found")
        sys.exit(1)

    print(f"Lecture {p}...")
    msgs = load_exports(p)
    print(f"  {len(msgs)} projets avec messages Discord")

    if not msgs:
        print("  Aucun message trouve. Verifie le format JSON (DiscordChatExporter).")
        print("  Astuce: exporte un salon test en JSON et montre-moi le fichier pour adapter le parser.")
        return

    propose_updates(msgs)

    if args.apply:
        print("\n--apply: pour l'instant, mets a jour manuellement Epingle puis lance generate_portfolio.py")
        print("  Prochaine etape: python scripts/generate_portfolio.py (sync portfolio + README)")

if __name__ == "__main__":
    main()
