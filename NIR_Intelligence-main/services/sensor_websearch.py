# NIR Intelligence Platform - Sensor Websearch Service (OP49)
# Opt-in lookup of unknown sensors via a local Ollama instance. Disabled by
# default; the platform remains offline/CI-safe unless explicitly enabled.
# Results are marked as external and unverified (honesty rule).
import os
from typing import Any, Dict, List, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

OLLAMA_DEFAULT_URL = "http://localhost:11434"
DEFAULT_MODEL = os.getenv("NIR_SENSOR_WEBSEARCH_MODEL", "mistral")
DEFAULT_TIMEOUT = 30

SEARCH_PROMPT = (
    "You are a technical assistant for NIR/UV-Vis/Raman spectroscopy sensors. "
    "A measurement was uploaded whose metadata mentions an unknown sensor: "
    "'{sensor}'. Summarize what is publicly known about this sensor or device: "
    "manufacturer, measurement principle, wavelength range, typical applications, "
    "and - if available - official or reputable project pages. Answer in the "
    "language of the sensor name (German names get a German answer). If you are "
    "not sure, say so explicitly. Keep it under 250 words."
)


def websearch_enabled() -> bool:
    """The lookup only runs when explicitly enabled (opt-in)."""
    return os.getenv("NIR_SENSOR_WEBSEARCH", "").strip().lower() in ("1", "true", "yes", "on")


def ollama_available(base_url: Optional[str] = None) -> bool:
    if not REQUESTS_AVAILABLE:
        return False
    url = (base_url or os.getenv("NIR_SENSOR_WEBSEARCH_URL", OLLAMA_DEFAULT_URL)).rstrip("/")
    try:
        from services.ollama_health import ollama_reachable
        return ollama_reachable(url)
    except Exception:
        return False


def search_sensor(sensor_name: str,
                  base_url: Optional[str] = None,
                  model: Optional[str] = None) -> Dict[str, Any]:
    """Ask the local Ollama instance about an unknown sensor.

    Returns a result dict with 'enabled', 'available', 'summary' and 'source'.
    Never raises: failures are reported honestly in the result.
    """
    result: Dict[str, Any] = {
        "sensor": sensor_name,
        "enabled": websearch_enabled(),
        "available": False,
        "summary": "",
        "model": model or DEFAULT_MODEL,
        "source": "ollama",
    }
    if not websearch_enabled():
        return result
    if not REQUESTS_AVAILABLE:
        result["error"] = "requests library not available"
        return result
    url = (base_url or os.getenv("NIR_SENSOR_WEBSEARCH_URL", OLLAMA_DEFAULT_URL)).rstrip("/")
    if not ollama_available(url):
        result["error"] = "ollama not reachable at %s" % url
        return result
    result["available"] = True
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [
            {"role": "user",
             "content": SEARCH_PROMPT.format(sensor=sensor_name)},
        ],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    try:
        response = requests.post(f"{url}/api/chat", json=payload,
                                 timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        result["summary"] = (data.get("message") or {}).get("content", "").strip()
    except Exception as exc:
        result["error"] = "ollama request failed: %s" % exc
    return result


def summarize_unmatched(unmatched_usage: List[Dict[str, Any]],
                        limit: int = 3) -> List[Dict[str, Any]]:
    """Run the opt-in lookup for unmatched sensor names (deduplicated)."""
    seen = set()
    results = []
    for entry in unmatched_usage or []:
        name = entry.get("instrument_type") or entry.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        results.append(search_sensor(name))
        if len(results) >= limit:
            break
    return results
