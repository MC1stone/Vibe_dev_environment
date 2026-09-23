#!/bin/bash
# install.sh - archive installation entry point (OP26 archive method).
# The archive extracts to nir_intelligence/ (-> /opt/nir_intelligence).
# This script performs the same steps as the .deb postinst: venv,
# dependencies, database migration and systemd service. Idempotent.

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_USER="nir"
APP_GROUP="nir"
VENV_DIR="${APP_DIR}/venv"
SERVICE_NAME="nir_intelligence"
SERVICE_SRC="${APP_DIR}/packaging/nir_intelligence.service"
SERVICE_DST="/etc/systemd/system/${SERVICE_NAME}.service"

echo "== NIR Intelligence Main: installation from archive =="

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: run with root rights (sudo ./install.sh)" >&2
    exit 1
fi

# --- service user ---------------------------------------------------------
if ! getent group "${APP_GROUP}" >/dev/null; then
    groupadd --system "${APP_GROUP}"
fi
if ! id -u "${APP_USER}" >/dev/null 2>&1; then
    useradd --system --gid "${APP_GROUP}" --home-dir "${APP_DIR}" \
        --shell /usr/sbin/nologin "${APP_USER}"
fi

# --- Python venv + dependencies -------------------------------------------
if [ ! -f "${VENV_DIR}/bin/activate" ]; then
    echo "-- creating venv"
    python3 -m venv "${VENV_DIR}"
fi
"${VENV_DIR}/bin/pip" install --quiet --upgrade pip || true
echo "-- installing requirements (missing optional ones continue)"
"${VENV_DIR}/bin/pip" install --quiet -r "${APP_DIR}/requirements.txt" || \
    echo "WARNING: some requirements failed; agents degrade gracefully" >&2

chown -R "${APP_USER}:${APP_GROUP}" "${APP_DIR}"

# --- database migration -----------------------------------------------------
echo "-- migrating database"
cd "${APP_DIR}/django_project"
sudo -u "${APP_USER}" "${VENV_DIR}/bin/python" manage.py migrate --noinput || \
    echo "WARNING: migration failed (run manually)" >&2

# --- systemd service ---------------------------------------------------------
if [ -f "${SERVICE_SRC}" ]; then
    echo "-- installing systemd service"
    install -m 644 "${SERVICE_SRC}" "${SERVICE_DST}"
    systemctl daemon-reload || true
    systemctl enable "${SERVICE_NAME}.service" >/dev/null 2>&1 || true
    systemctl restart "${SERVICE_NAME}.service" || true
else
    echo "NOTE: no service file found - start via" \
         "${VENV_DIR}/bin/python manage.py runserver 127.0.0.1:8000" >&2
fi

# --- completion marker (OP26 playbook idempotency guard) ----------------------
touch "${APP_DIR}/.install_completed"

echo "== done - web UI: http://127.0.0.1:8000 =="
exit 0
