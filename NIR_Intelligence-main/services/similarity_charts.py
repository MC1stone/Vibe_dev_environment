# NIR Intelligence Platform - spectrum and similarity charts (OP22)
# Two plots around the uploaded spectral data:
#
#   spectrum        : the uploaded/analysed spectrum as a single line
#                     (shown in the spectral analysis section)
#   similarity_top3 : the query spectrum plus the three most similar
#                     spectra from the comparison (FAISS similarity
#                     search) - shown in the database comparison section
#
# Both plots render from the real data. Everything degrades gracefully:
# no matplotlib, no intensities or no matches -> missing chart or empty
# dict, report intact. Base64 PNG data URLs, same contract as the other
# chart builders.
import base64
import io
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("Service.SimilarityCharts")

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


def _vectors(values: Any) -> Optional[np.ndarray]:
    if values is None:
        return None
    vector = np.asarray(values, dtype=float)
    if vector.size == 0 or not np.all(np.isfinite(vector)):
        return None
    return vector


def spectrum_chart_data_url(wavelengths: List[Any], intensities: List[Any],
                            title: str = "Spektrum") -> str:
    """One line for the uploaded spectrum - same style as the database
    detail page. Returns '' when matplotlib is missing or the data is
    empty. Never raises."""
    if not MATPLOTLIB_AVAILABLE:
        return ""
    try:
        wl = _vectors(wavelengths)
        it = _vectors(intensities)
        if wl is None or it is None or wl.size != it.size:
            return ""
        fig, ax = plt.subplots(figsize=(8, 4.2))
        ax.plot(wl, it, color="#0d6efd", lw=1.2)
        ax.set_xlabel("Wellenl\u00e4nge (nm)")
        ax.set_ylabel("Intensit\u00e4t")
        ax.set_title(title)
        ax.grid(alpha=0.3)
        return _figure_to_data_url(fig)
    except Exception:
        logger.exception("Spectrum chart rendering failed (non-fatal)")
        return ""


def similarity_top3_chart_data_url(query_wavelengths: List[Any],
                                   query_intensities: List[Any],
                                   matches: List[Dict[str, Any]],
                                   reference_curves: Dict[str, Tuple[Any, Any]],
                                   max_curves: int = 3) -> str:
    """The query spectrum overlaid with the most similar spectra.

    matches: FAISS agent matches (dicts with reference_id, similarity),
    sorted descending by similarity internally. reference_curves maps the
    reference id to (wavelengths, intensities). Returns '' when matplotlib
    is missing or nothing can be drawn. Never raises."""
    if not MATPLOTLIB_AVAILABLE:
        return ""
    try:
        wl = _vectors(query_wavelengths)
        it = _vectors(query_intensities)
        if wl is None or it is None or wl.size != it.size:
            return ""
        ordered = sorted(
            [m for m in (matches or [])
             if isinstance(m, dict) and str(m.get("reference_id")) in (reference_curves or {})],
            key=lambda m: float(m.get("similarity") or 0.0), reverse=True)
        if not ordered:
            return ""
        fig, ax = plt.subplots(figsize=(8.5, 5))
        ax.plot(wl, it, color="#212529", lw=1.8, label="Messung (diese Datei)")
        colors = ["#0d6efd", "#fd7e14", "#20c997"]
        for rank, match in enumerate(ordered[:max(1, max_curves)]):
            rid = str(match.get("reference_id"))
            ref_wl, ref_it = reference_curves[rid]
            ref_wl_v = _vectors(ref_wl)
            ref_it_v = _vectors(ref_it)
            if ref_wl_v is None or ref_it_v is None or ref_wl_v.size != ref_it_v.size:
                continue
            similarity = float(match.get("similarity") or 0.0)
            ax.plot(ref_wl_v, ref_it_v, lw=1.0, alpha=0.8, color=colors[rank % 3],
                    label=f"{rank + 1}. {rid} (Sim {similarity:.3f})")
        ax.set_xlabel("Wellenl\u00e4nge (nm)")
        ax.set_ylabel("Intensit\u00e4t")
        ax.set_title("Spektrenvergleich: 3 \u00e4hnlichste Spektren "
                     "(Datenbank + Projekt)")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        return _figure_to_data_url(fig)
    except Exception:
        logger.exception("Similarity chart rendering failed (non-fatal)")
        return ""


def similarity_charts_data_urls(query_wavelengths: List[Any],
                                query_intensities: List[Any],
                                matches: List[Dict[str, Any]],
                                reference_curves: Dict[str, Tuple[Any, Any]],
                                spectrum_title: str = "Spektrum") -> Dict[str, str]:
    """Convenience wrapper: spectrum line + top-3 comparison in one dict."""
    charts: Dict[str, str] = {}
    url = spectrum_chart_data_url(query_wavelengths, query_intensities,
                                 title=spectrum_title)
    if url:
        charts["spectrum"] = url
    url = similarity_top3_chart_data_url(query_wavelengths, query_intensities,
                                         matches, reference_curves)
    if url:
        charts["similarity_top3"] = url
    return charts
