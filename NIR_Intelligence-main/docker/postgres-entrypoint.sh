#!/bin/bash
# Custom postgres entrypoint: keep the database password in sync with
# POSTGRES_PASSWORD from the compose environment on EVERY container start
# (the official image applies it only when the data volume is first
# created - incident 2026-10-14: a later change of the env var left the
# DB with the old password and Django silently fell back to SQLite).
set -e

# Start the official postgres entrypoint in the background (it handles
# first-run initialisation and then runs the server in the foreground of
# its own subprocess).
docker-entrypoint.sh postgres &
ENTRYPOINT_PID=$!

# Wait until postgres accepts connections (max ~60s).
i=0
until pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -ge 60 ]; then
        echo "WARNING: postgres not ready after 60s - skipping password sync"
        wait "$ENTRYPOINT_PID"
        exit $?
    fi
    sleep 1
done

echo "Syncing password of ${POSTGRES_USER} with POSTGRES_PASSWORD env ..."
if psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" \
    -c "ALTER USER \"${POSTGRES_USER}\" WITH PASSWORD '${POSTGRES_PASSWORD}';" 2>/dev/null; then
    echo "DB password synced with environment."
else
    # Local socket auth allows the ALTER even with a stale password, but
    # escape-sensitive passwords may need manual handling.
    echo "WARNING: password sync failed - check POSTGRES_PASSWORD escaping."
fi

wait "$ENTRYPOINT_PID"
