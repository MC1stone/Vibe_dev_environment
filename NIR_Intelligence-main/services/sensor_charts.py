# NIR Intelligence Platform - sensor quality dashboard (OP21)
# A 4-panel SPC-style dashboard for the sensor quality section, rendered
# from the real measurement replicas and the sensor agent results:
#
#   Panel A : Shewhart control chart of the per-measurement deviation
#             from the reference (drift trend) with a +/-3 sigma band
#   Panel B : spectral overlay of all replica curves (visual drift as a
#             systematic shift)
#   Panel C : per-channel noise (box plot of the replica deviations per
#             channel - which of the channels drive the noise?)
#   Panel D : quality gauge 0-1 with traffic-light zones and the
#             sub-scores (drift, offset, noise)
#
# Plus concrete German optimization recommendations derived from the
# sensor agent results. Everything degrades gracefully: no matplotlib,
# no replicas or no sensor results -> empty dict, report intact.
# Base64 PNG data URLs, same contract as the other chart builders.
import base64
import io
import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("Service.SensorCharts")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


def _figure_to_data_url(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _as_matrix(samples) -> Optional[np.ndarray]:
    if not samples:
        return None
    matrix = np.asarray(samples, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] < 2 or matrix.shape[1] < 2:
        return None
    if not np.all(np.isfinite(matrix)):
        matrix = matrix[np.all(np.isfinite(matrix), axis=1)]
    if matrix.shape[0] < 2:
        return None
    return matrix


def _panel_control_chart(ax, matrix: np.ndarray) -> None:
    reference = matrix.mean(axis=0)
    scale = abs(float(matrix.mean())) or 1.0
    dev = np.abs(matrix - reference).mean(axis=1) / scale
    x = np.arange(1, matrix.shape[0] + 1)
    center = float(dev.mean())
    sigma = float(dev.std(ddof=1)) if matrix.shape[0] > 1 else 0.0
    ucl = center + 3.0 * sigma
    ax.axhspan(center - 3.0 * sigma, center + 3.0 * sigma,
               color="#198754", alpha=0.10, label="\u00b13\u03c3-Band")
    ax.axhline(center, color="#0d6efd", lw=1, label="Mittelwert (CL)")
    ax.axhline(ucl, color="#d62728", ls="--", lw=1, label="UCL (+3\u03c3)")
    if center - 3.0 * sigma >= 0:
        ax.axhline(center - 3.0 * sigma, color="#d62728", ls="--", lw=1)
    ax.plot(x, dev, "o-", color="k", ms=4, lw=1, label="Abweichung/Messung")
    ax.set_xlabel("Messung (Replikat)")
    ax.set_ylabel("Relative Abweichung vom Referenzspektrum")
    ax.set_title("A: Kontrollkarte (Shewhart) - Drift-Trend")
    ax.set_xticks(x[:: max(1, len(x) // 10)])
    ax.legend(fontsize=7, loc="upper left")
    ax.grid(alpha=0.3)


def _panel_overlay(ax, matrix: np.ndarray, wl: np.ndarray) -> None:
    cmap = plt.get_cmap("viridis")
    for i in range(matrix.shape[0]):
        color = cmap(i / max(1, matrix.shape[0] - 1))
        ax.plot(wl, matrix[i], lw=0.8, alpha=0.75, color=color)
    ax.set_xlabel("Wellenl\u00e4nge (nm)")
    ax.set_ylabel("Intensit\u00e4t")
    ax.set_title(f"B: Spektral-Overlay ({matrix.shape[0]} Kurven)")
    ax.grid(alpha=0.3)


def _panel_channel_noise(ax, matrix: np.ndarray, wl: np.ndarray) -> None:
    reference = matrix.mean(axis=0)
    scale = abs(float(matrix.mean())) or 1.0
    residuals = (matrix - reference) / scale
    labels = [f"{w:.0f}" for w in wl]
    try:
        ax.boxplot([residuals[:, j] for j in range(matrix.shape[1])],
                   tick_labels=labels, showfliers=True,
                   flierprops=dict(ms=2, marker="o", alpha=0.5))
    except TypeError:
        ax.boxplot([residuals[:, j] for j in range(matrix.shape[1])],
                   labels=labels, showfliers=True,
                   flierprops=dict(ms=2, marker="o", alpha=0.5))
    ax.set_xlabel("Wellenl\u00e4nge (nm)")
    ax.set_ylabel("Relative Abweichung")
    ax.set_title("C: Rauschen pro Kanal (Replikat-Streuung)")
    ax.tick_params(axis="x", rotation=60, labelsize=7)
    ax.grid(alpha=0.3, axis="y")


def _panel_gauge(ax, sensor_results: Dict[str, Any]) -> None:
    score = float(sensor_results.get("overall_quality_score", 0.0) or 0.0)
    score = min(1.0, max(0.0, score))
    zones = [0.0, 0.6, 0.8, 1.0]
    colors = ["#dc3545", "#ffc107", "#198754"]
    for lo, hi, color in zip(zones[:-1], zones[1:], colors):
        ax.barh([0.6], [hi - lo], left=[lo], height=0.55,
                color=color, alpha=0.30, edgecolor="none")
    ax.barh([0.6], [score], height=0.3, color="#212529")
    ax.text(score - 0.02, 0.6, f"{score:.2f}", ha="right", va="center",
            color="white", fontsize=11, fontweight="bold")
    grade = "gut" if score >= 0.8 else ("akzeptabel" if score >= 0.6 else "kritisch")
    ax.text(0.5, 0.15, f"Sensorqualit\u00e4t: {grade}",
            ha="center", va="center", fontsize=10, transform=ax.transAxes)

    sub_scores = [
        ("Drift", 1.0 - min(1.0, float(sensor_results.get("drift_level", 0.0) or 0.0))),
        ("Offset", 1.0 - min(1.0, float(sensor_results.get("offset_level", 0.0) or 0.0))),
        ("Rauschen", 1.0 - min(1.0, float(sensor_results.get("noise_level", 0.0) or 0.0))),
    ]
    for i, (name, value) in enumerate(sub_scores):
        y = 0.02 - i * 0.14
        ax.barh([y], [1.0], left=[0.0], height=0.06, color="#dee2e6")
        ax.barh([y], [value], left=[0.0], height=0.06,
                color="#198754" if value >= 0.8 else ("#ffc107" if value >= 0.6 else "#dc3545"))
        ax.text(1.02, y, f"{name}: {value:.2f}", va="center", fontsize=8)
    ax.set_xlim(0.0, 1.6)
    ax.set_ylim(-0.45, 1.0)
    ax.set_yticks([])
    ax.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_title("D: Quality Gauge (0-1) mit Teil-Scores")


def sensor_recommendations(sensor_results: Dict[str, Any]) -> List[str]:
    """Concrete optimization recommendations derived from the sensor results."""
    recommendations: List[str] = []
    results = sensor_results or {}
    score = float(results.get("overall_quality_score", 1.0) or 1.0)
    if results.get("drift_detected"):
        recommendations.append(
            "Drift \u00fcber die Messreihe: Warm-up-Phase des Sensors beachten "
            "(erste Messungen verwerfen) und eine Re-Kalibrierung durchf\u00fchren.")
    if results.get("offset_detected"):
        recommendations.append(
            "Baseline-Offset erkannt: Dunkelreferenz (Dark Current) und "
            "Weissreferenz neu aufnehmen.")
    if results.get("noise_detected"):
        recommendations.append(
            "Rauschen \u00fcber der Schwelle: Messzeit pro Spektrum erh\u00f6hen "
            "oder mehrere Replikate mitteln, um das Signal-Rausch-Verh\u00e4ltnis "
            "zu verbessern.")
    if not results.get("reference_valid", True):
        recommendations.append(
            "Referenzspektrum unbrauchbar: neue Referenzmessung erforderlich.")
    if score >= 0.8 and not recommendations:
        recommendations.append(
            "Sensor in Ordnung: keine Ma\u00dfnahmen erforderlich. Regelm\u00e4ssige "
            "Kontrollmessungen mit einem Standard beibehalten.")
    elif not recommendations:
        recommendations.append(
            "Sensorqualit\u00e4t eingeschr\u00e4nkt: Messbedingungen (Temperatur, "
            "Beleuchtung, Kontakt) pr\u00fcfen und die Messreihe wiederholen.")
    return recommendations


def sensor_dashboard_data_urls(measurement_samples: List[Any],
                               sensor_results: Dict[str, Any],
                               wavelengths: List[float]) -> Dict[str, str]:
    """Render the 4-panel sensor quality dashboard from the real replicas.

    Returns a dict with the single key 'sensor_dashboard' (base64 PNG data
    URL) - empty dict when matplotlib is missing, fewer than two replicas
    exist or no sensor results are supplied. Never raises.
    """
    charts: Dict[str, str] = {}
    if not MATPLOTLIB_AVAILABLE:
        return charts
    try:
        matrix = _as_matrix(measurement_samples)
        if matrix is None or not sensor_results:
            return charts
        wl = np.asarray(wavelengths, dtype=float) if wavelengths else \
            np.arange(matrix.shape[1], dtype=float)
        if wl.size != matrix.shape[1]:
            wl = np.arange(matrix.shape[1], dtype=float)

        fig, axes = plt.subplots(2, 2, figsize=(13, 9))
        _panel_control_chart(axes[0, 0], matrix)
        _panel_overlay(axes[0, 1], matrix, wl)
        _panel_channel_noise(axes[1, 0], matrix, wl)
        _panel_gauge(axes[1, 1], sensor_results)
        fig.suptitle("Sensorqualit\u00e4ts-Dashboard (SPC)", fontsize=13)
        fig.tight_layout(rect=(0, 0, 1, 0.97))
        charts["sensor_dashboard"] = _figure_to_data_url(fig)
    except Exception:
        logger.exception("Sensor dashboard rendering failed (non-fatal)")
        return {}
    return charts
