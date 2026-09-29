#!/bin/bash
# start_backend_stack.sh - OP45: startet den Host-Backend-Stack (Ollama, Qdrant,
# Redis) fuer die Bare-Metal-Installation (systemd-Django auf 127.0.0.1:8000).
#
# Die Django-App selbst laeuft als systemd-Service auf dem Host. Die Analyse-
# Backends laufen als Docker-Container mit Port-Freigabe an 127.0.0.1 - ohne
# diesen Stack sind die KI-Analysen (Mistral), die Aehnlichkeitssuche (Qdrant)
# und das Chatbot-RAG degraded.
#
# Idempotent: kann mehrfach ausgefuehrt werden. Fehlendes Docker/compose wird
# klar gemeldet (kein Fake-Erfolg), das Mistral-Modell wird gezogen, falls es
# fehlt.
set -uo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="${APP_DIR}/packaging/docker-compose.host-backend.yml"
OLLAMA_URL="http://127.0.0.1:11434"
MODEL="${NIR_LLM_MODEL:-mistral:latest}"

echo "== NIR Intelligence: Host-Backend-Stack (OP45) =="

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker ist nicht installiert." >&2
    echo "  Installation (Mint/Debian/Ubuntu):" >&2
    echo "    sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2" >&2
    echo "  Danach den Nutzer zur docker-Gruppe hinzufuegen und neu anmelden:" >&2
    echo "    sudo usermod -aG docker \$USER" >&2
    exit 1
fi

if docker compose version >/dev/null 2>&1; then
    compose_cmd=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    compose_cmd=(docker-compose)
else
    echo "ERROR: Docker Compose ist nicht verfuegbar." >&2
    echo "  Installation: sudo apt-get install -y docker-compose-v2" >&2
    echo "  (oder das Compose-Plugin: https://docs.docker.com/compose/install/)" >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Der Docker-Daemon ist nicht erreichbar." >&2
    echo "  Diagnose: sudo systemctl status docker; sudo systemctl start docker" >&2
    exit 1
fi

echo "-- starte ollama, qdrant, redis (Compose: ${COMPOSE_FILE})"
if ! "${compose_cmd[@]}" -f "${COMPOSE_FILE}" up -d; then
    echo "ERROR: docker compose up fehlgeschlagen." >&2
    echo "  Diagnose: ${compose_cmd[*]} -f ${COMPOSE_FILE} ps; docker logs nir_ollama" >&2
    exit 1
fi

echo "-- warte auf Ollama (max. 120s)"
ok=0
for _ in $(seq 1 120); do
    if curl -s -f "${OLLAMA_URL}/api/tags" >/dev/null 2>&1; then
        ok=1
        break
    fi
    sleep 1
done
if [ "${ok}" -ne 1 ]; then
    echo "WARNING: Ollama antwortet nicht auf ${OLLAMA_URL}/api/tags." >&2
    echo "  Diagnose: docker logs nir_ollama" >&2
    exit 1
fi

echo "-- pruefe Modell ${MODEL}"
if curl -s "${OLLAMA_URL}/api/tags" | grep -q "\"${MODEL%%:*}\""; then
    echo "-- Modell ${MODEL} vorhanden"
else
    echo "-- ziehe Modell ${MODEL} (einmalig, je nach Leitung mehrere Minuten/GB)"
    if ! docker exec nir_ollama ollama pull "${MODEL}"; then
        echo "ERROR: ollama pull ${MODEL} fehlgeschlagen." >&2
        echo "  Manuell: docker exec -it nir_ollama ollama pull ${MODEL}" >&2
        exit 1
    fi
fi

echo "== Backend-Stack aktiv =="
echo "   Django (systemd):  http://127.0.0.1:8000"
echo "   Ollama:            ${OLLAMA_URL}"
echo "   Qdrant:            http://127.0.0.1:6333"
echo "   Redis:             redis://127.0.0.1:6379"
exit 0
