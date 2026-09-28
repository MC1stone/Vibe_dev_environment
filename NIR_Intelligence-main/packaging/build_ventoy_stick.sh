#!/bin/bash
# build_ventoy_stick.sh - erzeugt den ansible-Payload fuer den Ventoy-Stick.
#
# Der Stick erwartet (OP26/OP42) unter <mount>/ansible/:
#   install_nir_intelligence.yml   das OP26-Installationsplaybook
#   bootstrap_install.sh            OP42: installiert Ansible + startet das Playbook
#   nir_intelligence_main.deb      Eigenentwicklung als .deb (bevorzugt)
#   nir_intelligence_main.tar.gz    Fallback: Archiv mit install.sh
#   INSTALL_NIR_INTELLIGENCE.md     Kurzanleitung
#
# Usage:
#   ./packaging/build_ventoy_stick.sh [ziel_pfad]
#
#   - Ohne Argument: Staging unter dist/ventoy_stick/
#   - Mit Argument (z. B. Mountpunkt /mnt/ventoy): zusaetzlich den
#     ansible/-Ordner dorthin kopieren - der Stick ist danach einsatzbereit.
#
# Idempotent: Staging wird vor jedem Lauf neu aufgebaut.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="${ROOT}/dist"
STAGE_DIR="${DIST_DIR}/ventoy_stick"
ANSIBLE_STAGE="${STAGE_DIR}/ansible"
TARGET_DIR="${1:-}"

echo "== baue Ventoy-Stick-Inhalt (ansible-Payload) =="

# ---------------------------------------------------------------------------
# 1. .deb-Paket bauen (bevorzugte Installationsmethode)
# ---------------------------------------------------------------------------
if command -v dpkg-deb >/dev/null 2>&1; then
    bash "${ROOT}/packaging/build_deb.sh"
else
    echo "-- dpkg-deb nicht verfuegbar - ueberspringe .deb-Build"
    echo "   (die Archiv-Methode des Playbooks genuegt als Fallback)"
fi

# ---------------------------------------------------------------------------
# 2. tar.gz-Archiv bauen (Archiv-Methode, OP26/OP27-Layout:
#    Wurzel nir_intelligence/ mit install.sh an der Spitze)
# ---------------------------------------------------------------------------
TARBALL="${DIST_DIR}/nir_intelligence_main.tar.gz"
ARCHIVE_STAGE="$(mktemp -d /tmp/nir_archive_build.XXXXXX)"
trap 'rm -rf "${ARCHIVE_STAGE}"' EXIT

APP_DIR="${ARCHIVE_STAGE}/nir_intelligence"
mkdir -p "${APP_DIR}"

for item in django_project agents services config templates tasks skills \
            docs requirements.txt README.md path_config.py; do
    if [ -e "${ROOT}/${item}" ]; then
        cp -r "${ROOT}/${item}" "${APP_DIR}/"
    fi
done
find "${APP_DIR}" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "${APP_DIR}" -type d -name '.pytest_cache' -prune -exec rm -rf {} + 2>/dev/null || true
rm -rf "${APP_DIR}/django_project/db.sqlite3" \
       "${APP_DIR}/django_project/media" \
       "${APP_DIR}/django_project/staticfiles" 2>/dev/null || true

cp -r "${ROOT}/packaging" "${APP_DIR}/packaging"
cp "${ROOT}/packaging/install.sh" "${APP_DIR}/install.sh"
chmod 755 "${APP_DIR}/install.sh"

test -f "${APP_DIR}/install.sh"
tar -czf "${TARBALL}" -C "${ARCHIVE_STAGE}" nir_intelligence
echo "-- archiv gebaut: ${TARBALL}"

# ---------------------------------------------------------------------------
# 3. Stick-Verzeichnis strukturieren
# ---------------------------------------------------------------------------
rm -rf "${STAGE_DIR}"
mkdir -p "${ANSIBLE_STAGE}"

cp "${ROOT}/ansible/install_nir_intelligence.yml" "${ANSIBLE_STAGE}/"
cp "${ROOT}/ansible/bootstrap_install.sh" "${ANSIBLE_STAGE}/"
cp "${ROOT}/ansible/INSTALL_NIR_INTELLIGENCE.md" "${ANSIBLE_STAGE}/"
chmod 755 "${ANSIBLE_STAGE}/bootstrap_install.sh"

if [ -f "${DIST_DIR}/nir_intelligence_main.deb" ]; then
    cp "${DIST_DIR}/nir_intelligence_main.deb" "${ANSIBLE_STAGE}/"
fi
cp "${TARBALL}" "${ANSIBLE_STAGE}/"

# ---------------------------------------------------------------------------
# 4. Verifikation des Stagings
# ---------------------------------------------------------------------------
test -f "${ANSIBLE_STAGE}/install_nir_intelligence.yml"
test -x "${ANSIBLE_STAGE}/bootstrap_install.sh"
test -f "${ANSIBLE_STAGE}/nir_intelligence_main.tar.gz"
if [ -f "${DIST_DIR}/nir_intelligence_main.deb" ]; then
    test -f "${ANSIBLE_STAGE}/nir_intelligence_main.deb"
fi

echo "== Stick-Inhalt bereit: ${ANSIBLE_STAGE} =="
ls -la "${ANSIBLE_STAGE}"

# ---------------------------------------------------------------------------
# 5. Optional: auf den echten Stick (Mountpunkt) kopieren
# ---------------------------------------------------------------------------
if [ -n "${TARGET_DIR}" ]; then
    if [ ! -d "${TARGET_DIR}" ]; then
        echo "ERROR: Zielpfad ist kein Verzeichnis (Stick gemountet?): ${TARGET_DIR}" >&2
        exit 1
    fi
    mkdir -p "${TARGET_DIR}/ansible"
    cp "${ANSIBLE_STAGE}"/* "${TARGET_DIR}/ansible/"
    echo "== ansible-Payload nach ${TARGET_DIR}/ansible/ kopiert =="
    echo "   Auf der Zielmaschine genuegt jetzt:"
    echo "   sudo bash ${TARGET_DIR}/ansible/bootstrap_install.sh"
fi
