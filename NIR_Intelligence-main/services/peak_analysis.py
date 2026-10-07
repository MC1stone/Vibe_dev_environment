"""Peak analysis module for the NIR-IP (M5 of the interoperability plan).

Reusable peak detection and characterisation built on scipy only:
- detect_peaks: robust peak picking (height/prominence/distance)
- detect_derivative_peaks: second-derivative peak picking (standard for
  overlapping NIR bands; minima of the second derivative mark band positions)
- characterize_peaks: position, height, width, area per peak
- peak_drift: per-peak shift between a reference and measurement spectrum
  for sensor drift monitoring (shift_detector_agent)
- peak_feature_vector: fixed-length descriptor for FAISS peak comparison

Independently developed with scipy (Fityk is GPL-2.0 - concept only, no code,
see THIRD_PARTY_LICENSES.md).
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import signal


def detect_peaks(intensities, min_height: float = 0.1,
                 min_prominence: float = 0.05,
                 min_distance: int = 5) -> np.ndarray:
    """Indices of prominent peaks in an intensity array."""
    intensities = np.asarray(intensities, dtype="float64")
    if intensities.size < 3:
        return np.array([], dtype=int)
    return signal.find_peaks(
        intensities,
        height=min_height,
        prominence=min_prominence,
        distance=min_distance,
    )[0]


def detect_derivative_peaks(wavelengths, intensities,
                            window_length: int = 7,
                            poly_order: int = 2,
                            min_prominence: float = 0.01) -> np.ndarray:
    """Second-derivative peak picking.

    For absorbance-like spectra band maxima appear as minima of the second
    derivative; we therefore pick minima of d2 and return their indices in
    the original axis.
    """
    wavelengths = np.asarray(wavelengths, dtype="float64")
    intensities = np.asarray(intensities, dtype="float64")
    if intensities.size < max(5, window_length):
        return np.array([], dtype=int)
    if window_length % 2 == 0:
        window_length += 1
    d2 = signal.savgol_filter(intensities, window_length, poly_order, deriv=2)
    inverted = -d2
    peaks, _ = signal.find_peaks(inverted, prominence=min_prominence)
    return peaks


def characterize_peaks(wavelengths, intensities,
                       peak_indices: Optional[np.ndarray] = None,
                       min_height: float = 0.1,
                       min_prominence: float = 0.05,
                       min_distance: int = 5) -> List[Dict[str, Any]]:
    """Descriptor list (position, height, width, area) for each peak."""
    wavelengths = np.asarray(wavelengths, dtype="float64")
    intensities = np.asarray(intensities, dtype="float64")
    if peak_indices is None:
        peak_indices = detect_peaks(intensities, min_height=min_height,
                                    min_prominence=min_prominence,
                                    min_distance=min_distance)
    results: List[Dict[str, Any]] = []
    if wavelengths.size != intensities.size or intensities.size == 0:
        return results
    for idx in peak_indices:
        idx = int(idx)
        if idx <= 0 or idx >= intensities.size - 1:
            left, mid, right = idx - 1, idx, idx + 1
        else:
            left, mid, right = idx - 1, idx, idx + 1
        half_height = intensities[mid] / 2.0
        lo = mid
        while lo > 0 and intensities[lo] > half_height:
            lo -= 1
        hi = mid
        while hi < intensities.size - 1 and intensities[hi] > half_height:
            hi += 1
        width = float(wavelengths[min(hi, wavelengths.size - 1)]
                      - wavelengths[max(lo, 0)])
        area = float(np.trapezoid(intensities[lo:hi + 1],
                                  wavelengths[lo:hi + 1]))
        results.append({
            "index": idx,
            "position": float(wavelengths[idx]),
            "height": float(intensities[idx]),
            "width": width,
            "area": area,
        })
    return results


def peak_drift(reference_wavelengths, reference_intensities,
               measurement_wavelengths, measurement_intensities,
               max_relative_shift: float = 0.02,
               **detect_kwargs) -> Dict[str, Any]:
    """Per-peak drift between reference and measurement spectrum.

    Returns {'pairs': [{reference_position, measured_position, shift}],
             'matched', 'reference_peak_count', 'measurement_peak_count',
             'mean_shift', 'max_shift'}.
    """
    ref_idx = detect_peaks(reference_intensities, **detect_kwargs)
    meas_idx = detect_peaks(measurement_intensities, **detect_kwargs)
    ref_pos = np.asarray(reference_wavelengths, dtype="float64")[ref_idx] \
        if ref_idx.size else np.array([])
    meas_pos = np.asarray(measurement_wavelengths, dtype="float64")[meas_idx] \
        if meas_idx.size else np.array([])

    pairs: List[Dict[str, Any]] = []
    used = set()
    for r in ref_pos:
        tolerance = abs(r) * max_relative_shift
        candidates = [(abs(m - r), i, m) for i, m in enumerate(meas_pos)
                      if i not in used and abs(m - r) <= max(tolerance, 1e-9)]
        if not candidates:
            continue
        candidates.sort()
        _, i, m = candidates[0]
        used.add(i)
        pairs.append({
            "reference_position": float(r),
            "measured_position": float(m),
            "shift": float(m - r),
        })
    shifts = [p["shift"] for p in pairs]
    return {
        "pairs": pairs,
        "matched": len(pairs),
        "reference_peak_count": int(ref_pos.size),
        "measurement_peak_count": int(meas_pos.size),
        "mean_shift": float(np.mean(shifts)) if shifts else 0.0,
        "max_shift": float(np.max(np.abs(shifts))) if shifts else 0.0,
    }


def peak_feature_vector(wavelengths, intensities, n_bins: int = 64,
                        **detect_kwargs) -> np.ndarray:
    """Fixed-length peak-position histogram for FAISS peak comparison.

    Peaks are binned over the covered wavelength range; the vector is
    L2-normalised so FAISS inner-product search acts as cosine similarity.
    """
    wavelengths = np.asarray(wavelengths, dtype="float64")
    intensities = np.asarray(intensities, dtype="float64")
    idx = detect_peaks(intensities, **detect_kwargs)
    vec = np.zeros(n_bins, dtype="float64")
    if idx.size == 0 or wavelengths.size < 2:
        return vec
    lo, hi = float(wavelengths.min()), float(wavelengths.max())
    span = hi - lo
    if span <= 0:
        vec[0] = float(idx.size)
        return vec
    for i in idx:
        bin_idx = int((float(wavelengths[i]) - lo) / span * (n_bins - 1))
        vec[bin_idx] += 1.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec
