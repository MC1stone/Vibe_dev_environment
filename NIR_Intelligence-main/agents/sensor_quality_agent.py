# NIR Intelligence Platform - Sensor Quality Agent
# Handles instrument performance monitoring and quality control (MO 4).
# Real implementation: drift, offset, noise and reference validity are
# computed from the supplied spectra via numpy (with an optional scipy
# detrend). No simulated values.

from typing import Any, Dict, List, Optional

import numpy as np

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


def _extract_matrix(spectra: Any) -> Optional[np.ndarray]:
    """Extract an (n_spectra, n_points) float matrix from supported inputs.

    Supported: 2-D array-like, list of intensity vectors, unified spectral
    schema dicts (S3, 'data' DataFrame or 'intensities' list).
    """
    if spectra is None:
        return None
    if isinstance(spectra, np.ndarray):
        return np.asarray(spectra, dtype=float) if spectra.size else None
    if isinstance(spectra, dict):
        if spectra.get("data") is None and spectra.get("intensities") is None:
            return None
        spectra = [spectra]
    if not isinstance(spectra, (list, tuple)) or len(spectra) == 0:
        return None
    rows: List[np.ndarray] = []
    for item in spectra:
        if isinstance(item, dict):
            data = item.get("data")
            if data is None:
                intensities = item.get("intensities")
                if intensities is None:
                    return None
                rows.append(np.asarray(intensities, dtype=float))
            else:
                import pandas as pd

                if isinstance(data, pd.DataFrame):
                    column = item.get("intensity_column", "intensity")
                    if column not in data.columns:
                        column = data.columns[-1]
                    rows.append(data[column].to_numpy(dtype=float))
                else:
                    rows.append(np.asarray(data, dtype=float))
        else:
            rows.append(np.asarray(item, dtype=float))
    if any(row.size == 0 for row in rows):
        return None
    if len({row.size for row in rows}) != 1:
        return None
    return np.vstack(rows)


class SensorQualityAgent(BaseAgent):
    """Agent for monitoring sensor quality and instrument performance.

    Real checks (context keys):
    - spectra: spectra to assess (list of vectors or unified schema dicts)
    - reference_spectrum: reference for drift/offset ('mean' default)
    - drift_threshold / noise_threshold: limit overrides
    """

    def __init__(self, **kwargs):
        super().__init__(name="SensorQualityAgent", version="2.0.0", **kwargs)
        self.dependencies = ["numpy", "scipy"]
        self.drift_threshold = float(kwargs.get("drift_threshold", 0.01))
        self.noise_threshold = float(kwargs.get("noise_threshold", 0.05))
        self.reference_spectrum = kwargs.get("reference_spectrum", "mean")
        self.checks = kwargs.get("checks", ["drift", "offset", "noise", "reference_validity"])

    def _compute_reference(self, matrix: np.ndarray, context: Dict[str, Any]) -> Optional[np.ndarray]:
        explicit = context.get("reference_spectrum")
        if explicit is not None:
            if isinstance(explicit, str) and explicit == "mean":
                return matrix.mean(axis=0)
            vector = _extract_matrix(explicit)
            if vector is not None:
                return vector.mean(axis=0)
            return None
        if self.reference_spectrum == "mean" or matrix.shape[0] == 1:
            return matrix.mean(axis=0)
        return matrix[0]

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute sensor quality agent workflow."""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting sensor quality agent execution")

            context = context or {}
            matrix = _extract_matrix(context.get("spectra", context.get("spectral_data")))
            if matrix is None:
                return self._create_success_output({
                    "checks_performed": [],
                    "status": "no_data",
                    "message": "No spectra supplied for sensor quality assessment",
                })

            reference = self._compute_reference(matrix, context)
            if reference is None:
                return self._handle_error(ValueError(
                    "reference_spectrum could not be interpreted"))

            mean_level = float(matrix.mean())
            scale = abs(mean_level) if mean_level != 0 else 1.0

            results: Dict[str, Any] = {
                "checks_performed": list(self.checks),
                "num_spectra": int(matrix.shape[0]),
                "data_points": int(matrix.shape[1]),
            }
            warnings: List[str] = []

            drift_threshold = float(context.get("drift_threshold", self.drift_threshold))
            noise_threshold = float(context.get("noise_threshold", self.noise_threshold))

            if "drift" in self.checks:
                normalized_drift = float(np.abs(matrix - reference).mean() / scale)
                drift_detected = bool(normalized_drift > drift_threshold)
                results["drift_detected"] = drift_detected
                results["drift_level"] = normalized_drift
                if drift_detected:
                    warnings.append(
                        f"Drift detected: mean deviation {normalized_drift:.4f} "
                        f"exceeds threshold {drift_threshold:.4f}")

            if "offset" in self.checks:
                offsets = matrix.mean(axis=1) - reference.mean()
                normalized_offset = float(np.abs(offsets).max() / scale)
                offset_detected = bool(normalized_offset > drift_threshold)
                results["offset_detected"] = offset_detected
                results["offset_level"] = normalized_offset
                if offset_detected:
                    warnings.append(
                        f"Offset detected: max baseline shift {normalized_offset:.4f} "
                        f"exceeds threshold {drift_threshold:.4f}")

            if "noise" in self.checks:
                try:
                    from scipy.signal import detrend
                    residuals = np.apply_along_axis(detrend, 1, matrix)
                except ImportError:
                    residuals = matrix - matrix.mean(axis=1, keepdims=True)
                if matrix.shape[0] == 1:
                    # Single spectrum: first differences of the detrended
                    # signal are dominated by the genuine spectral SHAPE
                    # (peaks, slopes), not sensor noise. Estimate noise from
                    # the robust scale of second differences (median absolute
                    # deviation * 1.4826), which suppresses smooth trends AND
                    # ignores single-band spikes (saturation outliers).
                    second_diff = np.diff(residuals, n=2, axis=1)
                    robust_sigma = float(np.median(np.abs(second_diff)) * 1.4826)
                    noise_level = float(robust_sigma / np.sqrt(6.0) / scale)
                else:
                    successive = np.abs(np.diff(residuals, axis=1)).mean()
                    noise_level = float(successive / np.sqrt(2.0) / scale)
                noise_detected = bool(noise_level > noise_threshold)
                results["noise_level"] = noise_level
                results["noise_detected"] = noise_detected
                if noise_detected:
                    warnings.append(
                        f"Noise level {noise_level:.4f} exceeds threshold {noise_threshold:.4f}")

            if "reference_validity" in self.checks:
                valid = bool(
                    np.all(np.isfinite(reference))
                    and reference.size == matrix.shape[1]
                    and np.abs(reference).max() > 0
                )
                results["reference_valid"] = valid
                if not valid:
                    warnings.append("Reference spectrum is not usable (empty or non-finite)")

            penalties = 0.0
            if results.get("drift_detected"):
                penalties += results["drift_level"]
            if results.get("offset_detected"):
                penalties += results["offset_level"]
            if results.get("noise_detected"):
                penalties += results["noise_level"]
            if not results.get("reference_valid", True):
                penalties += 0.5
            results["overall_quality_score"] = float(max(0.0, 1.0 - penalties))
            results["status"] = "ok" if not warnings else "degraded"
            results["warnings"] = warnings

            self.status = AgentStatus.COMPLETED
            return self._create_success_output(results)
        except Exception as e:
            return self._handle_error(e)
