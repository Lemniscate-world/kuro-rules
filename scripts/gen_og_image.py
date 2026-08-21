#!/usr/bin/env python3
"""gen_og_image.py — Génère assets/og.png (1200x630) style Ledger Brutal depuis les stats réelles.

Usage: python gen_og_image.py [--out chemin/og.png]
Appelé par generate_portfolio.py si Pillow disponible. Échoue silencieusement sans casser le build.
"""
import re, sys
from pathlib import Path

def epingle_stats():
    ep = Path.home() / "Documents" / "kuro-rules" / "Epingle_Projets.md"
    if not ep.exists():
        return None
    text = ep.read_text(encoding="utf-8")
    projs, pct_sum, pct_n = 0, 0, 0
    for line in text.splitlines():
        if line.startswith("| **") or (line.startswith("| ") and "%" in line):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 3:
                name = parts[0].replace("**", "").strip()
                pr = parts[1].strip()
                if not name or "?-" in pr or "Externe" in pr:
                    continue
                m = re.search(r"(\d+)", pr)
                if m:
                    projs += 1
                    pct_sum += int(m.group(1)); pct_n += 1
    if projs == 0:
        return None
    return {"projets": projs, "moyenne": round(pct_sum / pct_n)}

def main():
    from PIL import Image, ImageDraw, ImageFont
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else \
          Path.home() / "Documents" / "Lemniscate-world" / "assets" / "og.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    W, H = 1200, 630
    paper, ink, muted, hair = (250, 249, 245), (22, 21, 19), (111, 108, 100), (217, 214, 204)
    img = Image.new("RGB", (W, H), paper)
    d = ImageDraw.Draw(img)

    def font(size, bold=False, mono=True):
        names = ["consola.ttf", "CascadiaMono.ttf", "arial.ttf"] if mono else ["georgiab.ttf" if bold else "georgia.ttf", "arial.ttf"]
        for n in names:
            try:
                return ImageFont.truetype(n, size)
            except Exception:
                continue
        return ImageFont.load_default()

    # Cadre ledger
    d.rectangle([24, 24, W - 24, H - 24], outline=ink, width=3)
    d.line([24, 96, W - 24, 96], fill=ink, width=2)

    d.text((56, 44), "LAMBDA-SECTION — REGISTRE DES PROJETS", font=font(22), fill=muted)
    d.text((52, 130), "λ", font=font(150, bold=True, mono=False), fill=ink)
    d.text((210, 168), "60 projets.", font=font(64, bold=True, mono=False), fill=ink)
    d.text((210, 258), "Chaque ligne vérifiée", font=font(40, mono=False), fill=ink)
    d.text((210, 316), "contre l'activité Git réelle.", font=font(40, mono=False), fill=ink)

    st = epingle_stats()
    if st:
        d.line([56, 420, W - 56, 420], fill=hair, width=1)
        d.text((56, 448), f"{st['projets']} projets documentés", font=font(26), fill=ink)
        d.text((56, 492), f"progression moyenne {st['moyenne']}%", font=font(26), fill=ink)
        d.text((56, 536), "AI · Quant · Biohacking · Blockchain", font=font(22), fill=muted)
    d.text((W - 480, H - 78), "lemniscate-world.github.io/Lemniscate-world", font=font(22), fill=muted)

    img.save(out, "PNG", optimize=True)
    print(f"  og:image -> {out}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"  og:image skip: {e}")
