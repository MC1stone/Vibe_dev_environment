"""Shared curve extraction from uploaded spectrum files.

Single source of truth for turning a spectrum's original file into the
persisted curve (wavelengths/intensities/x_unit/y_unit). Used by:
- the upload pipeline (api/views.py _persist_curve_data)
- the analysis fallback (api/crewai_views.py start_analysis) so legacy
  records without a persisted curve remain analysable as long as their
  original file exists
- the backfill management command for existing datasets
"""

import logging
import os
import sys
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("Service.SpectrumCurve")


def _ensure_repo_on_path() -> Optional[str]:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    return repo_root


def extract_curve(file_path: str) -> Optional[Dict[str, Any]]:
    """Load the measured curve from a spectrum file via the format-agnostic
    loader chain. Returns {'wavelengths', 'intensities', 'x_unit', 'y_unit'}
    or None when no curve can be extracted. Never raises."""
    try:
        if not file_path or not os.path.exists(file_path):
            return None
        _ensure_repo_on_path()
        from agents.data_preparation_agent import EnhancedDataPreparationAgent
        from services.spectrum_units import canonical_xunit
        loader = EnhancedDataPreparationAgent(
            input_directory=os.path.dirname(file_path) or ".",
            output_directory=os.path.dirname(file_path) or ".",
            temp_directory=os.path.dirname(file_path) or ".",
        )
        loaded = loader._load_spectral_data(file_path)
        if not loaded or loaded.get('data') is None or len(loaded['data']) == 0:
            return None
        df = loaded['data']
        x_col = loaded.get('wavelength_column') or 'wavelength'
        y_col = loaded.get('intensity_column') or 'intensity'
        if x_col not in df.columns or y_col not in df.columns:
            return None
        wavelengths = [round(float(v), 6) for v in df[x_col].tolist()]
        intensities = [round(float(v), 6) for v in df[y_col].tolist()]
        if not wavelengths or len(wavelengths) != len(intensities):
            return None
        metadata = loaded.get('metadata') or {}
        x_unit = canonical_xunit(
            metadata.get('x_unit') or metadata.get('x_units') or 'nm')
        y_unit = str(metadata.get('y_unit') or metadata.get('y_units')
                     or 'a.u.')[:40] or 'a.u.'
        return {
            "wavelengths": wavelengths,
            "intensities": intensities,
            "x_unit": x_unit,
            "y_unit": y_unit,
        }
    except Exception as e:
        logger.error("Curve extraction failed for %s: %s", file_path, e)
        return None


def apply_curve_to_spectrum(spectrum, file_path: Optional[str] = None) -> bool:
    """Extract and persist the curve on a NIRSpectrum-like object (needs
    attributes wavelengths/intensities/x_unit/y_unit/data_points/
    wavelength_range_start/wavelength_range_end/resolution). Returns True
    when a curve was extracted. The caller saves the object."""
    path = file_path or getattr(spectrum, "get_file_path", lambda: None)()
    curve = extract_curve(path)
    if curve is None:
        return False
    spectrum.wavelengths = curve["wavelengths"]
    spectrum.intensities = curve["intensities"]
    spectrum.x_unit = curve["x_unit"]
    spectrum.y_unit = curve["y_unit"]
    spectrum.data_points = len(curve["wavelengths"])
    spectrum.wavelength_range_start = curve["wavelengths"][0]
    spectrum.wavelength_range_end = curve["wavelengths"][-1]
    spectrum.resolution = (
        (curve["wavelengths"][-1] - curve["wavelengths"][0])
        / (len(curve["wavelengths"]) - 1)
        if len(curve["wavelengths"]) > 1 else 1.0)
    return True
