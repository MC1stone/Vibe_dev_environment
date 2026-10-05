# NIR Intelligence Platform - robust Ollama reachability probe (OP50)
# Release-Fix: Ollama startet im Container langsamer als Django/Background-Crew
# hochfahren. Die bisherigen Einzelprobes (ein GET /api/tags, timeout 5s)
# lieferten deshalb direkt nach dem Systemstart ein False, und alle
# KI-Pass fellen ehrlich, aber unnoetig auf die deterministische
# Fallback-Analyse zurueck (Fallback-Quote nahe 100% statt ~1%).
#
# Dieser Probe aendert das Verhaeltnis auf das Release-Ziel:
#   - Beim ersten Aufruf (typisch direkt nach dem Start) wird mit
#     Wiederholungen und Backoff geprueft (Default: 5 Versuche,
#     1.0s Backoff), bis Ollama sein Modellverzeichnis meldet.
#   - Erfolgreiche Probes werden kurz gecacht (Default 60s), damit
#     Hot-Paths keine Latenz erhalten.
#   - Fehlgeschlagene Probes werden kuerzer gecacht (Default 30s), damit
#     ein zwischenzeitlich startender Ollama schnell erkannt wird, ohne
#     dass jeder Request in Timeouts laeuft.
# Nie werfend: alle Fehler gelten als "nicht erreichbar".

import logging
import os
import time
from typing import Optional

logger = logging.getLogger("Service.OllamaHealth")

DEFAULT_BASE_URL = "http://localhost:11434"

_ATTEMPTS = int(os.environ.get("NIR_OLLAMA_PROBE_ATTEMPTS", "5"))
_TIMEOUT = float(os.environ.get("NIR_OLLAMA_PROBE_TIMEOUT", "5"))
_BACKOFF = float(os.environ.get("NIR_OLLAMA_PROBE_BACKOFF", "1.0"))
_SUCCESS_TTL = float(os.environ.get("NIR_OLLAMA_PROBE_SUCCESS_TTL", "60"))
_FAILURE_TTL = float(os.environ.get("NIR_OLLAMA_PROBE_FAILURE_TTL", "30"))

_cache: dict = {}


def default_base_url() -> str:
    """Base URL like the other Ollama clients: explicit arg > OLLAMA_URL."""
    return (os.environ.get("OLLAMA_URL") or DEFAULT_BASE_URL).rstrip("/")


def _probe_once(url: str, timeout: float) -> bool:
    try:
        import requests
        response = requests.get(f"{url}/api/tags", timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


def ollama_reachable(base_url: Optional[str] = None,
                     attempts: Optional[int] = None,
                     timeout: Optional[float] = None,
                     backoff: Optional[float] = None) -> bool:
    """Robust reachability check for the local Ollama service.

    Retries with backoff on the first call after startup (or after the
    failure cache expired), so a slow-starting Ollama no longer sends the
    whole analysis pipeline into the deterministic fallback. Results are
    cached briefly; never raises.
    """
    url = (base_url or default_base_url()).rstrip("/")
    now = time.monotonic()
    cached = _cache.get(url)
    if cached:
        ok, expires = cached
        if now < expires:
            return ok
    n_attempts = attempts if attempts is not None else _ATTEMPTS
    n_timeout = timeout if timeout is not None else _TIMEOUT
    n_backoff = backoff if backoff is not None else _BACKOFF
    ok = False
    for attempt in range(max(1, n_attempts)):
        ok = _probe_once(url, n_timeout)
        if ok:
            break
        if attempt < n_attempts - 1 and n_backoff > 0:
            time.sleep(n_backoff)
    _cache[url] = (ok, now + (_SUCCESS_TTL if ok else _FAILURE_TTL))
    if not ok:
        logger.warning("Ollama nicht erreichbar unter %s (%d Versuche)",
                        url, max(1, n_attempts))
    return ok


def reset_cache() -> None:
    """Test hook: forget cached probe results."""
    _cache.clear()
