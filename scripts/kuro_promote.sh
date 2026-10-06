#!/usr/bin/env bash
# kuro_promote.sh — bascule MANUELLE du standby (JAMAIS automatique).
# Un PC eteint la nuit est normal : la promotion est une decision humaine.
#
#   bash kuro_promote.sh --check               # lecture seule : etat + verdict
#   bash kuro_promote.sh --promote              # backup live, installe replica, restart, verif
#   bash kuro_promote.sh --promote --force      # promeut meme un replica > 120 min
#
# Retour arriere : le backup pre-promotion est garde à côté du live
# (kuro.db.pre-promote-<ts>) — le restaurer = cp + restart daemon.
set -euo pipefail

KURO_HOME="${KURO_HOME:-$HOME}"
KDIR="$KURO_HOME/.kuro"
LIVE="$KDIR/kuro.db"
REPLICA="$KDIR/kuro-replica.db"
MAX_AGE_MIN=120

age_min() {
    if [ ! -f "$1" ]; then
        echo "none"
        return 0
    fi
    echo $(( ($(date +%s) - $(stat -c %Y "$1")) / 60 ))
    return 0
}

has_systemctl() { command -v systemctl >/dev/null 2>&1; }

do_check() {
    local live_age replica_age
    live_age=$(age_min "$LIVE")
    replica_age=$(age_min "$REPLICA")
    echo "live    : $LIVE (age ${live_age} min)"
    echo "replica : $REPLICA (age ${replica_age} min)"
    if has_systemctl; then
        echo "daemon  : $(systemctl --user is-active kuro-daemon 2>/dev/null || echo inconnu)"
        echo "api     : $(systemctl --user is-active kuro-api 2>/dev/null || echo inconnu)"
    else
        echo "systemd : absent (pas de restart possible ici)"
    fi
    if [ "$replica_age" = "none" ]; then
        echo "VERDICT : NO-GO — pas de replica (attendre le push PC)"
        return 1
    fi
    if [ "$replica_age" -gt "$MAX_AGE_MIN" ]; then
        echo "VERDICT : NO-GO — replica trop vieux (> $MAX_AGE_MIN min), --force pour outrepasser"
        return 2
    fi
    echo "VERDICT : GO — promotion possible (--promote)"
    return 0
}

do_restart() {
    if [ "${KURO_NO_RESTART:-0}" = "1" ] || ! has_systemctl; then
        echo "restart ignore (test ou systemd absent)"
        return 0
    fi
    systemctl --user stop kuro-api kuro-daemon 2>/dev/null || true
    sleep 4
    systemctl --user start kuro-daemon 2>/dev/null || true
    sleep 6
    systemctl --user start kuro-api 2>/dev/null || true
    sleep 4
}

do_verify() {
    if ! has_systemctl; then
        return 0
    fi
    systemctl --user is-active kuro-daemon kuro-api >/dev/null 2>&1 || return 1
    local code=""
    code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8767/api/status 2>/dev/null || echo "000")
    [ "$code" = "200" ]
}

do_promote() {
    local force=0
    if [ "${1:-}" = "--force" ]; then
        force=1
    fi
    local replica_age
    replica_age=$(age_min "$REPLICA")
    if [ "$replica_age" = "none" ]; then
        echo "PROMOTE REFUSE : pas de replica"
        return 1
    fi
    if [ "$force" -ne 1 ] && [ "$replica_age" -gt "$MAX_AGE_MIN" ]; then
        echo "PROMOTE REFUSE : replica vieux de ${replica_age} min (--force pour outrepasser)"
        return 2
    fi
    local stamp
    stamp=$(date -u +%Y%m%dT%H%M%SZ)
    if [ -f "$LIVE" ]; then
        cp "$LIVE" "$LIVE.pre-promote-$stamp"
        echo "backup live : $LIVE.pre-promote-$stamp"
    fi
    cp "$REPLICA" "$LIVE"
    echo "replica installe comme live"
    ls -t "$KDIR"/kuro.db.pre-promote-* 2>/dev/null | tail -n +4 | while IFS= read -r vieux; do
        rm -f "$vieux"
    done
    echo "retention backups : 3 derniers gardes"
    do_restart
    if do_verify; then
        echo "PROMOTE OK : services actifs, API 200"
        return 0
    fi
    echo "PROMOTE PARTIEL : fichiers en place, verif services en echec (voir ci-dessus)"
    return 3
}

case "${1:---check}" in
    --check) do_check ;;
    --promote) do_promote "${2:-}" ;;
    *) echo "usage: $0 --check | --promote [--force]"; exit 2 ;;
esac
