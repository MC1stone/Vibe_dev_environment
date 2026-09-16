#!/bin/bash
#
# NIR Intelligence Platform - Lokaler Entwicklungs-Server
#
# Stoppt die Docker-Container, die Port 8000 belegen und sich selbst
# neu starten (nir_django, nir_mcp), startet die Daten-Infrastruktur
# (postgres, qdrant, ollama) per 'docker compose up -d', bringt den
# Quellcode auf den neuesten Stand des PR-Branches und startet den
# lokalen Django-Dev-Server mit der fuer den Host korrekten
# DB-Konfiguration (DB_HOST=localhost).
#
# Nutzung:
#   ./dev-run.sh                       # Default: PR-Branch, kein Reset
#   ./dev-run.sh --reset                # Hartes Reset auf origin/<branch>
#   ./dev-run.sh --branch <branch>     # Anderer Branch
#   ./dev-run.sh --no-pull              # Kein git pull
#
# Abbruch mit Strg+C stoppt den Dev-Server; die Daten-Container laufen weiter.

set -e

# ---------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DJANGO_DIR="$REPO_ROOT/nir_platform/django_app"
DEFAULT_BRANCH="vibe/upload-eval-analysis-quarto-html-0b1bfc"
BRANCH="$DEFAULT_BRANCH"
DO_RESET=0
DO_PULL=1

# Container, die den Dev-Server stoeren: belegen Port 8000 und starten
# sich wegen restart: unless-stopped selbst wieder neu.
STOP_CONTAINERS=(nir_django nir_mcp)
# Daten-Infrastruktur, die der lokale Dev-Server benoetigt. Diese werden
# per 'docker compose up -d' gestartet (auch wenn sie noch nicht existieren)
# und laufen weiter, nachdem der Dev-Server beendet wurde.
COMPOSE_DIR="$REPO_ROOT/nir_platform/docker"
KEEP_CONTAINERS=(nir_postgres nir_qdrant nir_ollama)
# Diese Services werden hochgefahren (postgres, qdrant, ollama).
COMPOSE_SERVICES=(postgres qdrant ollama)

# ---------------------------------------------------------------------
# Argumente
# ---------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --reset)   DO_RESET=1; shift ;;
        --no-pull) DO_PULL=0; shift ;;
        --branch)  BRANCH="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Unbekannter Parameter: $1" >&2
            echo "Siehe: $0 --help" >&2
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------
log()  { printf '\033[1;34m[dev-run]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[dev-run]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[dev-run]\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31m[dev-run]\033[0m %s\n' "$*" >&2; }

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        err "Befehl nicht gefunden: $1"
        exit 1
    fi
}

container_exists() {
    docker ps -aq --filter "name=^/$1$" 2>/dev/null | grep -q .
}

# ---------------------------------------------------------------------
# 1. Voraussetzungen
# ---------------------------------------------------------------------
require_cmd docker
require_cmd git
# Debian ships python3 without a 'python' alias, so accept either.
if ! command -v python >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
    warn "'python' nicht gefunden, verwende 'python3'."
fi

if [ ! -d "$DJANGO_DIR" ]; then
    err "Django-Verzeichnis nicht gefunden: $DJANGO_DIR"
    err "Skript muss innerhalb des Repositories liegen."
    exit 1
fi

# ---------------------------------------------------------------------
# 2. Stoerende Docker-Container stoppen + Auto-Restart verhindern
# ---------------------------------------------------------------------
log "Stoppe Docker-Container, die Port 8000 belegen..."
for c in "${STOP_CONTAINERS[@]}"; do
    if container_exists "$c"; then
        # restart-Policy aufheben, sonst startet der Container nach
        # 'docker stop' wegen 'restart: unless-stopped' sofort wieder.
        docker update --restart=no "$c" >/dev/null 2>&1 || true
        docker stop "$c" >/dev/null 2>&1 || true
        ok "Container '$c' gestoppt (Auto-Restart deaktiviert)."
    else
        warn "Container '$c' nicht vorhanden - übersprungen."
    fi
done

# ---------------------------------------------------------------------
# 3. Daten-Infrastruktur starten (postgres, qdrant, ollama)
# ---------------------------------------------------------------------
log "Starte Daten-Container (postgres, qdrant, ollama) via docker compose..."
if [ -f "$COMPOSE_DIR/docker-compose.yml" ]; then
    cd "$COMPOSE_DIR"
    # 'docker compose up -d' erstellt fehlende Container und startet
    # gestoppte. Schraenkt auf die Daten-Services ein, damit der Dev-
    # Server (django, mcp) nicht versehentlich mit gestartet wird.
    if docker compose up -d "${COMPOSE_SERVICES[@]}" >/dev/null 2>&1; then
        ok "Daten-Container gestartet (postgres, qdrant, ollama)."
    else
        warn "'docker compose up -d' fehlgeschlagen - versuche Container einzeln zu starten."
        for c in "${KEEP_CONTAINERS[@]}"; do
            if container_exists "$c" && ! docker ps --filter "name=^/$c$" --filter "status=running" | grep -q "$c"; then
                docker start "$c" >/dev/null 2>&1 || warn "Konnte '$c' nicht starten."
            fi
        done
    fi
    cd "$REPO_ROOT"
else
    warn "docker-compose.yml nicht gefunden unter $COMPOSE_DIR - übersprungen."
fi

# Warte kurz, bis postgres Verbindungen annimmt.
if container_exists nir_postgres; then
    log "Warte auf postgres..."
    for _ in $(seq 1 15); do
        if docker exec nir_postgres pg_isready -U postgres >/dev/null 2>&1; then
            ok "postgres ist bereit."
            break
        fi
        sleep 1
    done
fi

# Pruefe, ob Ollama erreichbar ist (der Chat-Bot braucht es).
if container_exists nir_ollama; then
    log "Pruefe Ollama auf http://localhost:11435 ..."
    ollama_ok=0
    for _ in $(seq 1 10); do
        if curl -s --max-time 2 http://localhost:11435/api/tags >/dev/null 2>&1; then
            ollama_ok=1
            break
        fi
        sleep 1
    done
    if [ "$ollama_ok" -eq 1 ]; then
        ok "Ollama ist erreichbar (http://localhost:11435)."
        # Hinweis: Das Modell muss einmal gezogen worden sein.
        if ! docker exec nir_ollama ollama list 2>/dev/null | grep -qi mistral; then
            warn "Modell 'mistral' noch nicht in Ollama vorhanden."
            warn "Ziehen mit:  docker exec -it nir_ollama ollama pull mistral"
            warn "Danach ist der Chat-Bot einsatzbereit."
        else
            ok "Modell 'mistral' ist vorhanden - Chat-Bot einsatzbereit."
        fi
    else
        warn "Ollama antwortet nicht auf Port 11435. Chat-Bot nutzt lokalen Fallback."
        warn "Starte Ollama manuell:  docker start nir_ollama"
    fi
fi

# ---------------------------------------------------------------------
# 4. Quellcode auf neuesten Stand bringen
# ---------------------------------------------------------------------
cd "$REPO_ROOT"
if [ "$DO_PULL" -eq 1 ]; then
    log "Aktualisiere Quellcode (Branch: $BRANCH)..."
    git fetch origin "$BRANCH" >/dev/null 2>&1 || warn "fetch fehlgeschlagen - arbeite mit lokalem Stand."
    if [ "$DO_RESET" -eq 1 ]; then
        git reset --hard "origin/$BRANCH"
        ok "Hartes Reset auf origin/$BRANCH."
    else
        # Wechsle nur, wenn noetig; pulled keine lokalen Aenderungen.
        current="$(git rev-parse --abbrev-ref HEAD)"
        if [ "$current" != "$BRANCH" ]; then
            git checkout "$BRANCH" >/dev/null 2>&1 || warn "Checkout von $BRANCH fehlgeschlagen."
        fi
        git pull origin "$BRANCH" >/dev/null 2>&1 || warn "Pull fehlgeschlagen - evtl. lokale Aenderungen vorhanden."
    fi
    ok "Quellcode ist aktuell."
fi

# ---------------------------------------------------------------------
# 5. Python-Virtualenv pruefen
# ---------------------------------------------------------------------
cd "$DJANGO_DIR"
VENV_PY="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
    warn "Kein .venv gefunden unter $REPO_ROOT/.venv."
    warn "Erstelle eines mit:  python3 -m venv $REPO_ROOT/.venv && $REPO_ROOT/.venv/bin/pip install -r requirements.txt"
    PYTHON_BIN="python"
    command -v "$PYTHON_BIN" >/dev/null 2>&1 || PYTHON_BIN="python3"
else
    PYTHON_BIN="$VENV_PY"
fi
ok "Python: $PYTHON_BIN ($($PYTHON_BIN --version 2>&1))"

# ---------------------------------------------------------------------
# 6. Datenbank migrieren
# ---------------------------------------------------------------------
log "Fuehre Migrationen aus (DB_HOST=localhost)..."
DB_HOST=localhost "$PYTHON_BIN" manage.py migrate || warn "Migrationen fehlgeschlagen - fortgesetzt."
ok "Migrationen abgeschlossen."

# ---------------------------------------------------------------------
# 7. Port 8000 pruefen - darf nicht vom Docker-Container belegt sein
# ---------------------------------------------------------------------
if command -v ss >/dev/null 2>&1; then
    if ss -ltn 'sport = :8000' 2>/dev/null | grep -q ':8000'; then
        listener_pid=$(ss -ltnp 'sport = :8000' 2>/dev/null | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2)
        err "Port 8000 ist bereits belegt (PID ${listener_pid:-?})."
        err "Wahrscheinlich laeuft noch der Docker-Container nir_django mit altem Code."
        err "Beende ihn mit:  docker update --restart=no nir_django && docker stop nir_django"
        err "oder starte dieses Skript erneut, nachdem der Container gestoppt ist."
        exit 1
    fi
fi

# ---------------------------------------------------------------------
# 8. Dev-Server starten
# ---------------------------------------------------------------------
echo ""
echo "====================================================="
echo "  NIR Intelligence Platform - LOKALER DEV-SERVER"
echo "  http://localhost:8000"
echo "  Code:  $REPO_ROOT (Branch: $(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?'))"
echo "  Commit: $(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo '?')"
echo "  Python: $PYTHON_BIN"
echo "  Strg+C zum Beenden - Daten-Container laufen weiter."
echo "====================================================="
echo ""
DB_HOST=localhost exec "$PYTHON_BIN" manage.py runserver 0.0.0.0:8000
