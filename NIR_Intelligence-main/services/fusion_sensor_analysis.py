"""OP68: Sensor-Analyse und -Vergleich fuer Fusionsprojekte.

Nutzeranforderungen (2026-10-19):
1. Beim Merge soll die Sensor-Analyse und der Vergleich aller Details
   Teil der Bewertung sein (Kanal-Ratios, Korrelationsstruktur, Rauschen,
   ADC-Saettigung, Ratio-Streuung zwischen Messobjekten).
2. Aus den 'brauchbaren' Kanaelen soll eine Gain-Kurve geschaetzt werden,
   um die Kalibration zu stuetzen - sensoragnostisch: verbindlich ist der
   PROTOKOLL-Vertrag (Dark-/White-Referenzmessung mit >= 50 Wiederholungen,
   als Metadaten deklariert), keine bestimmte Hardware.
3. Nur fuer Fusionsprojekte (PO-Entscheidung): Projekte ohne Fusion
   veraendern ihr Verhalten nicht.

Ehrlichkeitsregel (OP14/OP18): Ohne gemeinsame Messobjekte sind Sensor-Gain
und Probeneffekt konfundiert - die Gain-Kurve ist dann nicht schaetzbar,
und genau das wird gemeldet (konfounding_warning), statt eine Kurve zu
faken. White-Referenzmessungen (>= 50 Wiederholungen) heben die
Konfundierung auf: die Transferfunktion ist probenunabhaengig messbar.

Vertrag (sensoragnostisch, Grundregel 'alle Spektrometer'):
- Referenzmessungen werden ueber Metadaten deklariert:
  reference_type: 'dark' | 'white', n_repeats >= 50, ggf.
  reference_artifact (freies Textfeld, z. B. 'White-Kappe', 'Spectralon').
- Datensaetze mit dataset_type 'reference_measurement' fließen NIE in die
  Kalibration, sondern nur in die Sensor-Bewertung.
"""
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

MIN_REFERENCE_REPEATS = 50
REFERENCE_TYPES = ('dark', 'white')
GAIN_CURVE_DEGREE = 2          # quadratisch: minimale glatte Kurve
USABLE_RATIO_RANGE = (0.5, 2.0)  # Ratios ausserhalb: Ausreisser-Kanal


def reference_measurements(dataset: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Prueft, ob ein Datensatz eine deklarierte Referenzmessung ist.

    Sensoragnostischer Vertrag: erkannt wird die METADATEN-Deklaration
    (reference_type + n_repeats), kein Geraet, kein Format.
    """
    meta = dataset.get('metadata') or {}
    rtype = str(meta.get('reference_type', '')).lower().strip()
    if rtype not in REFERENCE_TYPES:
        return None
    try:
        n = int(meta.get('n_repeats') or 0)
    except (TypeError, ValueError):
        n = 0
    rows = dataset.get('calibration_samples') or []
    if not rows:
        rows = dataset.get('spectra') or []
    n_actual = len(rows) or n
    if n_actual < MIN_REFERENCE_REPEATS:
        return {
            'reference_type': rtype,
            'n_repeats': n_actual,
            'compliant': False,
            'reason': (f'Referenzmessung mit {n_actual} Wiederholungen '
                       f'deklariert - Mindestvertrag ist '
                       f'{MIN_REFERENCE_REPEATS} (Dark/White-Abgleich).'),
        }
    return {
        'reference_type': rtype,
        'n_repeats': n_actual,
        'compliant': True,
        'values': np.asarray(rows, dtype=float),
        'artifact': str(meta.get('reference_artifact', '') or ''),
    }


def _channels(datasets: List[Dict[str, Any]]) -> Optional[List[str]]:
    for d in datasets:
        for key in ('channel_names', 'wavelengths', 'channels'):
            names = d.get(key)
            if names:
                return [str(c) for c in names]
    return None


def sensor_comparison(datasets_a: List[Dict[str, Any]],
                      datasets_b: List[Dict[str, Any]],
                      channel_names: Optional[List[str]] = None,
                      ) -> Dict[str, Any]:
    """Vollstaendiger Sensor-Vergleich zweier Quellen (alle Details).

    Liefert Kanal-Mediane, Ratios, CV, Korrelationsstruktur-Differenz,
    Replikat-Rauschen je Quelle, Konfundierungs-Diagnose (Ratio-Streuung
    zwischen Messobjekten) und - falls White-Referenzen beider Quellen
    verfuegbar sind - die saubere Gain-Kurve aus den Referenzen.
    """
    result: Dict[str, Any] = {'performed': False}

    def _usable_rows(datasets):
        rows = []
        for d in datasets:
            if d.get('dataset_type') == 'reference_measurement':
                continue
            if not d.get('usable'):
                continue
            r = d.get('calibration_samples')
            if r:
                rows.extend(r)
        return np.asarray(rows, dtype=float) if rows else None

    Xa, Xb = _usable_rows(datasets_a), _usable_rows(datasets_b)
    if Xa is None or Xb is None or Xa.ndim != 2 or Xb.ndim != 2 \
            or Xa.shape[1] != Xb.shape[1] or Xa.shape[0] < 10 \
            or Xb.shape[0] < 10:
        result['reason'] = ('Zu wenige verwertbare Messdatensaetze fuer '
                            'den Sensor-Vergleich.')
        return result

    names = channel_names or _channels(datasets_a + datasets_b) \
        or [f'ch{i+1}' for i in range(Xa.shape[1])]
    med_a, med_b = np.median(Xa, axis=0), np.median(Xb, axis=0)
    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = np.where(np.abs(med_a) > 1e-9, med_b / med_a, np.nan)

    cv = lambda X, med: np.array([
        100.0 * X[:, j].std(ddof=1) / abs(med[j]) if abs(med[j]) > 1e-9
        else float('nan') for j in range(X.shape[1])])
    cv_a, cv_b = cv(Xa, med_a), cv(Xb, med_b)

    # Korrelationsstruktur (Sensor-Signatur)
    try:
        Ca, Cb = np.corrcoef(Xa.T), np.corrcoef(Xb.T)
        corr_diff = float(np.abs(Ca - Cb).mean())
        jmax = int(np.unravel_index(np.abs(Ca - Cb).argmax(),
                                    (len(names), len(names)))[0])
        corr = {'mean_abs_diff': corr_diff,
                'max_abs_diff': float(np.abs(Ca - Cb).max()),
                'max_channel': names[jmax] if jmax < len(names) else None}
    except Exception:
        corr = None

    # Konfundierungs-Diagnose: Ratio-Streuung zwischen Messobjekten
    def _group_ratios(X, groups_a, med_ref):
        ratios = []
        for g in sorted(set(groups_a)):
            mask = np.asarray([gg == g for gg in groups_a])
            if mask.sum() >= 3:
                med_g = np.median(X[mask], axis=0)
                with np.errstate(divide='ignore', invalid='ignore'):
                    ratios.append(np.where(np.abs(med_ref) > 1e-9,
                                           med_g / med_ref, np.nan))
        return np.asarray(ratios) if ratios else None

    confounded = None
    ga = _group_labels(datasets_a)
    gb = _group_labels(datasets_b)
    if ga and gb:
        ra = _group_ratios(Xa, ga, med_a)
        rb = _group_ratios(Xb, gb, med_a)
        if ra is not None and rb is not None:
            allr = np.vstack([ra, rb])
            iqr = np.percentile(allr, 75, axis=0) \
                - np.percentile(allr, 25, axis=0)
            j = int(np.nanargmax(iqr))
            confounded = {
                'max_iqr_channel': names[j] if j < len(names) else None,
                'max_iqr': float(iqr[j]),
                'median_iqr': float(np.nanmedian(iqr)),
                'interpretation': (
                    'Hohe Ratio-Streuung zwischen Messobjekten: Sensor-Gain '
                    'und Probenbestand sind konfundiert - eine Gain-Kurve '
                    'ist aus Messdaten allein nicht belastbar schaetzbar '
                    '(Anchor-/Referenzmessung noetig).'
                    if float(np.nanmedian(iqr)) > 0.5 else
                    'Ratio-Streuung zwischen Messobjekten gering - eine '
                    'Gain-Kurve ist potenziell aus Messdaten schaetzbar.'),
            }

    result.update({
        'performed': True,
        'n_channels': int(Xa.shape[1]),
        'channels': [
            {'name': names[j] if j < len(names) else f'ch{j+1}',
             'median_a': float(med_a[j]),
             'median_b': float(med_b[j]),
             'ratio_b_over_a': float(ratio[j])
             if np.isfinite(ratio[j]) else None,
             'cv_a_percent': float(cv_a[j]) if np.isfinite(cv_a[j]) else None,
             'cv_b_percent': float(cv_b[j]) if np.isfinite(cv_b[j]) else None,
             }
            for j in range(Xa.shape[1])],
        'correlation_structure': corr,
        'confounding': confounded,
        'n_significant_channels': _n_significant(Xa, Xb),
    })
    return result


def _group_labels(datasets: List[Dict[str, Any]]) -> List[str]:
    out = []
    for d in datasets:
        if d.get('dataset_type') == 'reference_measurement' \
                or not d.get('usable'):
            continue
        n = len(d.get('calibration_samples') or [])
        label = d.get('file_name', 'obj')
        out.extend([label] * n)
    return out


def _n_significant(Xa: np.ndarray, Xb: np.ndarray) -> Optional[int]:
    try:
        from scipy import stats
        sig = 0
        for j in range(Xa.shape[1]):
            try:
                p = stats.mannwhitneyu(Xa[:, j], Xb[:, j]).pvalue
                if p < 0.001:
                    sig += 1
            except ValueError:
                continue
        return sig
    except Exception:
        return None


def gain_curve_from_references(refs_a: List[Dict[str, Any]],
                                refs_b: List[Dict[str, Any]],
                                ) -> Dict[str, Any]:
    """Sensoragnostische Gain-Kurve aus Dark/White-Referenzen.

    Schaetzt die Transferfunktion B->A aus den WHITE-Referenzen
    (probenunabhaengig, mit Konfidenz aus den Wiederholungen) und
    dokumentiert Dark-Offsets beider Quellen. Wellenlaengen-geglattet
    (Polynom Grad GAIN_CURVE_DEGREE) ueber die Kanal-Indizes; sind echte
    Wellenlaengen verfuegbar, werden sie bevorzugt.
    """
    out: Dict[str, Any] = {'estimable': False}

    def _white(refs):
        for r in refs:
            if r and r.get('reference_type') == 'white' \
                    and r.get('compliant'):
                return r
        return None

    wa, wb = _white(refs_a), _white(refs_b)
    if wa is None or wb is None:
        missing = []
        if wa is None:
            missing.append('Quelle A')
        if wb is None:
            missing.append('Quelle B')
        out['reason'] = (
            'Keine vorschriftsmaessige White-Referenzmessung '
            f"(>= {MIN_REFERENCE_REPEATS} Wiederholungen) in: "
            + ', '.join(missing) + '. Ohne Referenz-Abgleich ist die '
            'Gain-Kurve nicht sensoragnostisch schaetzbar.')
        return out

    Va, Vb = np.asarray(wa['values'], float), np.asarray(wb['values'], float)
    if Va.ndim != 2 or Vb.ndim != 2 or Va.shape[1] != Vb.shape[1]:
        out['reason'] = 'Kanalzahl der Referenzen unterscheidet sich.'
        return out

    # Radiometrische Kalibrierung je Quelle: (raw - dark) / (white - dark)
    def _dark(refs):
        for r in refs:
            if r and r.get('reference_type') == 'dark' \
                    and r.get('compliant'):
                return r
        return None

    da, db = _dark(refs_a), _dark(refs_b)
    dark_a = np.mean(np.asarray(da['values'], float), axis=0) if da \
        else np.zeros(Va.shape[1])
    dark_b = np.mean(np.asarray(db['values'], float), axis=0) if db \
        else np.zeros(Vb.shape[1])
    white_a = np.median(Va - dark_a, axis=0)
    white_b = np.median(Vb - dark_b, axis=0)
    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = np.where(np.abs(white_a) > 1e-9, white_b / white_a, np.nan)
    usable = np.isfinite(ratio) & (ratio > USABLE_RATIO_RANGE[0]) \
        & (ratio < USABLE_RATIO_RANGE[1])
    if usable.sum() < max(2, (Va.shape[1] + 1) // 2):
        out['reason'] = ('Zu wenige belastbare Referenzkanäle '
                         '(White-Wert nahe 0 oder Ausreisser-Ratio).')
        return out

    x = np.arange(Va.shape[1], dtype=float)
    coef = np.polyfit(x[usable], np.log(ratio[usable]), GAIN_CURVE_DEGREE)
    curve = np.exp(np.polyval(coef, x))

    # Konfidenz aus den Wiederholungen (SD des Ratios je Kanal)
    with np.errstate(divide='ignore', invalid='ignore'):
        sd_ratio = np.where(np.abs(white_a) > 1e-9,
                            Vb.std(0, ddof=1) / np.abs(white_a), np.nan)
    out.update({
        'estimable': True,
        'method': ('White-Referenz-Ratio, Wellenlaengen-geglattet '
                   f'(Polynom Grad {GAIN_CURVE_DEGREE})'),
        'gain_curve': [float(v) for v in curve],
        'n_usable_channels': int(usable.sum()),
        'dark_a': [float(v) for v in dark_a],
        'dark_b': [float(v) for v in dark_b],
        'white_a': [float(v) for v in white_a],
        'white_b': [float(v) for v in white_b],
        'ratio_sd_median': float(np.nanmedian(sd_ratio)),
        'n_repeats_a': wa.get('n_repeats'),
        'n_repeats_b': wb.get('n_repeats'),
        'artifacts': {'a': wa.get('artifact', ''),
                      'b': wb.get('artifact', '')},
        'confidence_note': (
            f"Gain-Kurve aus {wa.get('n_repeats')}x{wb.get('n_repeats')} "
            'Referenzwiederholungen; mediane Ratio-Streuung (SD/Median) '
            f'{float(np.nanmedian(sd_ratio)):.3f}.'),
    })
    return out


def apply_gain_curve(samples: List[List[float]],
                     curve: List[float]) -> List[List[float]]:
    """Korrektur: Quelle B auf Quelle A skalieren (elementweise / curve)."""
    c = np.asarray(curve, dtype=float)
    X = np.asarray(samples, dtype=float)
    if X.ndim != 2 or c.shape[0] != X.shape[1]:
        raise ValueError('Gain-Kurve passt nicht zur Kanalzahl.')
    if np.any(~np.isfinite(c)) or np.any(c <= 0):
        raise ValueError('Gain-Kurve enthaelt ungueltige Werte.')
    return (X / c).tolist()
