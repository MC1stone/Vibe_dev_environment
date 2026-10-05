#!/bin/bash
# OP51: stack status (legacy host-server check, now delegating).
set -e
cd "$(dirname "$0")/.."
docker compose ps
echo "Health-Endpoint: http://localhost:8000/health/ (im Browser pruefen)"
