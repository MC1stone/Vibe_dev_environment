# NIR Intelligence Platform - calibration charts (OP20)
# The three standard plots every chemometric calibration report carries:
#
#   ref_vs_pred   : reference vs. cross-validated predicted values
#                   (how good is the calibration?) - PLS with 5-fold CV,
#                   R2CV and RMSECV annotated
#   reg_coefficients : PLS regression coefficients per wavelength
#                   (why does it work? the sought-after plot) - signed
#                   coefficients over the channel axis
#   rmsecv_vs_n   : RMSECV as a function of the PLS component count
#                   (how complex must the model be?) - the minimum marks
#                   the optimal complexity
#
# All plots are computed from the real calibration samples with
# scikit-learn (no TensorFlow needed, CI-safe). Everything degrades
# gracefully: no matplotlib, too few calibration rows or a constant
# target -> empty dict, report intact. Base64 PNG data URLs, same
# contract as the other chart builders.
import base64
import io
import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("Service.CalibrationCharts")

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
    if matrix.ndim != 2 or matrix.shape[0] < 10 or matrix.shape[1] < 2:
        return None
    if not np.all(np.isfinite(matrix)):
        matrix = matrix[np.all(np.isfinite(matrix), axis=1)]
    if matrix.shape[0] < 10:
        return None
    return matrix


def _pls_ref_vs_pred(matrix: np.ndarray, y: np.ndarray):
    """5-fold cross-validated PLS predictions (never in-sample fit)."""
    from sklearn.cross_decomposition import PLSRegression
    from sklearn.model_selection import KFold, cross_val_predict

    n_components = max(1, min(10, matrix.shape[0] - 1, matrix.shape[1]))
    pls = PLSRegression(n_components=n_components)
    folds = max(2, min(5, matrix.shape[0]))
    predictions = cross_val_predict(pls, matrix, y, cv=KFold(folds, shuffle=True,
                                                            random_state=42))
    return np.asarray(predictions, dtype=float).ravel(), n_components, folds


def _ref_vs_pred(y_true: np.ndarray, y_pred: np.ndarray, r2: float,
                 rmse: float, method_note: str,
                 target_name: str = "Zielwert") -> str:
    fig, ax = plt.subplots(figsize=(6.5, 5))
    ax.scatter(y_true, y_pred, s=60, alpha=0.8, edgecolors="k")
    lo = float(min(y_true.min(), y_pred.min()))
    hi = float(max(y_true.max(), y_pred.max()))
    pad = 0.05 * (hi - lo) if hi > lo else 0.5
    ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], "r--", lw=1,
            label="Ideal (y = x)")
    ax.set_xlim(lo - pad, hi + pad)
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_xlabel(f"Referenz ({target_name})")
    ax.set_ylabel(f"Kreuzvalidierte Vorhersage ({target_name})")
    ax.set_title("Ref. vs. Pred (Kreuzvalidierung)\n"
                 f"R\u00b2cv = {r2:.3f}, RMSECV = {rmse:.3f} {target_name}")
    if method_note:
        ax.text(0.03, 0.97, method_note, transform=ax.transAxes, fontsize=8,
                va="top", ha="left", color="#0d6efd")
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(alpha=0.3)
    return _figure_to_data_url(fig)


def _reg_coefficients(coefficients: np.ndarray, wavelengths: np.ndarray,
                      n_components: int) -> str:
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = ["#d62728" if c < 0 else "#0d6efd" for c in coefficients]
    ax.bar(wavelengths, coefficients, color=colors, width=4.0, alpha=0.85)
    ax.axhline(0.0, color="k", lw=0.8)
    ax.set_xlabel("Wellenl\u00e4nge (nm)")
    ax.set_ylabel("Regressionskoeffizient")
    ax.set_title(f"Regressionskoeffizienten pro Wellenl\u00e4nge "
                 f"(PLS, {n_components} Komponenten)")
    ax.grid(alpha=0.3, axis="y")
    return _figure_to_data_url(fig)


def _rmsecv_vs_n(n_values: List[int], rmsecv_values: List[float],
                 best_n: int, target_name: str = "Zielwert") -> str:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(n_values, rmsecv_values, "o-", color="#0d6efd", ms=5)
    ax.axvline(best_n, color="#d62728", ls="--", lw=1,
               label=f"Optimum: n = {best_n}")
    ax.set_xlabel("Anzahl PLS-Komponenten (n)")
    ax.set_ylabel(f"RMSECV ({target_name})")
    ax.set_title("RMSECV vs. Anzahl Komponenten\n(Wie komplex muss das Modell sein?)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    return _figure_to_data_url(fig)


def calibration_chart_data_urls(calibration_samples: List[List[float]],
                                reference_values: List[float],
                                wavelengths: List[float],
                                target_name: str = "Zielwert") -> Dict[str, str]:
    """Render the three standard calibration plots from the real data.

    Returns a dict of base64 PNG data URLs (keys: ref_vs_pred,
    reg_coefficients, rmsecv_vs_n) - empty dict when matplotlib or
    scikit-learn is missing or the data is insufficient. Never raises.
    """
    charts: Dict[str, str] = {}
    if not MATPLOTLIB_AVAILABLE:
        return charts
    try:
        from sklearn.cross_decomposition import PLSRegression
        from sklearn.model_selection import KFold, cross_val_predict

        matrix = _as_matrix(calibration_samples)
        if matrix is None or reference_values is None:
            return charts
        y = np.asarray(reference_values, dtype=float).ravel()
        if y.size != matrix.shape[0]:
            return charts
        if matrix.shape[0] < 10 or np.unique(y).size < 3:
            return charts
        wl = np.asarray(wavelengths, dtype=float) if wavelengths else \
            np.arange(matrix.shape[1], dtype=float)
        if wl.size != matrix.shape[1]:
            wl = np.arange(matrix.shape[1], dtype=float)

        # --- Ref vs. Pred: 5-fold cross-validated PLS --------------------
        y_pred, n_components, folds = _pls_ref_vs_pred(matrix, y)
        ss_res = float(np.sum((y - y_pred) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2_cv = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        rmsecv = float(np.sqrt(ss_res / y.size))
        method_note = f"PLS ({n_components} Komponenten), {folds}-fache Kreuzvalidierung"
        charts["ref_vs_pred"] = _ref_vs_pred(y, y_pred, r2_cv, rmsecv,
                                            method_note, target_name)

        # --- Regression coefficients --------------------------------------
        pls = PLSRegression(n_components=n_components).fit(matrix, y)
        coefficients = np.asarray(pls.coef_, dtype=float).ravel()
        charts["reg_coefficients"] = _reg_coefficients(coefficients, wl, n_components)

        # --- RMSECV vs. n ---------------------------------------------------
        max_n = max(2, min(10, matrix.shape[0] - 1, matrix.shape[1]))
        folds = max(2, min(5, matrix.shape[0]))
        n_values: List[int] = []
        rmsecv_values: List[float] = []
        for n in range(1, max_n + 1):
            try:
                preds = cross_val_predict(PLSRegression(n_components=n), matrix, y,
                                          cv=KFold(folds, shuffle=True,
                                                   random_state=42))
            except Exception:
                continue
            preds = np.asarray(preds, dtype=float).ravel()
            n_values.append(n)
            rmsecv_values.append(float(np.sqrt(np.mean((y - preds) ** 2))))
        if not n_values:
            return {k: v for k, v in charts.items() if k != "rmsecv_vs_n"}
        best_n = n_values[int(np.argmin(rmsecv_values))]
        charts["rmsecv_vs_n"] = _rmsecv_vs_n(n_values, rmsecv_values, best_n,
                                           target_name)
    except Exception:
        logger.exception("Calibration chart rendering failed (non-fatal)")
        return {}
    return charts
