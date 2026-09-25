# NIR Intelligence Platform - outlier analysis service (OP37)
# Deterministic, robust outlier detection across all measurements of a
# dataset. The KI-first principle applies to the REPORTING of the findings,
# not to guesswork: the detection itself is pure statistics (SNV
# normalisation + robust MAD distance to the median spectrum), nothing is
# invented, too few measurements produce an honest "not assessable" verdict.
from typing import Any, Dict, List, Optional

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

import base64
import io

MAD_THRESHOLD = 3.5
MIN_MEASUREMENTS = 5


def _figure_to_data_url(fig) -> str:
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=110, bbox_inches='tight')
    matplotlib.pyplot.close(fig)
    return 'data:image/png;base64,' + base64.b64encode(
        buffer.getvalue()).decode('ascii')


def _snv(matrix):
    """Standard Normal Variate: row-wise mean-centring and unit-variance
    scaling - removes multiplicative/additive scatter so distance-based
    outlier detection sees spectral SHAPE differences, not intensity
    offsets."""
    mean = matrix.mean(axis=1, keepdims=True)
    std = matrix.std(axis=1, ddof=1, keepdims=True)
    std = np.where(std < 1e-12, 1.0, std)
    return (matrix - mean) / std


def detect_outliers(measurement_samples: List[List[float]],
                    wavelengths: Optional[List[float]] = None,
                    threshold: float = MAD_THRESHOLD) -> Dict[str, Any]:
    """Robust outlier detection over the measurement replicas.

    Every measurement is SNV-normalised and compared to the median
    spectrum via the median absolute deviation (MAD) of all distances
    (robust z-score). A measurement is an outlier when its robust
    z-score exceeds the threshold (default 3.5, the standard Iglewicz-
    Hoaglin cutoff). Returns an honest verdict structure - never raises.
    """
    verdict = {
        'assessable': False,
        'measurement_count': len(measurement_samples or []),
        'outlier_indices': [],
        'robust_z_scores': [],
        'distances': [],
        'threshold': threshold,
        'reason': '',
    }
    if not NUMPY_AVAILABLE:
        verdict['reason'] = 'numpy nicht verf\u00fcgbar'
        return verdict
    try:
        matrix = np.asarray(measurement_samples, dtype=float)
    except Exception:
        verdict['reason'] = 'Messwerte nicht als Zahlen interpretierbar'
        return verdict
    if matrix.ndim != 2 or matrix.shape[0] < MIN_MEASUREMENTS:
        verdict['reason'] = (
            f'zu wenige Messungen ({matrix.shape[0] if matrix.ndim == 2 else 0} '
            f'< {MIN_MEASUREMENTS}) - keine belastbare Ausreisseranalyse')
        return verdict
    normalized = _snv(matrix)
    median_spectrum = np.median(normalized, axis=0)
    distances = np.sqrt(((normalized - median_spectrum) ** 2).sum(axis=1))
    mad = np.median(np.abs(distances - np.median(distances)))
    if mad < 1e-9:
        # all distances (nearly) identical -> no spread to detect outliers in
        verdict.update({
            'assessable': True,
            'distances': distances.tolist(),
            'robust_z_scores': [0.0] * int(matrix.shape[0]),
            'outlier_indices': [],
            'reason': 'alle Messungen liegen (nahezu) identisch - '
                      'keine Ausreisser',
        })
        return verdict
    z_scores = 0.6745 * (distances - np.median(distances)) / mad
    outliers = [int(i) for i in np.where(np.abs(z_scores) > threshold)[0]]
    verdict.update({
        'assessable': True,
        'distances': distances.tolist(),
        'robust_z_scores': z_scores.tolist(),
        'outlier_indices': outliers,
        'reason': '',
    })
    return verdict


def outlier_charts(measurement_samples: List[List[float]],
                   wavelengths: Optional[List[float]],
                   verdict: Dict[str, Any],
                   file_name: str = 'Datensatz') -> Dict[str, str]:
    """Render the two documentation plots for the outlier findings.

    distance_plot: robust z-score per measurement with the threshold
    band; outlier points highlighted red. spectrum_overlay: all spectra
    in light grey, the median bold, outliers red - so the user SEES what
    deviates. Returns {'': ''} when matplotlib is missing or the verdict
    is not assessable. Never raises.
    """
    charts: Dict[str, str] = {}
    if not MATPLOTLIB_AVAILABLE or not verdict.get('assessable'):
        return charts
    try:
        matrix = np.asarray(measurement_samples, dtype=float)
        z = np.asarray(verdict.get('robust_z_scores') or [], dtype=float)
        outliers = set(verdict.get('outlier_indices') or [])
        threshold = float(verdict.get('threshold') or MAD_THRESHOLD)
        wl = (np.asarray(wavelengths, dtype=float)
              if wavelengths and len(wavelengths) == matrix.shape[1]
              else np.arange(matrix.shape[1], dtype=float))

        # --- distance plot ------------------------------------------
        fig, ax = plt.subplots(figsize=(7.5, 4.2))
        indices = np.arange(matrix.shape[0])
        inliers = [i for i in indices if i not in outliers]
        ax.bar(indices[inliers], np.abs(z[inliers]), color='#0d6efd',
               alpha=0.75, label='Messung (ok)')
        if outliers:
            ax.bar(sorted(outliers), np.abs(z[list(outliers)]),
                   color='#d62728', label='Ausreisser')
        ax.axhline(threshold, color='#d62728', ls='--', lw=1,
                   label=f'Schwelle (|z| = {threshold})')
        ax.set_xlabel('Messungs-Index')
        ax.set_ylabel('Robuster z-Score (Abstand zum Median-Spektrum)')
        ax.set_title(f'Ausreisser-Abst\u00e4nde: {_short(file_name)}')
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        charts['outlier_distance'] = _figure_to_data_url(fig)

        # --- spectrum overlay ---------------------------------------
        fig, ax = plt.subplots(figsize=(8, 4.2))
        for i in inliers:
            ax.plot(wl, matrix[i], color='grey', alpha=0.35, lw=0.8)
        if inliers:
            ax.plot(wl, np.median(matrix[inliers], axis=0), color='#0d6efd',
                    lw=2.2, label='Median (ok)')
        for i in sorted(outliers):
            ax.plot(wl, matrix[i], color='#d62728', lw=1.4,
                    label=f'Ausreisser (Messung {i + 1})')
        ax.set_xlabel('Wellenl\u00e4nge (nm)')
        ax.set_ylabel('Intensit\u00e4t')
        ax.set_title(f'Spektren mit markierten Ausreissern: {_short(file_name)}')
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        charts['outlier_overlay'] = _figure_to_data_url(fig)
    except Exception:
        charts = {}
    return charts


def _short(name: str, limit: int = 40) -> str:
    name = str(name or 'Datensatz')
    return name if len(name) <= limit else name[:limit - 1] + '\u2026'


def outlier_findings_text(verdict: Dict[str, Any],
                          file_name: str = 'Datensatz') -> List[str]:
    """German plain sentences documenting the outlier findings - used by
    the report section, the discussion and the chatbot knowledge base.
    Honest wording, no invention: numbers come straight from the verdict.
    """
    if not verdict.get('assessable'):
        return [f'F\u00fcr {_short(file_name)} konnte keine Ausreisseranalyse '
                f'durchgef\u00fchrt werden: {verdict.get("reason", "unbekannter Grund")}.']
    outliers = verdict.get('outlier_indices') or []
    count = verdict.get('measurement_count') or 0
    threshold = verdict.get('threshold')
    if not outliers:
        return [f'F\u00fcr {_short(file_name)} wurden {count} Messungen auf '
                f'Ausreisser gepr\u00fcft (robuster z-Score gegen\u00fcber dem '
                f'Median-Spektrum, Schwelle |z| = {threshold}): Es wurden keine '
                f'Ausreisser gefunden - alle Messungen liegen im erwarteten '
                f'Streuband.']
    listed = ', '.join(f'Messung {i + 1}' for i in outliers[:8])
    if len(outliers) > 8:
        listed += f' und {len(outliers) - 8} weitere'
    pct = 100.0 * len(outliers) / count if count else 0.0
    return [f'F\u00fcr {_short(file_name)} wurden {count} Messungen auf '
            f'Ausreisser gepr\u00fcft (robuster z-Score gegen\u00fcber dem '
            f'Median-Spektrum, Schwelle |z| = {threshold}): '
            f'{len(outliers)} Ausreisser ({pct:.0f} %) gefunden - {listed}. '
            f'Diese Messungen weichen im SNV-normalisierten Spektrum deutlich '
            f'vom Median ab und sollten vor einer Kalibration gepr\u00fcft '
            f'werden (Messwiederholung oder Ausschluss nach Ursachenkl\u00e4rung).']


def analyse_dataset(dataset: Dict[str, Any]) -> Dict[str, Any]:
    """Run the outlier analysis for one dataset entry (from the
    preparation report) and attach verdict + charts + findings text.
    Returns a section dict for the crew report. Never raises."""
    file_name = str(dataset.get('file_name') or 'Datensatz')
    samples = dataset.get('measurement_samples') or []
    wavelengths = (dataset.get('preview') or {}).get('wavelengths') or \
        dataset.get('wavelengths') or []
    verdict = detect_outliers(samples, wavelengths)
    charts = outlier_charts(samples, wavelengths, verdict, file_name)
    findings = outlier_findings_text(verdict, file_name)
    return {
        'file_name': file_name,
        'verdict': verdict,
        'charts': charts,
        'findings': findings,
    }
