#!/usr/bin/env bash
# server-screen-blank.sh — extinction de l'écran de la console du serveur (TTY, pas de GNOME).
# Cible : Ubuntu Server, console physique (getty sur tty1) — à lancer SUR le serveur lui-même.
# Usage : sudo bash server-screen-blank.sh [minutes]     # défaut 30 ; 0 = jamais
# Ex    : sudo bash server-screen-blank.sh 30            # politique 2026-10-19
#
# Ce que ça change (immédiat + persistant) :
#   1. setterm sur tous les TTY existants (effet immédiat, en MINUTES)
#   2. GRUB : consoleblank=<minutes*60> dans GRUB_CMDLINE_LINUX_DEFAULT (en SECONDES, dès le boot)
#   3. getty@tty1 : réapplique le réglage à chaque login console
# Ne touche pas au reste : ni xenon/kuro, ni logind (IdleAction=ignore reste géré par fix-server-xenon.sh).
set -euo pipefail

MIN="${1:-30}"
case "$MIN" in
  '' | *[!0-9]*) echo "[FAIL] minutes invalide : '$MIN' (entier attendu, ex. 30)"; exit 2 ;;
esac
SEC=$((MIN * 60))

echo "=== ECRAN CONSOLE : extinction apres ${MIN} min (consoleblank=${SEC} s) ==="

# --- 1) Effet immédiat (setterm prend des MINUTES, consoleblank des SECONDES) -------
for TTY in /dev/tty1 /dev/tty2 /dev/tty3 /dev/tty4 /dev/tty5 /dev/tty6; do
  [ -e "$TTY" ] && TERM=linux setterm -blank "$MIN" -powersave off -powerdown 0 < "$TTY" 2>/dev/null || true
done
TERM=linux setterm -blank "$MIN" -powersave off -powerdown 0 2>/dev/null \
  || echo "[warn] setterm direct KO (pas de console locale ?) — le noyau appliquera au reboot"
echo "[OK] setterm appliqué (${MIN} min)"

# --- 2) Persistant : consoleblank=<SEC> via GRUB ------------------------------------
if [ -f /etc/default/grub ]; then
  if grep -qE 'consoleblank=[0-9]+' /etc/default/grub; then
    echo "[fix] consoleblank existant -> ${SEC}"
    sed -i -E "s/consoleblank=[0-9]+/consoleblank=${SEC}/g" /etc/default/grub
  elif grep -q '^GRUB_CMDLINE_LINUX_DEFAULT=' /etc/default/grub; then
    echo "[fix] ajoute consoleblank=${SEC} à GRUB_CMDLINE_LINUX_DEFAULT"
    sed -i -E "s/^GRUB_CMDLINE_LINUX_DEFAULT=\"([^\"]*)\"/GRUB_CMDLINE_LINUX_DEFAULT=\"\1 consoleblank=${SEC}\"/" /etc/default/grub
    sed -i "s/ consoleblank=${SEC} consoleblank=${SEC}/ consoleblank=${SEC}/g" /etc/default/grub
  else
    echo "GRUB_CMDLINE_LINUX_DEFAULT=\"quiet consoleblank=${SEC}\"" >> /etc/default/grub
  fi
  update-grub || update-grub2 || true
  echo "[OK] grub mis à jour — reboot requis pour effet noyau"
else
  echo "[warn] /etc/default/grub absent (pas GRUB ?) — ajoute consoleblank=${SEC} à la cmdline manuellement"
fi

# --- 3) Persistant : getty@tty1 réapplique au login console -------------------------
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/blank.conf <<EOF
[Service]
ExecStartPre=-/bin/sh -c 'TERM=linux setterm -blank ${MIN} -powersave off -powerdown 0 < /dev/%I'
EOF
# Retire l'ancien override « jamais » s'il traîne (R116 : pas de réglage contradictoire)
rm -f /etc/systemd/system/getty@tty1.service.d/noblank.conf
systemctl daemon-reload || true
echo "[OK] getty@tty1 blank.conf installé (ancien noblank.conf supprimé si présent)"

# --- 4) Vérif finale ---------------------------------------------------------------
echo ""
echo "=== VERIF ==="
grep -n '^GRUB_CMDLINE_LINUX_DEFAULT=' /etc/default/grub 2>/dev/null || true
echo "consoleblank noyau (valeur du boot, 0444 donc non modifiable à chaud) : $(cat /sys/module/kernel/parameters/consoleblank 2>/dev/null || echo n/a)"
ls /etc/systemd/system/getty@tty1.service.d/ 2>/dev/null || true
echo "[DONE] écran console : extinction apres ${MIN} min (immédiat + persistant)"
