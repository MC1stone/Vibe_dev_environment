#!/bin/bash
# OP51: stops the Docker stack (legacy host-server stopper, now delegating).
set -e
cd "$(dirname "$0")/.."
docker compose down
