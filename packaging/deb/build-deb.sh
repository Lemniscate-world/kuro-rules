#!/usr/bin/env bash
# build-deb.sh — construit kuro_<VER>_all.deb (Kuro complet). Sans sudo.
# Usage : bash build-deb.sh [VERSION]   (defaut : 1.3.0-1)
# Demande : git, gh (authentifie), dpkg-deb. Test : Ubuntu 24.04.
set -euo pipefail

VER="${1:-1.3.0-1}"
PKG=kuro
WORK=/tmp/kuro-deb
SRC="$WORK/src"
STAGE="$WORK/${PKG}_${VER}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Sources locales par defaut (deja synchronisees sur cette machine).
# Release propre : KURO_RULES_SRC/KURO_SRC pointes vers des clones frais du tag.
RULES_SRC="${KURO_RULES_SRC:-$HOME/Documents/kuro-rules}"
KURO_SRC="${KURO_SRC:-$HOME/Documents/kuro}"

echo "[1/6] sources (kuro-rules + Kuro, JAMAIS modifies, R105)..."
rm -rf "$SRC"
mkdir -p "$SRC"
cp -r "$RULES_SRC" "$SRC/kuro-rules"
cp -r "$KURO_SRC" "$SRC/Kuro"

echo "[2/6] arborescence..."
rm -rf "$STAGE"
mkdir -p "$STAGE"/DEBIAN \
         "$STAGE"/opt/kuro-dashboard/src \
         "$STAGE"/opt/kuro \
         "$STAGE"/usr/bin \
         "$STAGE"/usr/share/doc/"$PKG" \
         "$STAGE"/lib/systemd/system

echo "[3/6] paquet dashboard (API + system + scan + UI)..."
cp -r "$SRC/kuro-rules/src/kuro_dashboard" "$STAGE/opt/kuro-dashboard/src/"
cp "$SCRIPT_DIR"/usr-bin-kuro-dashboard "$STAGE/usr/bin/kuro-dashboard"
cp "$SCRIPT_DIR"/usr-bin-kuro-system "$STAGE/usr/bin/kuro-system"
cp "$SCRIPT_DIR"/usr-bin-xenon "$STAGE/usr/bin/xenon"
cp "$SCRIPT_DIR"/usr-bin-xenon-tui "$STAGE/usr/bin/xenon-tui"
cp "$SCRIPT_DIR"/usr-bin-kuro-glances "$STAGE/usr/bin/kuro-glances"
cp "$SCRIPT_DIR"/usr-bin-kuro-glances-tui "$STAGE/usr/bin/kuro-glances-tui"
chmod 755 "$STAGE/usr/bin/kuro-dashboard" "$STAGE/usr/bin/kuro-system" "$STAGE/usr/bin/xenon" "$STAGE/usr/bin/xenon-tui" "$STAGE/usr/bin/kuro-glances" "$STAGE/usr/bin/kuro-glances-tui"

echo "[4/6] daemon Kuro (repo Kuro, embarque tel quel)..."
cp "$SRC/Kuro/daemon.py" "$STAGE/opt/kuro/"
cp -r "$SRC/Kuro/kuro" "$STAGE/opt/kuro/"
find "$STAGE/opt" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$STAGE/opt" -name .pytest_cache -type d -prune -exec rm -rf {} + 2>/dev/null || true
cp "$SRC/kuro-rules/packaging/README.pypi.md" "$STAGE/usr/share/doc/$PKG/README.md" || true

echo "[5/6] metadonnees Debian..."
sed "s/^Version:.*/Version: $VER/" "$SCRIPT_DIR/control" > "$STAGE/DEBIAN/control"
cp "$SCRIPT_DIR/postinst" "$SCRIPT_DIR/prerm" "$STAGE/DEBIAN/"
cp "$SCRIPT_DIR/kuro-daemon.service" "$SCRIPT_DIR/kuro-dashboard.service" \
   "$STAGE/lib/systemd/system/"
chmod 755 "$STAGE/DEBIAN/postinst" "$STAGE/DEBIAN/prerm"

echo "[6/6] build + controle..."
dpkg-deb --build "$STAGE" "$WORK/${PKG}_${VER}_all.deb"
if command -v lintian >/dev/null 2>&1; then
    lintian "$WORK/${PKG}_${VER}_all.deb" || true
else
    echo "(lintian absent, controle ignore)"
fi
dpkg-deb -c "$WORK/${PKG}_${VER}_all.deb"
echo "[OK] $WORK/${PKG}_${VER}_all.deb"
