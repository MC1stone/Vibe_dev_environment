#!/bin/bash
# bootstrap_install.sh - installiert Ansible (falls fehlend) und startet
# direkt das OP26-Installationsplaybook. Ein Aufruf auf der frisch
# installierten Zielmaschine genuegt:
#
#   sudo bash /mnt/ventoy/ansible/bootstrap_install.sh
#   (ohne sudo: fragt das Playbook nach dem Become-Passwort)
#
# Es wird das Vollpaket 'ansible' installiert (apt, Fallback pipx) - nicht
# nur ansible-core: die ansible.cfg dieses Verzeichnisses nutzt den
# 'yaml'-Stdout-Callback sowie profile_tasks/timer aus community.general,
# die im Core-Paket fehlen und den Lauf zum Absturz bringen.
# Idempotent: ist ansible-playbook bereits vorhanden, entfaellt die
# Installation; das Playbook selbst ist idempotent (OP26).

set -euo pipefail

PLAYBOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
PLAYBOOK="${PLAYBOOK_DIR}/install_nir_intelligence.yml"

if [ ! -f "${PLAYBOOK}" ]; then
    echo "ERROR: Playbook nicht gefunden: ${PLAYBOOK}" >&2
    exit 1
fi

# --- Ansible installieren, falls fehlend -----------------------------------
if ! command -v ansible-playbook >/dev/null 2>&1; then
    echo "== ansible-playbook nicht gefunden - installiere Ansible =="
    if [ "$(id -u)" -eq 0 ]; then
        SUDO=""
    else
        SUDO="sudo"
    fi
    if ! ${SUDO} apt-get update && ${SUDO} apt-get install -y ansible; then
        echo "-- apt-Paket 'ansible' nicht verfuegbar - Fallback: pipx =="
        if ! command -v pipx >/dev/null 2>&1; then
            ${SUDO} apt-get install -y pipx || python3 -m pip install --user pipx
        fi
        pipx install --include-deps ansible
        pipx ensurepath >/dev/null
        export PATH="${HOME}/.local/bin:${PATH}"
    fi
    command -v ansible-playbook >/dev/null 2>&1 || {
        echo "ERROR: ansible-playbook konnte nicht installiert werden." >&2
        exit 1
    }
fi

echo "== starte Installationsplaybook =="

# --- Become-Passwort nur anfordern, wenn noetig ---------------------------
# Als root laeuft das Playbook direkt; mit passwortlosem sudo ebenso;
# andernfalls fragt --ask-become-pass nach dem Passwort.
if [ "$(id -u)" -eq 0 ] || sudo -n true >/dev/null 2>&1; then
    exec ansible-playbook -i localhost, -c local "${PLAYBOOK}" "$@"
else
    exec ansible-playbook -i localhost, -c local "${PLAYBOOK}" \
        --ask-become-pass "$@"
fi
