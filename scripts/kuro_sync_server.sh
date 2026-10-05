#!/usr/bin/env bash
# kuro_sync_server.sh — auto-sync des repos + auto-update des services Kuro.
# Tourne SUR le serveur (timer systemd --user). Zero sudo.
#
#   bash kuro_sync_server.sh --dry-run   # affiche le plan, ne touche a rien
#   bash kuro_sync_server.sh            # sync + reinstall+restart si besoin (= --auto)
#   bash kuro_sync_server.sh --reinstall # reinstalle + restart maintenant
#   bash kuro_sync_server.sh --install   # installe units + timer --user
#
# Regles : git ff-only uniquement (le divergent est signale, jamais ecrase ;
# seuls les commits pousses voyagent, jamais le travail non commite) ;
# restart stop/attente/start (jamais de restart sec sur le port 8767) ;
# log ASCII dans ~/.kuro/sync.log ; lock anti-chevauchement.
set -euo pipefail

RULES_DIR="${KURO_RULES_DIR:-$HOME/Documents/kuro-rules}"
LIST_FILE="${KURO_SYNC_LIST:-$RULES_DIR/scripts/sync-repos.txt}"
DOCS_DIR="${KURO_DOCS_DIR:-$HOME/Documents}"
VENV_BIN="${KURO_VENV_BIN:-$HOME/.venvs/kuro/bin}"
LOG_FILE="$HOME/.kuro/sync.log"
LOCK_FILE="/tmp/kuro-sync.lock"
MODE="${1:---auto}"

log() { printf '%s | %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" >> "$LOG_FILE"; }
say() { printf '%s\n' "$1"; }

install_units() {
    local unitdir="$HOME/.config/systemd/user"
    mkdir -p "$unitdir"
    cat > "$unitdir/kuro-sync.service" <<EOF
[Unit]
Description=Kuro auto-sync repos + auto-update services
After=network-online.target

[Service]
Type=oneshot
ExecStart=$RULES_DIR/scripts/kuro_sync_server.sh --auto
EOF
    cat > "$unitdir/kuro-sync.timer" <<EOF
[Unit]
Description=Kuro auto-sync toutes les 30 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=30min

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload
    systemctl --user enable --now kuro-sync.timer
    say "timer installe et actif (toutes les 30 min)"
}

sync_one() {
    # $1=nom $2=url. Affiche : cloned|changed|uptodate|failed|would-clone|would-pull
    local name="$1" url="$2" dest="$DOCS_DIR/$name"
    local before="" after=""
    if [ ! -d "$dest/.git" ]; then
        if [ "$MODE" = "--dry-run" ]; then echo "would-clone"; return 0; fi
        if timeout 180 git clone "$url" "$dest" >>"$LOG_FILE" 2>&1; then
            echo "cloned"
        else
            echo "failed"
        fi
        return 0
    fi
    before=$(git -C "$dest" rev-parse HEAD 2>/dev/null || echo "unknown")
    if ! timeout 120 git -C "$dest" fetch origin >>"$LOG_FILE" 2>&1; then
        echo "failed"
        return 0
    fi
    if [ "$MODE" = "--dry-run" ]; then echo "would-pull"; return 0; fi
    if timeout 120 git -C "$dest" pull --ff-only >>"$LOG_FILE" 2>&1; then
        after=$(git -C "$dest" rev-parse HEAD 2>/dev/null || echo "unknown")
        if [ "$before" = "$after" ]; then echo "uptodate"; else echo "changed"; fi
    else
        echo "failed"
    fi
    return 0
}

restart_services() {
    systemctl --user stop kuro-api kuro-daemon 2>/dev/null || true
    sleep 4
    systemctl --user start kuro-daemon 2>/dev/null || true
    sleep 6
    systemctl --user start kuro-api 2>/dev/null || true
    sleep 4
}

reinstall_package() {
    # Reinstallation auto (entry points + metadata) : idempotent, sans sudo.
    # Echec = warning loggue, on continue avec l ancien code (degrade honnete).
    if [ ! -x "$VENV_BIN/pip" ]; then
        log "reinstall: pas de pip venv ($VENV_BIN), ignore"
        return 0
    fi
    if timeout 300 "$VENV_BIN/pip" install -q --disable-pip-version-check \
        "$RULES_DIR" watchdog psutil >>"$LOG_FILE" 2>&1; then
        log "reinstall: pip install kuro-rules + deps OK (snapshot, non-editable)"
    else
        log "reinstall: PIP EN ECHEC, on garde l ancien code"
        return 0
    fi
    local missing=""
    local cmd=""
    for cmd in xenon kuro-system kuro-dashboard; do
        if ! timeout 60 "$VENV_BIN/$cmd" --help >/dev/null 2>&1; then
            missing="$missing $cmd"
        fi
    done
    if [ -n "$missing" ]; then
        log "reinstall: commandes manquantes:$missing"
    else
        log "reinstall: 3 commandes OK"
    fi
    return 0
}

check_endpoints() {
    local path="" code=""
    for path in "/" "/api/system" "/api/status" "/api/dashboard"; do
        code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8767$path" 2>/dev/null || echo "000")
        if [ "$code" != "200" ]; then
            return 1
        fi
    done
    return 0
}

restart_and_verify() {
    restart_services
    if check_endpoints; then
        log "restart: 4 endpoints 200"
        say "restart: OK, 4 endpoints 200"
    else
        log "restart: ENDPOINTS EN ERREUR - intervention requise"
        say "restart: ENDPOINTS EN ERREUR - intervention requise"
    fi
}

main() {
    if [ "$MODE" = "--install" ]; then
        install_units
        return 0
    fi
    if [ "$MODE" = "--reinstall" ]; then
        log "reinstallation manuelle demandee"
        reinstall_package
        restart_and_verify
        return 0
    fi
    if [ ! -f "$LIST_FILE" ]; then
        say "liste introuvable: $LIST_FILE"
        return 1
    fi
    mkdir -p "$(dirname "$LOG_FILE")"
    if [ -f "$LOG_FILE" ]; then
        tail -n 500 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
    fi
    exec 9>"$LOCK_FILE"
    if ! flock -n 9; then
        say "sync deja en cours, abandon"
        return 0
    fi
    local line="" name="" url="" result="" need_restart=0 failed_any=0
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in ""|\#*) continue ;; esac
        # shellcheck disable=SC2086 : decoupage voulu nom + url
        set -- $line
        if [ $# -lt 2 ]; then
            continue
        fi
        name="$1"
        url="$2"
        result=$(sync_one "$name" "$url")
        log "$name: $result"
        say "$name: $result"
        if [ "$result" = "changed" ] || [ "$result" = "cloned" ]; then
            if [ "$name" = "kuro" ] || [ "$name" = "kuro-rules" ]; then
                need_restart=1
            fi
        fi
        if [ "$result" = "failed" ]; then
            failed_any=1
        fi
    done < "$LIST_FILE"
    if [ "$MODE" != "--dry-run" ] && [ "$need_restart" = "1" ]; then
        log "reinstallation auto (kuro-rules ou Kuro a change)"
        reinstall_package
        log "restart services (kuro-rules ou Kuro a change)"
        restart_and_verify
    fi
    if [ "$failed_any" = "1" ]; then
        log "termine avec des echecs (voir ci-dessus)"
        return 1
    fi
    return 0
}

main
