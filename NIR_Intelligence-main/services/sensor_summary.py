#!/usr/bin/env python3
"""NIR Intelligence Platform - KI-generated sensor page summary (OP53).

Summarizes everything the platform knows about one sensor (adapter
profile, recorded usage, documents, suggestions) into a compact German
page intro using the local Ollama LLM. The client is injectable (same
pattern as MetadataLLMService) so tests run against a fake and CI stays
offline. summarize() NEVER raises: it returns None when the LLM is
unavailable - the page then renders the structured data honestly.
"""
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Service.SensorSummary")

DEFAULT_LLM_MODEL = os.environ.get("NIR_LLM_MODEL", "mistral")
OLLAMA_DEFAULT_URL = "http://localhost:11434"

_SUMMARY_PROMPT = """Du bist ein NIR-Spektroskopie-Experte. Fasse auf Basis NUR der folgenden strukturierten Daten einen kurzen, sachlichen deutschsprachigen Ueberblick (max. 6 Saetze, keine Aufzaehlungen) ueber den Sensor zusammen: Was ist das fuer ein Geraet bzw. was ist bekannt, wie wird es auf der Plattform genutzt (Messungen, Projekte), welche Einstellungen sind dokumentiert und was gibt es an Hinweisen (Dokumente, Optimierungsvorschlaege)? Erfinde keine technischen Details, die nicht in den Daten stehen. Wenn Angaben fehlen, lass sie weg.

Sensor-Daten (JSON):
{data}
"""


class SensorSummaryService:
    """KI-first sensor summary with an honest no-LLM fallback."""

    def __init__(self, client: Optional[Any] = None, max_data_chars: int = 6000):
        if client is None:
            from services.metadata_llm import OllamaMetadataClient
            client = OllamaMetadataClient()
        self.client = client
        self.max_data_chars = max_data_chars

    def summarize(self, sensor_name: str, facts: Dict[str, Any]) -> Optional[str]:
        """Return a German summary paragraph or None (LLM unavailable).

        facts: dict with the structured sensor knowledge (adapter
        profile, usage, documents, suggestions, ...). Never raises.
        """
        import json
        payload = {
            "sensor": sensor_name,
            "adapter_profil": facts.get("sensor") or None,
            "beschreibung": facts.get("description") or None,
            "verwendung_aus_datenbank": facts.get("usage") or None,
            "dokumente": [d.get_summary() if hasattr(d, "get_summary") else d
                          for d in (facts.get("documents") or [])],
            "optimierungsvorschlaege": (facts.get("suggestions") or [])[:10],
        }
        payload = {k: v for k, v in payload.items() if v not in (None, [], {})}
        if not payload or list(payload) == ["sensor"]:
            return None
        try:
            data_json = json.dumps(payload, ensure_ascii=False,
                                   default=str)[: self.max_data_chars]
        except Exception:
            return None
        prompt = _SUMMARY_PROMPT.format(data=data_json)
        try:
            raw = self.client.chat(prompt)
        except Exception as e:
            logger.info("LLM sensor summary unavailable for %s: %s",
                        sensor_name, e)
            return None
        return self._clean(raw)

    def _clean(self, raw: Optional[str]) -> Optional[str]:
        """Keep plain text answers, unwrap json {'summary': ...} answers."""
        if not raw:
            return None
        text = str(raw).strip()
        if not text:
            return None
        if text.startswith("{"):
            import json
            try:
                parsed = json.loads(text)
                for key in ("summary", "text", "antwort", "answer"):
                    if isinstance(parsed, dict) and isinstance(parsed.get(key), str):
                        return parsed[key].strip() or None
            except Exception:
                pass
        if len(text) > 4000:
            text = text[:4000]
        return text
