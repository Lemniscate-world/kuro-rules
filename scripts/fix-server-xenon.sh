#!/usr/bin/env bash
# fix-server-xenon.sh — répare Xenon (ex kuro-glances) sur la console du serveur.
# Cible : Ubuntu Server console (TTY, pas de GNOME) — à lancer SUR le PC serveur lui-même.
# Usage : sudo bash fix-server-xenon.sh
# NOTE (2026-10-19) : l'écran console n'est plus réglé ici — une seule source de vérité :
#   scripts/server-screen-blank.sh (défaut 30 min, réglable en argument). Voir §3/3.
set -euo pipefail

echo "=== 1/3 DIAG xenon ==="
echo "-- PATH / binaire --"
XENON_BIN="$(which xenon 2>/dev/null || which kuro-glances 2>/dev/null || true)"
if [ -n "$XENON_BIN" ]; then echo "trouvé : $XENON_BIN"; else echo "MANQUANT: xenon introuvable dans PATH"; fi
ls -l /usr/bin/kuro-* 2>/dev/null || echo "MANQUANT: /usr/bin/kuro-* absent"
ls -l /opt/kuro-dashboard/src/kuro_dashboard/tui.py 2>/dev/null || echo "MANQUANT: /opt/kuro-dashboard absent"
echo "-- python / psutil --"
python3 --version || true
python3 -c "import psutil; print('psutil OK', psutil.__version__)" 2>&1 || echo "MANQUANT: python3-psutil absent"
echo "-- paquet deb --"
dpkg -l | grep -i kuro || echo "paquet kuro non installé (dpkg vide)"
cat /sys/module/kernel/parameters/consoleblank 2>/dev/null && echo "(consoleblank en secondes : 0 = jamais, 300 = 5 min, 900 = 15 min, 1800 = 30 min)" || true

echo ""
echo "=== 2/3 INSTALL / REPARE xenon ==="
if ! which xenon >/dev/null 2>&1 && ! which kuro-glances >/dev/null 2>&1; then
  echo "[fix] installation dépendances + fallback..."
  apt-get update
  apt-get install -y python3 python3-psutil python3-watchdog console-tools 2>/dev/null || apt-get install -y python3 python3-psutil
  # Si le .deb est présent localement (copié via USB/scp), l'installer :
  DEB=$(ls -t /tmp/kuro-deb/kuro_*_all.deb 2>/dev/null | head -n1 || true)
  if [ -n "${DEB:-}" ] && [ -f "$DEB" ]; then
    echo "[fix] installe $DEB"
    dpkg -i "$DEB" || apt-get install -f -y
  else
    echo "[info] pas de .deb dans /tmp/kuro-deb — fallback PYTHONPATH."
    echo "[info] Pour build complet, sur PC dev : bash packaging/deb/build-deb.sh puis copier le .deb ici."
    # Fallback minimal : cloner juste le TUI si /opt absent et repo présent
    if [ ! -f /opt/kuro-dashboard/src/kuro_dashboard/tui.py ]; then
      echo "[warn] /opt/kuro-dashboard absent — copiez le dossier src/kuro_dashboard vers /opt/kuro-dashboard/src/ ou installez le .deb."
    fi
  fi
fi
# Vérif finale
if [ -n "${XENON_BIN:-}" ]; then
  echo "[OK] trouvé : $XENON_BIN"
  "$XENON_BIN" --help 2>&1 | head -n 5 || true
  echo "[test] une frame non-interactive (pipe) :"
  kuro-system --json 2>&1 | head -c 500; echo ""
else
  echo "[FAIL] toujours absent. Lancez manuel :"
  echo "  PYTHONPATH=/opt/kuro-dashboard/src python3 -m kuro_dashboard.tui"
  echo "  PYTHONPATH=/opt/kuro-dashboard/src python3 -m kuro_dashboard.system --json | head"
fi

echo ""
echo "=== 3/3 ECRAN CONSOLE (délégué) ==="
# Source unique de vérité : server-screen-blank.sh (défaut 30 min ; SCREEN_MIN=x pour surcharger)
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [ -f "$SELF_DIR/server-screen-blank.sh" ]; then
  bash "$SELF_DIR/server-screen-blank.sh" "${SCREEN_MIN:-30}"
else
  echo "[warn] $SELF_DIR/server-screen-blank.sh introuvable — copie-le à côté de ce script puis lance :"
  echo "  sudo bash server-screen-blank.sh 30"
fi

# Sécurité : logind ne doit jamais idle-suspendre (serveur)
if [ -f /etc/systemd/logind.conf ]; then
  grep -q "^HandleIdleAction=" /etc/systemd/logind.conf && sed -i 's/^HandleIdleAction=.*/HandleIdleAction=ignore/' /etc/systemd/logind.conf || echo "HandleIdleAction=ignore" >> /etc/systemd/logind.conf
  grep -q "^IdleAction=" /etc/systemd/logind.conf && sed -i 's/^IdleAction=.*/IdleAction=ignore/' /etc/systemd/logind.conf || echo "IdleAction=ignore" >> /etc/systemd/logind.conf
  systemctl restart systemd-logind 2>/dev/null || true
  echo "[OK] logind IdleAction=ignore"
fi

echo ""
echo "=== VERIF FINALE ==="
cat /sys/module/kernel/parameters/consoleblank 2>/dev/null || echo "(consoleblank lisible seulement après reboot)"
[ -n "${XENON_BIN:-}" ] && echo "[DONE] xenon OK + écran console géré par server-screen-blank.sh" || echo "[A FAIRE] réinstalle le .deb kuro puis relance ce script"
