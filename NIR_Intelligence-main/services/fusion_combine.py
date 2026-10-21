"""OP80: Kombinierter Fusions-Datensatz + Wellenlaengen-Harmonisierung.

Nutzer-Anforderung (2026-10-21): 'Bei einem Merge sollen die Datensaetze
gemergt werden und damit bekomme ich im Grunde nur noch EINE Auswertung.
Interessant waere, ob bekannte Unterschiede wie ein anderer Sensor
statistisch Signifikanzen erzeugen. Was, wenn wir unterschiedliche
Wellenlaengen-Daten haben und mit der Kurve selbst arbeiten muessen?'

Dieser Dienst baut aus den Quell-Datensaetzen eines Fusionsprojekts
EINEN kombinierten Datensatz:
- identisches Wellenlaengen-Raster -> Zeilen einfach stapeln
- unterschiedliches Raster -> Interpolation der Intensitaeten auf ein
  gemeinsames Raster (Schnittmenge der Bereiche, feinstes gemeinsames
  Sampling) - ehrlich dokumentiert im resultierenden 'fusion_merge'
  Berichtsteil (was interpoliert wurde, wie viele Punkte, welche
  Bereiche entfielen).
- je Zeile wird die Herkunft (Quell-Datei) als group_label mitgefuehrt,
  damit der Statistik-Agent Gruppenunterschiede (z. B. Sensor A vs. B)
  signifikanztesten kann.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def _grid_of(dataset: Dict[str, Any]) -> Optional[List[float]]:
    wl = (dataset.get('preview') or {}).get('wavelengths') or []
    return [float(w) for w in wl] if wl else None


def _rasters_equal(a: List[float], b: List[float],
                   tol: float = 1e-6) -> bool:
    if len(a) != len(b):
        return False
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def _common_grid(grids: List[List[float]]) -> Tuple[List[float], Dict]:
    """Gemeinsames Raster: Schnittmenge der Bereiche, feinste Schritt-
    weite, deterministisch erzeugt (kein Hauptfehler-Raster bevorzugt)."""
    lo = max(min(g) for g in grids)
    hi = min(max(g) for g in grids)
    step = min(min(np.diff(sorted(set(g)))) if len(set(g)) > 1 else 1.0
               for g in grids)
    step = max(float(step), 0.5)
    n = int(np.floor((hi - lo) / step)) + 1
    grid = [round(lo + i * step, 4) for i in range(n)]
    return grid, {'range_low': lo, 'range_high': hi, 'step': step}


def _interp_rows(rows: List[List[float]], src_grid: List[float],
                 dst_grid: List[float]) -> List[List[float]]:
    src = np.asarray(src_grid, dtype=float)
    out = []
    for row in rows:
        r = np.asarray(row, dtype=float)
        if len(r) != len(src):
            continue
        out.append([float(v) for v in np.interp(dst_grid, src, r)])
    return out


def build_combined_dataset(datasets: List[Dict[str, Any]],
                            parsed_wishes: Optional[List[Dict[str, Any]]] = None,
                            unparsed_wishes: Optional[List[str]] = None,
                            file_names: Optional[Dict[str, str]] = None,
                            ) -> Optional[Dict[str, Any]]:
    """file_names: optionale Map file_id -> Original-Dateiname (Upload),
    damit die Review-Karte lesbare Quellnamen zeigt statt UUIDs."""
    """Baut EINEN kombinierten Datensatz aus den Quell-Datensaetzen.

    Voraussetzung: alle Datensaetze verwertbar mit calibration_samples
    und reference_values (gleiche Spaltenzahl = gleiche Kanaele oder
    harmonisierbar via preview-Raster). Liefert None, wenn nichts
    kombinierbar ist (Aufrufer faellt auf Einzel-Auswertung zurueck).
    """
    usable = [d for d in datasets if d.get('usable')
              and d.get('calibration_samples') and d.get('reference_values')
              and _grid_of(d)]
    if len(usable) < 2:
        return None
    grids = [_grid_of(d) for d in usable]
    all_equal = all(_rasters_equal(grids[0], g) for g in grids[1:])

    merge_report: Dict[str, Any] = {
        'kind': 'combined_fusion_dataset',
        'n_sources': len(usable),
        'rasters_equal': all_equal,
        'sources': [],
    }
    samples: List[List[float]] = []
    targets: List[float] = []
    group_labels: List[str] = []
    group_files: List[str] = []
    target_name = None
    n_interp_rows = 0
    combined: List[List[float]] = []
    combined_grid = grids[0]
    if not all_equal:
        combined_grid, info = _common_grid(grids)
        merge_report['harmonization'] = {
            'method': 'linear_interpolation',
            **info,
            'excluded_ranges': [
                {'file': _src_name(d),
                 'below': round(min(g), 2),
                 'above': round(max(g), 2)}
                for d, g in zip(usable, grids)
                if min(g) > min(combined_grid) or max(g) < max(combined_grid)],
        }
    else:
        merge_report['harmonization'] = None

    names = dict(file_names or {})

    def _src_name(d: Dict[str, Any]) -> str:
        name = str(d.get('file_name') or '').strip()
        if not name:
            name = str((d.get('metadata') or {}).get('file_name')
                       or '').strip()
        if not name:
            name = names.get(str(d.get('file_id') or ''), '').strip()
        if not name:
            name = str(d.get('file_id') or 'Quelle')
        return name

    for d, g in zip(usable, grids):
        rows = d.get('calibration_samples') or []
        if not all_equal:
            rows = _interp_rows(rows, g, combined_grid)
            n_interp_rows += len(rows)
        elif len(rows[0]) != len(combined_grid):
            # gleiche Werte, andere Kanalzahl - nicht kombinierbar
            merge_report['sources'].append({
                'file': _src_name(d), 'status': 'skipped',
                'reason': 'Kanalzahl weicht ab'})
            continue
        tvals = [float(v) for v in (d.get('reference_values') or [])]
        if len(rows) != len(tvals):
            merge_report['sources'].append({
                'file': _src_name(d), 'status': 'skipped',
                'reason': 'Zeilen-/Zielwert-Differenz'})
            continue
        samples.extend(rows)
        targets.extend(tvals)
        src_name = _src_name(d)
        group_labels.extend([src_name] * len(rows))
        group_files.append(src_name)
        target_name = target_name or d.get('target_name')
        merge_report['sources'].append({
            'file': _src_name(d), 'status': 'merged',
            'n_rows': len(rows)})
    if not all_equal:
        merge_report['harmonization']['n_interpolated_rows'] = n_interp_rows
    if not samples:
        return None

    combined.append({
        'file_name': 'Fusion kombiniert ('
                     + ' + '.join(group_files) + ')',
        'file_id': 'fusion_combined',
        'usable': True,
        'target_name': target_name,
        'calibration_samples': samples,
        'reference_values': targets,
        'preview': {'wavelengths': list(combined_grid),
                    'intensities': []},
        'metadata': {
            'sample_id': 'Fusion kombiniert',
            'fusion_merged': True,
            'group_labels': group_labels,
            'source_files': group_files,
            'n_sources': len(group_files),
        },
        'measurement_samples': samples,
        'derived_classes': None,
        'fusion_merge': merge_report,
    })
    # OP77: Klassen-Wuensche wirken auf den KOMBINIERTEN Zielwerten -
    # die Zusatz-Klassifikation laeuft auf den gemergten Daten (eine
    # Auswertung), Klassen aus der gemeinsamen Verteilung.
    combined_ds = combined[0]
    if parsed_wishes:
        try:
            from services.analysis_wishes import apply_wishes_to_dataset
            combined_ds['metadata']['target_name'] = target_name or 'Zielwert'
            applied = apply_wishes_to_dataset(combined_ds, parsed_wishes)
            if applied:
                merge_report['wishes_applied'] = applied
        except Exception:
            logger.exception('wishes on combined dataset failed '
                             '(non-fatal)')
    # Unparsed-Wuensche ehrlich als offene Fragen an den kombinierten
    # Datensatz (gleiche Sprache wie OP77).
    if unparsed_wishes:
        questions = combined_ds.setdefault('open_questions', [])
        for w in unparsed_wishes:
            questions.append(
                f"Analyse-Wunsch erkannt, aber noch nicht unterstuetzt: "
                f"'{w}'. Beschreiben Sie ihn im Metadaten-Editor oder als "
                "Kommentar - die Plattform lernt dazu.")
    return combined_ds


def sensor_significance_hint(combined: Dict[str, Any]) -> Optional[str]:
    """Ehrlicher Hinweis fuer den Bericht, wenn die Quellen sich in
    bekannten Metadaten (z. B. Sensor) unterscheiden - der Statistik-
    Agent kann dann Gruppenunterschiede signifikanztesten (Levene/
    Welch, OP68-Vertrag)."""
    groups = (combined.get('metadata') or {}).get('group_labels') or []
    if len(set(groups)) < 2:
        return None
    return ('Kombinierter Fusions-Datensatz aus '
            + str(len(set(groups))) + ' Quellen. Gruppenunterschiede '
            '(z. B. Sensor, Geraet, Bedingung) koennen '
            'signifikanzgetestet werden: Sensor-Vergleich + '
            'Korrelationsstruktur wie im OP68-Vertrag.')
