# NIR Intelligence Platform - LLM metadata extraction service (OP31)
# KI-first metadata extraction via the local Ollama/Mistral service. The LLM
# is the PRIMARY extractor (mission statement: Ollama + mistral always run
# locally); the deterministic regex/header layer validates and secures.
#
# Strict anti-hallucination contract (hard requirement, OP14 truthfulness):
#   1. The model may ONLY report values that appear VERBATIM in the source
#      text. The guard below enforces this in CODE, not by prompt trust:
#      every extracted value must be found in the normalised source text,
#      otherwise it is rejected and logged as a rejected hallucination.
#   2. The model must cite the evidence snippet for every field; fields
#      without verbatim evidence are dropped.
#   3. The model never invents fields: only canonical platform fields are
#      accepted (aliases are folded onto the canonical names).
#   4. Conflicts (deterministic header value != LLM value) are NEVER
#      silently resolved: the hard fact wins, the conflict is recorded
#      and escalated to the user (report + chatbot, see ingest/ChatbotAgent).
#   5. Uncertainty becomes an explicit question for the user - the LLM
#      lists 'questions' and the platform surfaces them instead of
#      guessing.
#
# Never raises: when Ollama is unreachable the caller falls back to the
# deterministic extraction (resilience, no data loss).

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Service.MetadataLLM")

OLLAMA_DEFAULT_URL = "http://ollama:11434"
DEFAULT_LLM_MODEL = "mistral"

# Canonical platform metadata fields (task_definition.yaml categories +
# OP28 canonical loader fields). The LLM output is folded onto these -
# anything else is rejected, so the model cannot invent new namespaces.
CANONICAL_FIELDS = [
    "sample_id", "operator_name", "instrument_type", "timestamp",
    "temperature", "humidity", "location", "integration_time",
    "scan_count", "resolution", "wavelength_range", "serial_number",
    "notes", "description",
]

_EXTRACTION_PROMPT = """Du extrahierst Mess-Metadaten aus dem Text einer Spektrometer-Datei.

STRENGE REGELN (Verstoß = Wert wird verworfen):
1. NUR Werte nennen, die WORTWÖRTLICH im Text stehen. Niemals raten, ergänzen oder korrigieren.
2. Für JEDES Feld die Fundstelle (evidence) als exaktes Textzitat angeben.
3. Fehlt ein Feld: null angegeben. Keine erfundenen Werte, keine Synonyme umformulieren.
4. Bei Widersprüchen oder Mehrdeutigkeit: das Feld auf null setzen und eine Frage in "questions" formulieren.

Antworte NUR mit JSON in exakt dieser Struktur:
{{"fields": {{"operator_name": {{"value": ..., "evidence": "wörtliches Zitat"}} | null, ...}},
 "questions": ["Frage an den Nutzer, wenn etwas unklar ist"]}}

Kanonische Felder: sample_id, operator_name, instrument_type, timestamp,
temperature, humidity, location, integration_time, scan_count,
resolution, wavelength_range, serial_number, notes, description.

Text aus der Datei "{file_name}":
{text}
"""


class OllamaMetadataClient:
    """Thin HTTP client for the Ollama chat API (same style as the
    ChatbotService/EmbeddingService clients)."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None,
                 timeout: int = 60):
        self.base_url = (base_url or os.environ.get("OLLAMA_URL")
                         or OLLAMA_DEFAULT_URL).rstrip("/")
        self.model = model or os.environ.get("NIR_LLM_MODEL") or DEFAULT_LLM_MODEL
        self.timeout = timeout

    def chat(self, prompt: str) -> Optional[str]:
        import requests
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
        }
        response = requests.post(f"{self.base_url}/api/chat", json=payload,
                                 timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return (data.get("message") or {}).get("content")

    def is_available(self) -> bool:
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False


def _normalise(text: str) -> str:
    """Case-insensitive, whitespace-folded comparison basis for the
    verbatim guard (German umlauts kept, punctuation flexible)."""
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _verbatim(value: Any, source_norm: str) -> bool:
    """Anti-hallucination guard: the value must appear in the source text.
    Numbers tolerate format variants (25 / 25.0), text must match as a
    whole (word-boundary, whitespace-folded) - partial invented strings
    fail the guard."""
    text = _normalise(value)
    if not text:
        return False
    if text in source_norm:
        return True
    # numeric tolerance: '25.0' matches '25' and vice versa
    try:
        return str(float(str(value).replace(",", "."))) in {
            str(float(str(value).replace(",", "."))),
        } and _number_in_source(str(value), source_norm)
    except (ValueError, TypeError):
        return False


def _number_in_source(value: str, source_norm: str) -> bool:
    try:
        target = float(value.replace(",", "."))
    except (ValueError, TypeError):
        return False
    for match in re.finditer(r"-?\d+(?:[.,]\d+)?", source_norm):
        try:
            if float(match.group(0).replace(",", ".")) == target:
                return True
        except ValueError:
            continue
    return False


class MetadataLLMService:
    """KI-first metadata extraction with a deterministic verbatim guard.

    The client is injectable (same pattern as EmbeddingService) so tests
    run against a fake and CI stays offline; at runtime the real Ollama
    client is used. extract() NEVER raises: it returns None when the LLM
    is unavailable or produced no verbatim-validated fields.
    """

    def __init__(self, client: Optional[OllamaMetadataClient] = None,
                 max_text_chars: int = 6000):
        self.client = client or OllamaMetadataClient()
        self.max_text_chars = max_text_chars

    def extract(self, text: str, file_name: str = "") -> Optional[Dict[str, Any]]:
        """Extract metadata from a file's text with the LLM (KI-first).

        Returns {'fields': {canonical: {'value', 'evidence'}},
                 'questions': [...], 'rejected': [field, ...]} or None
        (LLM unavailable / no valid fields). Never raises."""
        source_norm = _normalise(text)
        if not source_norm:
            return None
        prompt = _EXTRACTION_PROMPT.format(
            file_name=file_name or "unbenannt",
            text=text[: self.max_text_chars])
        try:
            raw = self.client.chat(prompt)
        except Exception as e:
            logger.info("LLM metadata extraction unavailable for %s: %s",
                        file_name, e)
            return None
        return self.validate(raw, source_norm, file_name)

    def validate(self, raw: Optional[str], source_norm: str,
                 file_name: str = "") -> Optional[Dict[str, Any]]:
        """Deterministic post-processing of the LLM answer (the guard).

        - only canonical fields survive (no invented namespaces)
        - every value must pass the verbatim check, else it is rejected
        - questions are passed through capped and sanitised
        """
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            logger.warning("LLM metadata answer was not JSON for %s: %.200s",
                           file_name, raw)
            return None
        if not isinstance(data, dict):
            return None

        fields: Dict[str, Dict[str, Any]] = {}
        rejected: List[str] = []
        raw_fields = data.get("fields")
        if isinstance(raw_fields, dict):
            for name, payload in raw_fields.items():
                canonical = _canonical_field_name(name)
                if canonical is None:
                    rejected.append(f"{name} (unbekanntes Feld)")
                    continue
                if not isinstance(payload, dict):
                    rejected.append(f"{canonical} (ungültige Struktur)")
                    continue
                value = payload.get("value")
                if value in (None, ""):
                    continue
                if not _verbatim(value, source_norm):
                    # HARD anti-hallucination rule: value not in the source
                    # text -> reject, never keep a possibly invented value.
                    rejected.append(
                        f"{canonical}='{value}' (nicht wortwörtlich im Text)")
                    logger.info(
                        "Rejected hallucinated metadata value for %s: "
                        "%s=%r (no verbatim evidence)", file_name, canonical,
                        value)
                    continue
                fields[canonical] = {
                    "value": str(value).strip(),
                    "evidence": str(payload.get("evidence") or "")[:300],
                }
        if not fields:
            return None

        questions: List[str] = []
        raw_questions = data.get("questions")
        if isinstance(raw_questions, list):
            for q in raw_questions:
                if isinstance(q, str) and q.strip() and len(q) <= 300:
                    questions.append(q.strip())
        return {
            "fields": fields,
            "questions": questions[:5],
            "rejected": rejected,
        }


def _canonical_field_name(name: str) -> Optional[str]:
    """Fold an LLM field name onto the canonical platform fields."""
    if not isinstance(name, str):
        return None
    key = re.sub(r"[\s\-]+", "_", name).strip("_").lower()
    aliases = {
        "operator": "operator_name", "messperson": "operator_name",
        "user": "operator_name", "benutzer": "operator_name",
        "instrument": "instrument_type", "geraet": "instrument_type",
        "spectrometer": "instrument_type", "spektrometer": "instrument_type",
        "sensor": "instrument_type", "device": "instrument_type",
        "measurement_date": "timestamp", "acquisition_time": "timestamp",
        "date": "timestamp", "datum": "timestamp", "uhrzeit": "timestamp",
        "zeit": "timestamp", "messzeitpunkt": "timestamp",
        "sample": "sample_id", "probe": "sample_id",
        "probenname": "sample_id", "sample_name": "sample_id",
        "humidity_pct": "humidity", "luftfeuchte": "humidity",
        "feuchte": "humidity", "raumtemperatur": "temperature",
        "integration_time_ms": "integration_time",
        "integrationszeit": "integration_time",
        "scans": "scan_count", "messungen": "scan_count",
        "aufloesung": "resolution", "wellenlaengenbereich": "wavelength_range",
        "seriennummer": "serial_number", "kommentar": "notes",
        "notizen": "notes", "comment": "notes", "ort": "location",
        "standort": "location",
    }
    if key in CANONICAL_FIELDS:
        return key
    return aliases.get(key)
