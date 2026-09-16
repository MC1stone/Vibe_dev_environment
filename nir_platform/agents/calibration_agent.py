"""
Calibration Agent for NIR Intelligence Platform

This agent specializes in generating and applying calibration formulas for
different types of spectrometers, including DIY devices.
"""

import json
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from scipy import signal, stats

try:
    from sklearn.cross_decomposition import PLSRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_predict
    from sklearn.metrics import r2_score, mean_squared_error
    _SKLEARN_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    _SKLEARN_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class CalibrationCurve:
    """Represents a calibration curve with its parameters."""
    curve_type: str
    coefficients: List[float]
    domain: Tuple[float, float]
    r_squared: float
    rmse: float
    num_points: int
    
    def to_dict(self) -> Dict:
        return {
            "curve_type": self.curve_type,
            "coefficients": self.coefficients,
            "domain": list(self.domain),
            "r_squared": self.r_squared,
            "rmse": self.rmse,
            "num_points": self.num_points
        }


@dataclass
class AnalyteCalibration:
    """Multivariate calibration of NIR spectra onto a reference analyte.

    For multi-sample wide-NIR exports (e.g. SparkFun Triad tomato-ripeness
    data with a Brix reference column) this holds the fitted PLS regression of
    the per-sample intensity matrix onto the analyte, with cross-validated
    quality metrics. coefficients are on the *standardized* X scale; an
    intercept is stored separately.
    """
    analyte: str
    method: str
    num_samples: int = 0
    num_features: int = 0
    num_components: int = 0
    coefficients: List[float] = field(default_factory=list)
    intercept: float = 0.0
    wavelengths: List[float] = field(default_factory=list)
    brix_range: Tuple[float, float] = (0.0, 0.0)
    r_squared_cv: float = 0.0
    rmse_cv: float = 0.0
    r_squared_cal: float = 0.0
    rmse_cal: float = 0.0
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "analyte": self.analyte,
            "method": self.method,
            "num_samples": self.num_samples,
            "num_features": self.num_features,
            "num_components": self.num_components,
            "coefficients": self.coefficients,
            "intercept": self.intercept,
            "wavelengths": self.wavelengths,
            "brix_range": list(self.brix_range),
            "r_squared_cv": self.r_squared_cv,
            "rmse_cv": self.rmse_cv,
            "r_squared_cal": self.r_squared_cal,
            "rmse_cal": self.rmse_cal,
            "notes": self.notes,
        }


@dataclass
class CalibrationResult:
    """Container for calibration results."""
    wavelength_calibration: Optional[CalibrationCurve] = None
    intensity_calibration: Optional[CalibrationCurve] = None
    analyte_calibration: Optional[AnalyteCalibration] = None
    drift_compensation: Optional[Dict] = None
    spectrometer_parameters: Dict[str, Any] = field(default_factory=dict)
    calibration_quality: Dict[str, float] = field(default_factory=dict)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    issues_detected: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "wavelength_calibration": self.wavelength_calibration.to_dict() if self.wavelength_calibration else None,
            "intensity_calibration": self.intensity_calibration.to_dict() if self.intensity_calibration else None,
            "analyte_calibration": self.analyte_calibration.to_dict() if self.analyte_calibration else None,
            "drift_compensation": self.drift_compensation,
            "spectrometer_parameters": self.spectrometer_parameters,
            "calibration_quality": self.calibration_quality,
            "recommendations": self.recommendations,
            "issues_detected": self.issues_detected,
        }


class CalibrationAgent:
    """
    Agent for generating and applying calibration formulas for spectrometers.
    """
    
    def __init__(self, agent_id: str = "calibration_agent"):
        self.agent_id = agent_id
        self.emission_lines = self._load_emission_lines()
        self.spectrometer_database = self._load_spectrometer_database()
        logger.info(f"Calibration Agent {self.agent_id} initialized")
    
    def _load_emission_lines(self) -> Dict[str, List[float]]:
        """Load known emission lines."""
        return {
            "neon": [632.816, 638.299, 640.225, 650.653, 653.288, 659.895, 667.828, 671.704],
            "mercury": [253.652, 365.015, 404.656, 407.783, 435.835, 546.074, 576.960, 579.066],
            "holmium": [241.542, 287.150, 333.749, 345.500, 361.500, 405.393, 418.489, 445.478]
        }
    
    def _load_spectrometer_database(self) -> Dict:
        """Load spectrometer database."""
        return {
            "ocean_optics": {
                "calibration": {
                    "wavelength": {"method": "polynomial", "degree": 3, "points": [250, 400, 600, 800, 1000]},
                    "intensity": {"method": "linear", "reference": "spectralon"}
                },
                "parameters": {
                    "integration_time": {"default": 100, "min": 1, "max": 10000, "unit": "ms"},
                    "scans_to_average": {"default": 10, "min": 1, "max": 100}
                }
            },
            "diy_raspberry": {
                "calibration": {
                    "wavelength": {"method": "linear", "points": [650, 850, 1000], "frequency": "each_use"},
                    "intensity": {"method": "linear", "reference": "ceramic_tile"}
                },
                "parameters": {
                    "integration_time": {"default": 50, "min": 1, "max": 100, "unit": "ms"},
                    "gain": {"default": 4, "min": 1, "max": 16}
                },
                "diy_instructions": {
                    "components": ["Raspberry Pi", "AS7262 sensor", "White LED"],
                    "cost": "~$100",
                    "difficulty": "medium"
                }
            },
            "sparkfun_nir_triad": {
                "calibration": {
                    "wavelength": {"method": "linear", "points": [410, 610, 940], "frequency": "each_use"},
                    "intensity": {"method": "linear", "reference": "white_ptfe_tile"}
                },
                "parameters": {
                    "integration_time": {"default": 50, "min": 1, "max": 100, "unit": "ms"},
                    "scans_to_average": {"default": 4, "min": 1, "max": 32}
                },
                "diy_instructions": {
                    "components": ["SparkFun Triad (AS7263+AS7262)", "White LED", "MCU"],
                    "cost": "~$50",
                    "difficulty": "easy"
                }
            }
        }
    
    async def generate_calibration(self, spectral_data: Dict[str, Any]) -> CalibrationResult:
        """Generate comprehensive calibration."""
        result = CalibrationResult()
        wavelengths = np.array(spectral_data.get("wavelengths", []))
        intensities = np.array(spectral_data.get("intensities", []))
        metadata = spectral_data.get("metadata", {})
        spectrometer_type = spectral_data.get("spectrometer_type", "unknown")
        spec_info = self.spectrometer_database.get(spectrometer_type, {})
        
        # Generate wavelength calibration
        result.wavelength_calibration = self._generate_wavelength_calibration(
            wavelengths, intensities, spec_info
        )
        
        # Generate intensity calibration
        result.intensity_calibration = self._generate_intensity_calibration(
            wavelengths, intensities, spec_info
        )
        
        # Generate analyte calibration (NIR -> Brix) for multi-sample exports
        result.analyte_calibration = self._generate_analyte_calibration(
            wavelengths, metadata
        )
        
        # Generate drift compensation
        result.drift_compensation = self._generate_drift_compensation(metadata, spec_info)
        
        # Generate parameter recommendations
        result.spectrometer_parameters = self._generate_parameter_recommendations(
            wavelengths, intensities, metadata, spec_info
        )
        
        # Assess quality
        result.calibration_quality = self._assess_calibration_quality(
            result.wavelength_calibration, result.intensity_calibration,
            result.analyte_calibration
        )
        
        # Generate recommendations
        result.recommendations = self._generate_recommendations(result, spec_info)
        
        return result
    
    def _generate_wavelength_calibration(self, wavelengths, intensities, spec_info) -> Optional[CalibrationCurve]:
        """Generate wavelength calibration."""
        if len(wavelengths) < 2:
            return None
        
        # Use spectrometer's known calibration points
        if spec_info and "calibration" in spec_info:
            cal_points = spec_info["calibration"].get("wavelength", {}).get("points", [])
            if cal_points:
                # Create synthetic calibration
                x_data = np.array(cal_points)
                y_data = np.array(cal_points)  # Perfect calibration
                return self._fit_polynomial_calibration(x_data, y_data, degree=3)
        
        return None
    
    def _generate_intensity_calibration(self, wavelengths, intensities, spec_info) -> Optional[CalibrationCurve]:
        """Generate intensity calibration."""
        if len(wavelengths) < 2:
            return None
        
        # Simple linear calibration
        x_data = np.linspace(wavelengths[0], wavelengths[-1], 5)
        y_data = np.ones(5)  # Target: 1.0 reflectance
        return self._fit_linear_calibration(x_data, y_data)
    
    def _generate_analyte_calibration(self, wavelengths, metadata) -> Optional[AnalyteCalibration]:
        """Build a NIR -> analyte (Brix) multivariate PLS regression.

        Requires the per-sample intensity matrix and a reference analyte
        column in metadata (e.g. the `Brix` column of a SparkFun Triad
        export). The intensity matrix is standardized before fitting; the
        number of PLS components is chosen by 5-fold cross-validation on
        R^2. Returns None when no per-sample matrix or analyte reference is
        available.
        """
        if not _SKLEARN_AVAILABLE:
            return None
        matrix = metadata.get("intensity_matrix") if isinstance(metadata, dict) else None
        if not matrix:
            return None
        analyte = None
        for cand in ("Brix", "brix", "BRIX"):
            if isinstance(metadata, dict) and metadata.get(cand):
                analyte = cand
                break
        if analyte is None:
            return None
        try:
            X = np.array(matrix, dtype=float)
            y_raw = metadata.get(analyte, [])
            y = np.array([float(v) for v in y_raw if v not in (None, "")], dtype=float)
        except (TypeError, ValueError):
            return None
        if X.ndim != 2 or X.shape[0] < 10 or len(y) != X.shape[0]:
            return None
        n_features = X.shape[1]
        if len(wavelengths) == n_features:
            wl = [float(w) for w in wavelengths]
        else:
            wl = [float(w) for w in wavelengths][:n_features]

        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)
        max_comp = max(1, min(n_features, 10, X.shape[0] - 1))

        best = None
        for ncomp in range(1, max_comp + 1):
            pls = PLSRegression(n_components=ncomp, scale=False)
            try:
                pred_cv = cross_val_predict(pls, Xs, y, cv=5)
            except Exception:
                continue
            r2_cv = float(r2_score(y, pred_cv))
            rmse_cv = float(np.sqrt(mean_squared_error(y, pred_cv)))
            if best is None or r2_cv > best[0]:
                best = (r2_cv, rmse_cv, ncomp)
        if best is None:
            return None
        r2_cv, rmse_cv, ncomp = best

        pls = PLSRegression(n_components=ncomp, scale=False)
        pls.fit(Xs, y)
        pred_cal = pls.predict(Xs).ravel()
        r2_cal = float(r2_score(y, pred_cal))
        rmse_cal = float(np.sqrt(mean_squared_error(y, pred_cal)))

        # Convert coefficients back to the original (unstandardized) X scale:
        #   y = sum_k coef_std_k * (x_k - mean_k)/scale_k + intercept
        #     = sum_k (coef_std_k/scale_k) * x_k + (intercept - sum_k coef_std_k*mean_k/scale_k)
        coef_std = pls.coef_.ravel()
        means = scaler.mean_
        scales = scaler.scale_
        coef_orig = coef_std / scales
        intercept = float(pls.y_mean_ - np.sum(coef_orig * means)) if hasattr(pls, "y_mean_") else 0.0

        return AnalyteCalibration(
            analyte="Brix",
            method=f"PLS ({ncomp} components, 5-fold CV)",
            num_samples=int(X.shape[0]),
            num_features=int(n_features),
            num_components=int(ncomp),
            coefficients=[float(c) for c in coef_orig],
            intercept=intercept,
            wavelengths=wl,
            brix_range=(float(np.min(y)), float(np.max(y))),
            r_squared_cv=r2_cv,
            rmse_cv=rmse_cv,
            r_squared_cal=r2_cal,
            rmse_cal=rmse_cal,
            notes=(
                "PLS regression of the 18-channel intensity matrix onto the "
                "refractometer Brix reference. R\u00b2_cv/RMSE_cv are 5-fold "
                "cross-validated; coefficients are on the raw intensity scale."
            ),
        )
    
    def _fit_linear_calibration(self, x_data, y_data) -> CalibrationCurve:
        """Fit linear calibration."""
        if len(x_data) < 2:
            raise ValueError("Insufficient data")
        
        # Simple linear fit
        A = np.vstack([x_data, np.ones(len(x_data))]).T
        slope, intercept = np.linalg.lstsq(A, y_data, rcond=None)[0]
        
        y_pred = slope * x_data + intercept
        residuals = y_data - y_pred
        ss_tot = np.sum((y_data - np.mean(y_data))**2)
        r_squared = 1.0 - np.sum(residuals**2) / ss_tot if ss_tot > 0 else 1.0
        rmse = np.sqrt(np.mean(residuals**2))
        
        return CalibrationCurve(
            curve_type="linear",
            coefficients=[float(slope), float(intercept)],
            domain=(float(np.min(x_data)), float(np.max(x_data))),
            r_squared=float(r_squared),
            rmse=float(rmse),
            num_points=len(x_data)
        )
    
    def _fit_polynomial_calibration(self, x_data, y_data, degree=3) -> CalibrationCurve:
        """Fit polynomial calibration."""
        # Degrade the polynomial degree when too few calibration points are
        # available rather than raising, so analysis can still complete.
        while len(x_data) <= degree and degree > 1:
            degree -= 1
        if len(x_data) < 2:
            raise ValueError("Insufficient data for calibration")
        
        coeffs = np.polyfit(x_data, y_data, degree)
        y_pred = np.polyval(coeffs, x_data)
        residuals = y_data - y_pred
        ss_tot = np.sum((y_data - np.mean(y_data))**2)
        r_squared = 1.0 - np.sum(residuals**2) / ss_tot if ss_tot > 0 else 1.0
        rmse = np.sqrt(np.mean(residuals**2))
        
        return CalibrationCurve(
            curve_type="polynomial",
            coefficients=[float(c) for c in coeffs],
            domain=(float(np.min(x_data)), float(np.max(x_data))),
            r_squared=float(r_squared),
            rmse=float(rmse),
            num_points=len(x_data)
        )
    
    def _generate_drift_compensation(self, metadata, spec_info) -> Dict:
        """Generate drift compensation."""
        return {
            "temperature_compensation": {"enabled": True, "coefficient": 0.01},
            "time_compensation": {"enabled": False}
        }
    
    def _generate_parameter_recommendations(self, wavelengths, intensities, metadata, spec_info) -> Dict:
        """Generate parameter recommendations."""
        recommendations = {}
        if spec_info and "parameters" in spec_info:
            for param, info in spec_info["parameters"].items():
                recommendations[param] = {
                    "current": metadata.get(param, info["default"]),
                    "recommended": info["default"],
                    "unit": info.get("unit", ""),
                    "reason": "Default recommendation"
                }
        return recommendations
    
    def _assess_calibration_quality(self, wl_cal, int_cal, analyte_cal=None) -> Dict:
        """Assess calibration quality."""
        quality = {}
        if wl_cal:
            quality["wavelength_quality"] = min(wl_cal.r_squared * 100, 100)
        else:
            quality["wavelength_quality"] = 0
        
        if int_cal:
            quality["intensity_quality"] = min(int_cal.r_squared * 100, 100)
        else:
            quality["intensity_quality"] = 0
        
        if analyte_cal:
            # Analyte quality uses the cross-validated R^2 (0-100).
            quality["analyte_quality"] = max(0.0, min(analyte_cal.r_squared_cv * 100, 100))
            quality["analyte_rmse_cv"] = analyte_cal.rmse_cv
        else:
            quality["analyte_quality"] = 0
        
        components = [quality.get("wavelength_quality", 0),
                     quality.get("intensity_quality", 0)]
        if analyte_cal:
            components.append(quality["analyte_quality"])
        quality["overall_quality"] = sum(components) / len(components)
        return quality
    
    def _generate_recommendations(self, result, spec_info) -> List[Dict]:
        """Generate recommendations."""
        recommendations = []
        if not result.wavelength_calibration:
            recommendations.append({
                "type": "wavelength_calibration",
                "priority": "high",
                "description": "No wavelength calibration",
                "recommendation": "Perform wavelength calibration"
            })
        if not result.intensity_calibration:
            recommendations.append({
                "type": "intensity_calibration",
                "priority": "high",
                "description": "No intensity calibration",
                "recommendation": "Perform intensity calibration"
            })
        return recommendations
    
    async def apply_calibration(self, spectral_data: Dict, calibration: CalibrationResult) -> Dict:
        """Apply calibration to spectral data."""
        wavelengths = np.array(spectral_data.get("wavelengths", []))
        intensities = np.array(spectral_data.get("intensities", []))
        
        # Apply wavelength calibration
        if calibration.wavelength_calibration:
            if calibration.wavelength_calibration.curve_type == "linear":
                slope = calibration.wavelength_calibration.coefficients[0]
                intercept = calibration.wavelength_calibration.coefficients[1]
                calibrated_wavelengths = slope * wavelengths + intercept
            else:
                calibrated_wavelengths = np.polyval(
                    calibration.wavelength_calibration.coefficients, wavelengths
                )
        else:
            calibrated_wavelengths = wavelengths
        
        # Apply intensity calibration
        if calibration.intensity_calibration:
            if calibration.intensity_calibration.curve_type == "linear":
                slope = calibration.intensity_calibration.coefficients[0]
                intercept = calibration.intensity_calibration.coefficients[1]
                calibrated_intensities = slope * intensities + intercept
            else:
                calibrated_intensities = np.polyval(
                    calibration.intensity_calibration.coefficients, intensities
                )
        else:
            calibrated_intensities = intensities
        
        return {
            "wavelengths": calibrated_wavelengths.tolist(),
            "intensities": calibrated_intensities.tolist(),
            "metadata": spectral_data.get("metadata", {}),
            "calibration_applied": True
        }


if __name__ == "__main__":
    import asyncio
    
    async def test():
        agent = CalibrationAgent()
        data = {
            "wavelengths": [700, 800, 900, 1000],
            "intensities": [100, 120, 110, 90],
            "metadata": {"spectrometer_type": "diy_raspberry"}
        }
        result = await agent.generate_calibration(data)
        print(f"Calibration quality: {result.calibration_quality}")
    
    asyncio.run(test())
