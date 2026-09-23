# NIR Intelligence Platform - PCA chart builder (OP16)
# Standard spectroscopy PCA visualisations for the statistical analysis
# section: score plot (PC1 vs PC2), loading plot, biplot, scree plot,
# R2 per wavelength and SPE plot. Rendered with matplotlib (Agg) as base64
# PNG data URLs, same contract as the OP11 report charts. Charts are
# optional: without matplotlib (or with too few samples) the returned
# dict simply stays empty and the report degrades gracefully.
import base64
import io
import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("Service.PcaCharts")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

MIN_SAMPLES = 3


def _figure_to_data_url(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _matrix(measurement_samples) -> Optional[np.ndarray]:
    if not measurement_samples:
        return None
    matrix = np.asarray(measurement_samples, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] < MIN_SAMPLES or matrix.shape[1] < 2:
        return None
    if not np.all(np.isfinite(matrix)):
        matrix = matrix[np.all(np.isfinite(matrix), axis=1)]
    if matrix.shape[0] < MIN_SAMPLES:
        return None
    return matrix


def _n_components(matrix: np.ndarray) -> int:
    return int(max(2, min(5, matrix.shape[0] - 1, matrix.shape[1])))


def pca_chart_data_urls(measurement_samples: List[List[float]],
                        wavelengths: List[float],
                        sample_labels: Optional[List[str]] = None
                        ) -> Dict[str, str]:
    """Returns a dict with keys 'score_plot', 'loading_plot', 'biplot',
    'scree_plot', 'r2_per_wavelength', 'spe_plot' - each a base64 PNG data
    URL, or '' / missing when a plot cannot be built (never raises)."""
    """Render the six standard PCA plots for one dataset.

    Returns a dict with keys 'score_plot', 'loading_plot', 'biplot',
    'scree_plot', 'r2_per_wavelength', 'spe_plot' - each a base64 PNG data
    URL, or '' / missing when a plot cannot be built (never raises).
    """
    charts: Dict[str, str] = {}
    if not MATPLOTLIB_AVAILABLE:
        return charts
    try:
        matrix = _matrix(measurement_samples)
        if matrix is None:
            return charts
        wl = np.asarray(wavelengths, dtype=float) if wavelengths else np.arange(matrix.shape[1], dtype=float)
        if wl.size != matrix.shape[1]:
            wl = np.arange(matrix.shape[1], dtype=float)
        from sklearn.decomposition import PCA

        n_components = _n_components(matrix)
        pca = PCA(n_components=n_components)
        scores = pca.fit_transform(matrix)
        explained = pca.explained_variance_ratio_
        loadings = pca.components_.T  # (n_points, n_components)
        mean = pca.mean_
        residual = matrix - pca.inverse_transform(scores)
        spe = np.sum(residual ** 2, axis=1)
        # R2 per wavelength: fraction of each channel's variance explained
        # by the retained components (reconstructed vs original values).
        reconstructed = pca.inverse_transform(scores)
        channel_var = np.var(matrix, axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            r2 = 1.0 - np.var(matrix - reconstructed, axis=0) / np.where(channel_var > 0, channel_var, np.nan)
        r2 = np.nan_to_num(r2, nan=0.0)

        def pct(i):
            return 100.0 * explained[i] if i < len(explained) else 0.0

        # --- Score plot (PC1 vs PC2): sample clustering, outliers -------
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter(scores[:, 0], scores[:, 1], s=70, alpha=0.8, edgecolors="k")
        if sample_labels:
            for x, y, label in zip(scores[:, 0], scores[:, 1], sample_labels[:len(scores)]):
                ax.annotate(str(label), (x, y), fontsize=7, alpha=0.7)
        ax.axhline(0, color="grey", lw=0.5)
        ax.axvline(0, color="grey", lw=0.5)
        ax.set_xlabel(f"PC1 ({pct(0):.1f} % Varianz)")
        ax.set_ylabel(f"PC2 ({pct(1):.1f} % Varianz)")
        ax.set_title("Score-Plot: Proben-Clustering (PC1 vs PC2)")
        ax.grid(alpha=0.3)
        charts["score_plot"] = _figure_to_data_url(fig)

        # --- Loading plot: which wavelengths drive each component ------
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for comp in range(min(2, loadings.shape[1])):
            ax.plot(wl, loadings[:, comp],
                    label=f"PC{comp + 1}", linewidth=1.2)
        ax.axhline(0, color="grey", lw=0.5)
        ax.set_xlabel("Wellenlänge (nm)")
        ax.set_ylabel("Loading")
        ax.set_title("Loading-Plot: Wellenlängen-Beiträge pro Komponente")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        charts["loading_plot"] = _figure_to_data_url(fig)

        # --- Biplot: scores + loadings in one graphic -------------------
        scale = np.abs(scores[:, :2]).max() / (np.abs(loadings[:, :2]).max() or 1.0)
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter(scores[:, 0], scores[:, 1], s=70, alpha=0.8, edgecolors="k", label="Proben")
        for idx in np.argsort(-np.abs(loadings[:, 0]))[: min(7, len(wl))]:
            ax.annotate("", xy=(loadings[idx, 0] * scale, loadings[idx, 1] * scale),
                        xytext=(0, 0),
                        arrowprops=dict(arrowstyle="->", color="#d62728", lw=1))
            ax.annotate(f"{wl[idx]:.0f}", (loadings[idx, 0] * scale, loadings[idx, 1] * scale),
                        fontsize=7, color="#d62728")
        ax.axhline(0, color="grey", lw=0.5)
        ax.axvline(0, color="grey", lw=0.5)
        ax.set_xlabel(f"PC1 ({pct(0):.1f} % Varianz)")
        ax.set_ylabel(f"PC2 ({pct(1):.1f} % Varianz)")
        ax.set_title("Biplot: Scores und Loadings")
        ax.grid(alpha=0.3)
        charts["biplot"] = _figure_to_data_url(fig)

        # --- Scree plot: eigenvalues -> choice of component count -------
        fig, ax = plt.subplots(figsize=(7, 4.5))
        eigenvalues = pca.explained_variance_
        ax.plot(range(1, len(eigenvalues) + 1), eigenvalues, "o-")
        ax.set_xlabel("Hauptkomponente")
        ax.set_ylabel("Eigenwert")
        ax.set_title("Scree-Plot: Eigenwerte der Hauptkomponenten")
        ax.grid(alpha=0.3)
        charts["scree_plot"] = _figure_to_data_url(fig)

        # --- R2 per wavelength: which spectral regions each PC explains -
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.plot(wl, r2, color="#0d6efd")
        ax.set_xlabel("Wellenlänge (nm)")
        ax.set_ylabel("R² pro Wellenlänge")
        ax.set_title(f"Erklärte Varianz pro Wellenlänge ({n_components} PC)")
        ax.set_ylim(min(0.0, float(np.min(r2))), 1.05)
        ax.grid(alpha=0.3)
        charts["r2_per_wavelength"] = _figure_to_data_url(fig)

        # --- SPE plot: outlier / model-fit quality ----------------------
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.plot(range(1, len(spe) + 1), spe, "o-", color="#d62728")
        if len(spe) >= 3:
            threshold = float(np.median(spe) + 3.0 * float(np.std(spe)))
            ax.axhline(threshold, color="orange", linestyle="--", lw=1,
                       label=f"Schwelle (med+3σ): {threshold:.1f}")
            ax.legend(fontsize=8)
        ax.set_xlabel("Messung (Index)")
        ax.set_ylabel("SPE (quadrierter Rekonstruktionsfehler)")
        ax.set_title("SPE-Plot: Outlier / Modellgüte")
        ax.grid(alpha=0.3)
        charts["spe_plot"] = _figure_to_data_url(fig)
    except Exception:
        logger.exception("PCA chart rendering failed (non-fatal)")
        return {}
    return charts
