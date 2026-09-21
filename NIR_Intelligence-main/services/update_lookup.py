# NIR Intelligence Platform - Online update lookups (roadmap OP4, MO 15)
# Queries PyPI and Docker Hub for the latest available versions of the
# components declared in the platform manifests. The HTTP transport is
# injectable; without network access every lookup degrades gracefully and
# the monitor falls back to the offline behaviour (S7).
import re
from typing import Any, Callable, Dict, Optional

try:
    import requests
except Exception:
    requests = None

PYPI_JSON_URL = "https://pypi.org/pypi/{name}/json"
DOCKER_HUB_TAGS_URL = "https://hub.docker.com/v2/repositories/{repository}/tags?page_size=25"

DOCKER_LIBRARY_NAMESPACE = "library"


class UpdateLookupService:
    """Looks up the latest available versions on PyPI and Docker Hub.

    The transport is injectable for offline tests (same pattern as the
    ILIAS API service). All network errors degrade to ``None`` results -
    the update monitor remains functional offline (S7 guarantee).
    """

    def __init__(self, transport: Optional[Callable[..., Any]] = None,
                 timeout: int = 15):
        self._timeout = timeout
        self._transport = transport or self._default_transport

    def _default_transport(self, method: str, url: str, **kwargs):
        if requests is None:
            raise RuntimeError("requests package not available")
        return requests.request(method, url, timeout=self._timeout, **kwargs)

    # ---------- PyPI ----------

    def latest_pypi_version(self, package: str) -> Optional[str]:
        """Latest non-yanked, non-prerelease version on PyPI, or None."""
        url = PYPI_JSON_URL.format(name=package)
        try:
            response = self._transport("GET", url)
            status = getattr(response, "status_code", None)
            if status is not None and status != 200:
                return None
            payload = getattr(response, "json", lambda: {})()
        except Exception:
            return None
        releases = payload.get("releases", {})
        candidates = []
        fallback = None
        for version, files in releases.items():
            if not files:
                continue
            if any(f.get("yanked", False) for f in files):
                continue
            if self._is_prerelease(version):
                if fallback is None:
                    fallback = version
                continue
            candidates.append(version)
        if candidates:
            return max(candidates, key=self._version_sort_key)
        if fallback:
            return fallback
        info = payload.get("info", {})
        return info.get("version")

    @staticmethod
    def _is_prerelease(version: str) -> bool:
        """Heuristic pre-release detection without a new dependency."""
        import packaging.version as _pv

        try:
            return _pv.parse(str(version)).is_prerelease
        except Exception:
            return True

    @staticmethod
    def _version_sort_key(version: str):
        """Numeric-aware sort key for version strings (no new dependency)."""
        import re as _re

        return [
            (0, int(part)) if part.isdigit() else (1, part)
            for part in _re.split(r"[.-]", str(version))
        ]

    # ---------- Docker Hub ----------

    def latest_docker_tag(self, image: str) -> Optional[str]:
        """Latest stable (non-'latest', semver-like) tag on Docker Hub."""
        repository = self._normalize_repository(image)
        url = DOCKER_HUB_TAGS_URL.format(repository=repository)
        try:
            response = self._transport("GET", url)
            status = getattr(response, "status_code", None)
            if status is not None and status != 200:
                return None
            payload = getattr(response, "json", lambda: {})()
        except Exception:
            return None
        tags = [t.get("name") for t in payload.get("results", []) if t.get("name")]
        stable = [t for t in tags
                  if t not in ("latest",)
                  and re.match(r"^[0-9]+(\.[0-9]+)*$", str(t))]
        if not stable:
            return None
        return max(stable, key=self._version_sort_key)

    @staticmethod
    def _normalize_repository(image: str) -> str:
        """Normalize an image reference to a Docker Hub repository path."""
        name = image.split("@")[0].strip()
        head, _, last = name.rpartition("/")
        if ":" in last:
            last = last.split(":")[0]
            name = f"{head}/{last}" if head else last
        first, sep, rest = name.partition("/")
        if not sep:
            name = f"{DOCKER_LIBRARY_NAMESPACE}/{name}"
            first, sep, rest = name.partition("/")
        if rest and ("." in first or ":" in first or first in ("localhost",)):
            return rest
        return name

    # ---------- batch ----------

    def enrich_report(self, components, online: bool = True) -> int:
        """Enrich ComponentEntry objects with the latest available version.

        Sets ``available`` (latest upstream version), ``update_available``
        and ``note`` on every entry it can look up. Returns the number of
        entries successfully enriched. Degrades gracefully when offline.
        """
        if not online:
            return 0
        enriched = 0
        for entry in components:
            if entry.kind == "pip":
                available = self.latest_pypi_version(entry.name)
                if available:
                    entry.available = available
                    self._flag(entry, available)
                    enriched += 1
            elif entry.kind == "docker":
                available = self.latest_docker_tag(entry.name)
                if available:
                    entry.available = available
                    self._flag(entry, available)
                    enriched += 1
        return enriched

    @staticmethod
    def _flag(entry, available: str) -> None:
        import packaging.version as _pv

        try:
            available_v = _pv.parse(available)
        except Exception:
            return
        reference = getattr(entry, "installed", None) or getattr(entry, "declared", None)
        if not reference or reference in ("", "latest"):
            entry.update_available = None
            entry.note = f"upstream latest: {available} - compare manually"
            return
        try:
            reference_v = _pv.parse(reference)
        except Exception:
            return
        if available_v > reference_v:
            entry.update_available = True
            entry.note = f"upstream {available} newer than {reference}"
        else:
            entry.update_available = False
            entry.note = f"upstream latest: {available}"


def create_update_lookup(transport=None, timeout: int = 15) -> "UpdateLookupService":
    """Factory used by scripts/CI to get the online update lookup service"""
    return UpdateLookupService(transport=transport, timeout=timeout)
