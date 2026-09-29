#!/bin/bash
# build_deb.sh - build nir_intelligence_main.deb from the repository tree.
# Bundles the platform (django_project, agents, services, config, templates,
# tests fixtures excluded) into /opt/nir_intelligence with the DEBIAN control
# files, the systemd unit and install.sh. Output: dist/nir_intelligence_main.deb
#
# Usage:  ./packaging/build_deb.sh [version]

set -e

VERSION="${1:-1.1.0}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$(mktemp -d /tmp/nir_deb_build.XXXXXX)"
APP_DIR="${STAGE}/opt/nir_intelligence"
DIST_DIR="${ROOT}/dist"

trap 'rm -rf "${STAGE}"' EXIT

echo "== building nir-intelligence-main ${VERSION} =="

mkdir -p "${APP_DIR}/packaging" "${DIST_DIR}"

# --- application payload ---------------------------------------------------
for item in django_project agents services config templates tasks skills \
            docs scripts requirements.txt README.md path_config.py; do
    if [ -e "${ROOT}/${item}" ]; then
        cp -r "${ROOT}/${item}" "${APP_DIR}/"
    fi
done
# OP45 host backend stack ships inside packaging/
cp "${ROOT}/packaging/docker-compose.host-backend.yml" "${APP_DIR}/packaging/"
cp "${ROOT}/packaging/start_backend_stack.sh" "${APP_DIR}/packaging/"
chmod 755 "${APP_DIR}/packaging/start_backend_stack.sh"

# strip caches and heavy build output from the payload
find "${APP_DIR}" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "${APP_DIR}" -type d -name '.pytest_cache' -prune -exec rm -rf {} + 2>/dev/null || true
rm -rf "${APP_DIR}/django_project/db.sqlite3" \
       "${APP_DIR}/django_project/media" \
       "${APP_DIR}/django_project/staticfiles" 2>/dev/null || true

# --- packaging metadata ------------------------------------------------------
cp -r "${ROOT}/packaging/DEBIAN" "${STAGE}/DEBIAN"
sed -i "s/^Version: .*/Version: ${VERSION}/" "${STAGE}/DEBIAN/control"
cp "${ROOT}/packaging/nir_intelligence.service" "${APP_DIR}/packaging/"
cp "${ROOT}/packaging/install.sh" "${APP_DIR}/install.sh"
chmod 755 "${STAGE}/DEBIAN/postinst" "${APP_DIR}/install.sh"
chmod 644 "${STAGE}/DEBIAN/control"

# sanity: the archive installer must sit at the expected location
test -f "${APP_DIR}/install.sh"
# sanity: the OP45 host backend stack must sit at the expected location
test -f "${APP_DIR}/packaging/docker-compose.host-backend.yml"
test -f "${APP_DIR}/packaging/start_backend_stack.sh"
test -x "${APP_DIR}/packaging/start_backend_stack.sh"

echo "-- staged payload: $(du -sh "${APP_DIR}" | cut -f1)"

dpkg-deb -b --root-owner-group "${STAGE}" "${DIST_DIR}/nir_intelligence_main.deb"

echo "== built: ${DIST_DIR}/nir_intelligence_main.deb =="
dpkg-deb -I "${DIST_DIR}/nir_intelligence_main.deb" | head -20
