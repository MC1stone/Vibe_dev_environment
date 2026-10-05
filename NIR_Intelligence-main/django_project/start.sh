#!/bin/bash
# OP51: The single supported way to run the platform is the Docker stack.
# This legacy host-Django starter now delegates to docker compose and
# warns about the removed parallel-host-server mode (no second port,
# no kill -9 of unrelated manage.py processes anymore).
set -e
cd "$(dirname "$0")/.."
echo "== NIR Intelligence Platform - Start (Docker-Stack) =="
if [ -n "$1" ]; then
  echo "Hinweis: Port-Argument wird ignoriert - die Plattform laeuft im Docker-Stack auf Port 8000."
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker ist nicht installiert/verfuegbar." >&2
  echo "  Installation: https://docs.docker.com/engine/install/" >&2
  exit 1
fi
docker compose up -d
echo
echo "Web-UI:      http://localhost:8000/"
echo "Admin:        http://localhost:8000/admin/"
echo "ILIAS:        http://localhost:8080/"
echo "Status:       docker compose ps"
echo "Stoppen:      docker compose down"
