"""M5 verification: shared peak analysis module.

Covers peak detection, second-derivative peaks, characterisation, one-to-one
per-peak drift matching and the FAISS peak feature vector, plus integration
with the shift detector agent."""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from services.peak_analysis import (
    characterize_peaks,
    detect_derivative_peaks,
    detect_peaks,
    peak_drift,
    peak_feature_vector,
)


def _gaussian_band(x, center, height=1.0, width=20.0):
    return height * np.exp(-((x - center) ** 2) / (2 * width ** 2))


def _spectrum(centers, x=None):
    if x is None:
        x = np.arange(1000, 2500, 2.0)
    y = np.zeros_like(x)
    for c in centers:
        y += _gaussian_band(x, c)
    return x, y


def test_detect_peaks_finds_bands():
    x, y = _spectrum([1200.0, 1800.0, 2200.0])
    idx = detect_peaks(y, min_height=0.3, min_prominence=0.2, min_distance=10)
    found = [float(x[i]) for i in idx]
    assert len(found) == 3
    assert abs(found[0] - 1200.0) <= 2.0
    assert abs(found[2] - 2200.0) <= 2.0


def test_detect_peaks_empty_for_flat_spectrum():
    idx = detect_peaks(np.zeros(50), min_height=0.1)
    assert idx.size == 0


def test_derivative_peaks_resolve_overlapping_bands():
    x = np.arange(1000, 2000, 1.0)
    y = _gaussian_band(x, 1300.0, 1.0, 40.0) + _gaussian_band(x, 1360.0, 0.8, 30.0)
    idx = detect_derivative_peaks(x, y, window_length=11, min_prominence=1e-4)
    found = sorted(float(x[i]) for i in idx)
    assert len(found) >= 2
    assert abs(found[0] - 1300.0) <= 15.0
    assert abs(found[-1] - 1360.0) <= 15.0


def test_characterize_peaks_descriptors():
    x, y = _spectrum([1500.0])
    peaks = characterize_peaks(x, y, min_height=0.3, min_prominence=0.2)
    assert len(peaks) == 1
    p = peaks[0]
    assert abs(p["position"] - 1500.0) <= 2.0
    assert abs(p["height"] - 1.0) < 0.01
    assert p["width"] > 0
    assert p["area"] > 0


def test_peak_drift_detects_uniform_shift():
    x_ref, y_ref = _spectrum([1200.0, 1600.0, 2000.0])
    x_meas = x_ref + 5.0
    _, y_meas = _spectrum([1205.0, 1605.0, 2005.0], x=x_meas)
    drift = peak_drift(x_ref, y_ref, x_meas, y_meas,
                       min_height=0.3, min_prominence=0.2)
    assert drift["matched"] == 3
    assert abs(drift["mean_shift"] - 5.0) < 1.0
    assert drift["max_shift"] >= 4.0
    for pair in drift["pairs"]:
        assert abs(pair["shift"] - 5.0) < 1.5


def test_peak_drift_no_false_matches():
    x_ref, y_ref = _spectrum([1200.0, 1600.0, 2000.0])
    x_m, y_m = _spectrum([1450.0])
    drift = peak_drift(x_ref, y_ref, x_m, y_m,
                       max_relative_shift=0.02,
                       min_height=0.3, min_prominence=0.2)
    assert drift["matched"] == 0
    assert drift["mean_shift"] == 0.0


def test_peak_feature_vector():
    x1, y1 = _spectrum([1200.0, 1800.0])
    x2, y2 = _spectrum([1200.0, 1800.0])
    x3, y3 = _spectrum([2100.0])
    v1 = peak_feature_vector(x1, y1, min_height=0.3, min_prominence=0.2)
    v2 = peak_feature_vector(x2, y2, min_height=0.3, min_prominence=0.2)
    v3 = peak_feature_vector(x3, y3, min_height=0.3, min_prominence=0.2)
    assert v1.shape == (64,)
    assert abs(np.linalg.norm(v1) - 1.0) < 1e-9
    assert float(np.dot(v1, v2)) > 0.9
    assert float(np.dot(v1, v3)) < 0.2


def test_shift_detector_integration():
    import logging
    logging.disable(logging.WARNING)
    from agents.shift_detector_agent import ShiftDetectorAgent
    agent = ShiftDetectorAgent()
    x_ref, y_ref = _spectrum([1200.0, 1600.0, 2000.0])
    x_meas = x_ref + 5.0
    _, y_meas = _spectrum([1205.0, 1605.0, 2005.0], x=x_meas)
    result = agent.detect_peak_drift(x_meas, y_meas, x_ref, y_ref)
    assert result is not None
    assert result.detection_method == "per_peak_drift"
    assert abs(result.shift_value - 5.0) < 1.0
    result_none = agent.detect_peak_drift(x_ref, y_ref, x_ref, y_ref)
    assert result_none is None


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {t.__name__}: {e}")
    if failed:
        raise SystemExit(f"{failed} test(s) failed")
    print(f"All {len(tests)} tests passed.")


if __name__ == "__main__":
    main()
