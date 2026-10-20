"""OP77: Analyse-Wuensche beim Upload - generisch, nicht hardcodiert.

Nutzer-Anforderung (2026-10-20): 'Beim Hochladen die Moeglichkeit, z. B.
zu sagen: erstelle die Auswertung und bilde dazu 5 Reifeklassen der
Tomaten' - und (Korrektur desselben Nutzers): 'Der Nutzer koennte auch
andere Wuensche eingeben - keine Hardcodierung der Loesung, nur die
Funktion!'

Design:
- Der Nutzer gibt beim Upload FREIEN TEXT ein (Analyse-Wuensche), z. B.
  '5 Reifeklassen der Tomaten bilden' oder '3 Feuchtegruppen'.
- parse_wishes() uebersetzt den Text in strukturierte Wuensche. Derzeit
  bekannter Wunsch-Typ: KLASSENBILDUNG (N Klassen aus dem erkannten
  Messziel - egal ob Brix, Feuchte, Protein: 'Reife' ist nur ein
  Beispiel-Wort, die Funktion ist zielagnostisch).
- NEUE Wunsch-Typen sind als Erweiterungspunkt vorgesehen:
  _WISH_PARSERS-Registry - ein neuer Parser + Handler genuegt, keine
  Pipeline-Aenderung noetig.
- Nicht verstandene Wuensche werden NICHT still ignoriert: sie werden
  als offene KI-Frage im Bericht sichtbar ('Wunsch erkannt, aber noch
  nicht unterstuetzt: ...').
"""
import logging
import re
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("Service.AnalysisWishes")

# Zahlwoerter fuer formulierungen wie 'fuenf Klassen'
_NUMBER_WORDS = {
    'zwei': 2, 'drei': 3, 'vier': 4, 'fuenf': 5, 'sechs': 6,
    'sieben': 7, 'acht': 8, 'neun': 9, 'zehn': 10, 'elf': 11,
    'zwoelf': 12,
}

_CLASS_NOUN_RE = re.compile(
    r'(?:klassen|gruppe[n]?|stufen|kategorien|segmente)', re.IGNORECASE)
_NUMBER_RE = re.compile(r'(\d{1,2})')


def parse_wishes(text: str) -> Dict[str, Any]:
    """Uebersetzt freien Text in strukturierte Analyse-Wuensche.

    Liefert {'wishes': [{'type': 'classes', 'n': N, 'name': ...}],
    'unparsed': [ ... ]} - unknown wishes ehrlich zurueckgemeldet.
    """
    wishes: List[Dict[str, Any]] = []
    unparsed: List[str] = []
    if not text or not str(text).strip():
        return {'wishes': wishes, 'unparsed': unparsed}
    # Satzweise zerlegen - mehrere Wuensche in einem Text moeglich
    for chunk in re.split(r'[.;\n]|und\b', str(text)):
        chunk = chunk.strip()
        if len(chunk) < 4:
            continue
        # Wunsch-Typ KLASSENBILDUNG: '<Zahl> <Klassen-Nomen>'
        if _CLASS_NOUN_RE.search(chunk):
            m = _NUMBER_RE.search(chunk)
            n = None
            if m:
                n = int(m.group(1))
            else:
                low = chunk.lower()
                for word, val in _NUMBER_WORDS.items():
                    if re.search(rf'\b{word}\b', low):
                        n = val
                        break
            if n is not None and 2 <= n <= 12:
                wishes.append({'type': 'classes', 'n': n,
                               'name': chunk[:120]})
                continue
            unparsed.append(chunk[:160])
            continue
        # Alles andere: ehrlich melden (kein stills Ignorieren)
        unparsed.append(chunk[:160])
    return {'wishes': wishes, 'unparsed': unparsed}


def build_target_classes(reference_values: List[float],
                         n_classes: int = 5,
                         target_name: str = 'Zielwert',
                         ) -> Dict[str, Any]:
    """Bildet N equal-frequency Klassen aus den Referenzwerten
    (zielagnostisch: Brix, Feuchte, Protein ...). Ehrlich leer bei
    zu duenner Datenlage - nie erfunden."""
    try:
        y = np.asarray([float(v) for v in reference_values], dtype=float)
        finite = y[np.isfinite(y)]
        if finite.size < max(10, 2 * int(n_classes)):
            return {}
        if np.unique(finite).size < 2:
            return {}
        n = max(2, int(n_classes))
        qs = np.quantile(finite, np.linspace(0, 1, n + 1))
        edges = list(dict.fromkeys(np.round(qs, 6).tolist()))
        labels = []
        for i in range(len(edges) - 1):
            lo, hi = edges[i], edges[i + 1]
            labels.append(f'K{i + 1} ({lo:.2f}-{hi:.2f} {target_name})')
        if len(labels) < 2:
            return {}
        assignment = []
        for v in y:
            if not np.isfinite(v):
                assignment.append(None)
                continue
            idx = int(np.searchsorted(edges, v, side='right') - 1)
            idx = min(max(idx, 0), len(labels) - 1)
            assignment.append(labels[idx])
        return {
            'labels': labels,
            'assignment': assignment,
            'edges': [float(e) for e in edges],
            'target_name': target_name,
            'n_classes': len(labels),
        }
    except Exception:
        logger.exception('target class build failed (non-fatal)')
        return {}


def apply_wishes_to_dataset(dataset: Dict[str, Any],
                            wishes: List[Dict[str, Any]]) -> List[str]:
    """Fuehrt strukturierte Wuensche an EINEM Datensatz aus.

    Klassen-Wuensche: N Klassen aus dem erkannten Messziel, zeilen-
    synchron als classification_samples/labels fuer die zusaetzliche
    Klassifikations-Analyse. Rueckgabe: Liste der angewandten Wuensche
    (fuer das Protokoll). Nicht ausfuehrbare Wuensche landeten bereits
    als offene Fragen beim Aufrufer (parse_wishes.unparsed).
    """
    applied: List[str] = []
    samples = dataset.get('calibration_samples') or []
    refs = dataset.get('reference_values') or []
    if not samples or len(samples) != len(refs):
        return applied
    target = (dataset.get('metadata') or {}).get('target_name') \
        or 'Zielwert'
    for wish in wishes:
        if wish.get('type') != 'classes':
            continue
        cls = build_target_classes(refs, n_classes=int(wish.get('n', 5)),
                                    target_name=str(target))
        if not cls:
            continue
        labels = cls['assignment']
        valid = [(s, l) for s, l in zip(samples, labels)
                 if l is not None]
        if len(valid) < 10:
            continue
        dist: Dict[str, int] = {}
        for _, l in valid:
            dist[l] = dist.get(l, 0) + 1
        dataset['derived_classes'] = {
            'wish': wish.get('name', ''),
            'n_classes': cls['n_classes'],
            'labels': cls['labels'],
            'edges': cls['edges'],
            'target_name': cls['target_name'],
            'distribution': dist,
        }
        dataset['classification_samples'] = [s for s, _ in valid]
        dataset['classification_labels'] = [l for _, l in valid]
        dataset['class_labels'] = cls['labels']
        applied.append(f"{wish.get('n')}-Klassen aus '{target}' "
                        f"({wish.get('name', '')[:60]})")
    return applied
