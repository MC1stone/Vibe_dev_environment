"""KI-gestuetzter Struktur-Klaerungsdialog fuer Datendateien (Stufe B).

Wenn der format-agnostische Loader eine Datei nicht als Spektrum lesen
kann (usable=False), uebernimmt dieser Service den Zwischenschritt:

1. ANALYSE: Die Datei-Informanten (Spaltennamen, erste Zeilen, Trennzeichen-
   Statistik) werden aufbereitet und der KI (Mistral via Ollama) vorgelegt.
   Die KI schlaegt eine Struktur-Interpretation mit Konfidenz vor und/oder
   stellt Klaerungsfragen an den Nutzer (wie der Metadaten-Flow).
2. ANWENDUNG: Nutzer-Antworten (oder ein per Konfiguration besttigter
   KI-Vorschlag) werden als StructureHints an den Loader uebergeben; der
   Loader fuehrt die Datei mit diesen Hinweisen erneut aus.
3. LERNEN: Die bestaetigte Struktur wird als StructureProfile persistiert
   (Muster-Signatur: Spaltennamen-Sha), sodass der NAECHSTE Datensatz
   desselben Formats automatisch (mit KI-Vorschlag + Bestaetigung oder
   direkt, je Profil-Vertrauensstufe) laeuft - keine neue Version noetig.

Anti-Halluzination wie im Metadaten-Flow: KI-Aussagen ohne Beleg im
Dateitext werden verworfen; Konflikte werden als Fragen eskaliert.
"""

import hashlib
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Service.StructureDialog")

# ---------------------------------------------------------------------------
# Datei-Informanten (was der KI vorgelegt wird)
# ---------------------------------------------------------------------------


def file_fingerprints(file_path: str, max_rows: int = 8) -> Dict[str, Any]:
    """Kompakte, KI-taugliche Informanten einer Datendatei:
    Spaltennamen, Beispielzeilen, Trennzeichen-Haeufigkeit, Formate."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            head_lines = [f.readline() for _ in range(max_rows)]
    except Exception:
        return {"readable": False}

    non_empty = [l.rstrip("\n\r") for l in head_lines if l.strip()]
    if not non_empty:
        return {"readable": False, "empty": True}

    delim_stats = {d: 0 for d in [",", ";", "\t", "|"]}
    for line in non_empty:
        for d in delim_stats:
            delim_stats[d] += line.count(d)
    best_delim = max(delim_stats, key=delim_stats.get) if any(
        delim_stats.values()) else None

    header_guess = non_empty[0]
    columns = [c.strip() for c in header_guess.split(best_delim or ",")]

    return {
        "readable": True,
        "first_lines": non_empty[:5],
        "column_names": columns[:40],
        "delimiter": {"candidate": repr(best_delim) if best_delim else None,
                      "counts": {repr(k): v for k, v in delim_stats.items()}},
        "line_count_sampled": len(non_empty),
    }


def structure_signature(fingerprints: Dict[str, Any]) -> str:
    """Muster-Signatur fuer StructureProfile: Spaltennamen normalisiert
    (Kanal-/Wellenlangen-Suffixe bleiben erhalten), shorthash."""
    columns = fingerprints.get("column_names") or []
    norm = [re.sub(r"\d+\.\d+", "<num>", c.lower()) for c in columns]
    joined = "|".join(norm)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# KI-Dialog: Vorschlag + Klaerungsfragen
# ---------------------------------------------------------------------------

_STRUCTURE_PROMPT = """Du bist ein NIR-Spektroskopie-Datenexperte. Eine Datendatei konnte vom
automatischen Loader nicht als Spektrum gelesen werden. Analysiere die Informanten:

{fingerprints}

Aufgabe:
1. Schlage eine Struktur-Interpretation vor (JSON):
   - "layout": "xy" (zwei Spalten: Wellenlange, Intensitaet) | "wide" (eine Messung je Zeile, Kanaele als Spalten) | "unknown"
   - "wavelength_column": Spaltenname der Wellenlangenachse (bei xy) oder null
   - "intensity_column": Spaltenname der Intensitaet (bei xy) oder null
   - "channel_columns": Kanalespalten mit Wellenlange im Namen (bei wide) oder null
   - "sample_column": Spalte mit Proben-/Messungs-ID oder null
   - "reference_columns": Spalten mit Referenzwerten (z.B. Brix) oder null
   - "delimiter": Trennzeichen oder null
   - "header_row": true/false
   - "confidence": 0..1 (wie sicher du bist)
   - "evidence": kurzer Beleg aus den Informanten (Zitat)
2. Stelle bis zu 3 Klaerungsfragen an den Nutzer (Liste "questions"), wenn
   etwas unklar ist - jede Frage mit "field" (layout/wavelength_column/...).

Antworte NUR mit JSON: {{"proposal": {{...}}, "questions": [...]}}
Belege jede Aussage mit den sichtbaren Informanten - nichts erfinden."""


def ki_structure_proposal(file_path: str) -> Optional[Dict[str, Any]]:
    """KI-Analyse der Dateistruktur. Returns
    {'fingerprints', 'signature', 'proposal', 'questions'} oder None
    (KI nicht verfuegbar / unbrauchbar). Never raises."""
    try:
        from services.metadata_llm import OllamaMetadataClient
        if not OllamaMetadataClient().is_available():
            return None
        fingerprints = file_fingerprints(file_path)
        if not fingerprints.get("readable"):
            return None
        prompt = _STRUCTURE_PROMPT.format(
            fingerprints=json.dumps(fingerprints, ensure_ascii=False,
                                    indent=1))
        raw = OllamaMetadataClient().chat(prompt)
        if not raw:
            return None
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        parsed = json.loads(match.group(0))
        proposal = parsed.get("proposal") or {}
        questions = parsed.get("questions") or []
        # Anti-Halluzination: Evidence muss in den Informanten belegt sein
        evidence = str(proposal.get("evidence") or "")
        sample_text = " ".join(str(fingerprints.get("first_lines") or [])
                               + (fingerprints.get("column_names") or []))
        if evidence and evidence[:30] and evidence[:30] not in sample_text:
            # Beleg nicht in den Informanten -> nur Fragen weitergeben
            return {"fingerprints": fingerprints,
                    "signature": structure_signature(fingerprints),
                    "proposal": None,
                    "questions": questions or [
                        {"field": "layout",
                         "question": "Wie sind die Daten aufgebaut "
                                     "(zwei Spalten XY / Kanaele als Spalten)?"}],
                    "evidence_rejected": True}
        return {"fingerprints": fingerprints,
                "signature": structure_signature(fingerprints),
                "proposal": proposal,
                "questions": questions}
    except Exception:
        logger.exception("KI structure proposal failed")
        return None


# ---------------------------------------------------------------------------
# StructureHints (Anwendung auf den Loader)
# ---------------------------------------------------------------------------


def hints_from_answers(answers: Dict[str, Any]) -> Dict[str, Any]:
    """Nutzer-/KI-Antworten -> StructureHints fuer den Loader."""
    return {
        "layout": answers.get("layout"),
        "wavelength_column": answers.get("wavelength_column"),
        "intensity_column": answers.get("intensity_column"),
        "channel_columns": answers.get("channel_columns"),
        "sample_column": answers.get("sample_column"),
        "reference_columns": answers.get("reference_columns"),
        "delimiter": answers.get("delimiter"),
        "header_row": answers.get("header_row"),
    }


def apply_hints(loader, file_path: str, hints: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Datei mit StructureHints erneut laden. Der Loader erhaelt die
    Hinweise als context - die Auswertung geschieht ruckwirkungskompatibel:
    unbekannte Hinweise werden ignoriert, bekannte gelenkt den Parse."""
    try:
        import pandas as pd
        delimiter = hints.get("delimiter")
        header_row = hints.get("header_row")
        df = None
        if delimiter and delimiter in (",", ";", "\t", "|"):
            has_header = True if header_row is None else bool(header_row)
            df = pd.read_csv(file_path, sep=delimiter,
                             header=0 if has_header else None,
                             engine="python", encoding="utf-8")
        if df is None:
            return None
        layout = hints.get("layout")
        if layout == "wide":
            channel_map = {}
            for col in (hints.get("channel_columns") or []):
                m = re.search(r"(\d{3,4}(?:\.\d+)?)\s*(?:nm)?\s*$",
                              str(col).strip())
                if m:
                    channel_map[str(col)] = float(m.group(1))
            if not channel_map:
                for col in df.columns:
                    m = re.search(r"(\d{3,4}(?:\.\d+)?)\s*(?:nm)?\s*$",
                                  str(col).strip())
                    if m:
                        channel_map[str(col)] = float(m.group(1))
            if channel_map:
                expanded = loader._load_wide_format_spectra(
                    file_path, df, channel_map)
                if expanded is not None:
                    meta = dict(expanded.get('metadata') or {})
                    meta['structure_dialog'] = True
                    meta['hints_applied'] = hints
                    expanded['metadata'] = meta
                return expanded
            return None
        if layout == "xy":
            wl = hints.get("wavelength_column")
            it = hints.get("intensity_column")
            if wl in df.columns and it in df.columns:
                out = df[[wl, it]].copy()
                out.columns = ["wavelength", "intensity"]
                for col in (wl, it):
                    out[col if col in out.columns else "wavelength"] = \
                        pd.to_numeric(
                            out[col if col in out.columns else "wavelength"],
                            errors="coerce")
                return {
                    "data": out,
                    "source_file": file_path,
                    "format": os.path.splitext(file_path)[1].lower(),
                    "wavelength_column": "wavelength",
                    "intensity_column": "intensity",
                    "metadata": {"structure_dialog": True,
                                 "hints_applied": hints},
                }
        return None
    except Exception:
        logger.exception("apply_hints failed")
        return None
