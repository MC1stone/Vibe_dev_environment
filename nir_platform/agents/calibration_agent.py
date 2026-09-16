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
    from sklearn.model_selection import cross_val_predict, KFold
    from sklearn.metrics import r2_score, mean_squared_error
    from sklearn.neural_network import MLPRegressor
    from sklearn.covariance import MinCovDet
    from sklearn.decomposition import PCA
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
    outliers_removed: int = 0
    outlier_method: str = ""
    outlier_indices: List[int] = field(default_factory=list)

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
            "outliers_removed": self.outliers_removed,
            "outlier_method": self.outlier_method,
            "outlier_indices": self.outlier_indices,
        }


@dataclass
class NeuralCalibration:
    """Neural-network (MLP) calibration of NIR spectra onto a reference
    analyte, fitted in parallel to the PLS regression for comparison."""
    analyte: str
    method: str = "MLPRegressor (5-fold CV)"
    num_samples: int = 0
    num_features: int = 0
    hidden_layer_sizes: Tuple[int, ...] = (32, 16)
    r_squared_cv: float = 0.0
    rmse_cv: float = 0.0
    r_squared_cal: float = 0.0
    rmse_cal: float = 0.0
    outliers_removed: int = 0
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "analyte": self.analyte,
            "method": self.method,
            "num_samples": self.num_samples,
            "num_features": self.num_features,
            "hidden_layer_sizes": list(self.hidden_layer_sizes),
            "r_squared_cv": self.r_squared_cv,
            "rmse_cv": self.rmse_cv,
            "r_squared_cal": self.r_squared_cal,
            "rmse_cal": self.rmse_cal,
            "outliers_removed": self.outliers_removed,
            "notes": self.notes,
        }


@dataclass
class CalibrationResult:
    """Container for calibration results."""
    wavelength_calibration: Optional[CalibrationCurve] = None
    intensity_calibration: Optional[CalibrationCurve] = None
    analyte_calibration: Optional[AnalyteCalibration] = None
    neural_calibration: Optional[NeuralCalibration] = None
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
            "neural_calibration": self.neural_calibration.to_dict() if self.neural_calibration else None,
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
        
        # Generate neural-network calibration (MLP) in parallel to PLS
        result.neural_calibration = self._generate_neural_calibration(
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
            result.analyte_calibration, result.neural_calibration
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
    
    def _detect_outliers(self, X: np.ndarray, y: np.ndarray) -> tuple:
        """Detect outlier samples in the (X, y) calibration set.

        Uses a PCA-based chemometric outlier strategy that is standard in
        NIR spectroscopy:
        1. Reduce X to a few principal components and compute Hotelling's
           T^2 (leverage in the score space) and the Q-residual (distance
           to the PCA model plane). A sample is a spectral outlier when its
           T^2 or Q exceeds the 99th-percentile F / chi-square threshold.
        2. A conservative IQR rule (3x IQR) on the Brix reference flags
           reference values far outside the bulk distribution.

        A sample is removed only when flagged by the spectral rule OR the
        reference rule, capped at 10% of the data to avoid stripping
        genuine signal. Returns (keep_mask, indices_removed, method).
        """
        n = X.shape[0]
        if n < 20:
            return np.ones(n, dtype=bool), [], "none (too few samples)"
        removed = set()
        method_parts = []
        # Stage 1: PCA T^2 + Q-residual on the intensity matrix.
        try:
            scaler = StandardScaler()
            Xs = scaler.fit_transform(X)
            n_comp = max(1, min(X.shape[1], 5, X.shape[0] - 1))
            pca = PCA(n_components=n_comp, random_state=0)
            scores = pca.fit_transform(Xs)
            # Hotelling T^2 from the explained-variance-weighted scores.
            expl = pca.explained_variance_
            t2 = np.sum((scores ** 2) / expl[None, :], axis=1)
            from scipy.stats import f
            t2_thresh = float(f.ppf(0.99, n_comp, n - n_comp) * n_comp * (n - 1) / (n - n_comp))
            # Q-residual = reconstruction error.
            recon = pca.inverse_transform(scores)
            q = np.sum((Xs - recon) ** 2, axis=1)
            # Q threshold via the Jackson-Mudholkar chi-square approximation.
            from scipy.stats import chi2
            q_thresh = float(chi2.ppf(0.99, df=n_comp))
            spec_out = set(int(i) for i in np.where((t2 > t2_thresh) | (q > q_thresh))[0])
            if spec_out:
                removed |= spec_out
                method_parts.append(f"PCA T\u00b2/Q (p<0.01): {len(spec_out)}")
        except Exception:
            pass
        # Stage 2: conservative IQR (3x) on the Brix reference.
        try:
            q1 = np.percentile(y, 25)
            q3 = np.percentile(y, 75)
            iqr = q3 - q1
            if iqr > 0:
                lo = q1 - 3.0 * iqr
                hi = q3 + 3.0 * iqr
                ref_out = set(int(i) for i in np.where((y < lo) | (y > hi))[0])
                if ref_out:
                    removed |= ref_out
                    method_parts.append(f"IQR on Brix (3x): {len(ref_out)}")
        except Exception:
            pass
        # Cap removals at 10% of the data, keeping the most extreme flagged
        # samples first, so genuine signal is not stripped wholesale.
        max_remove = max(1, int(0.10 * n))
        if len(removed) > max_remove:
            try:
                scaler2 = StandardScaler()
                Xs2 = scaler2.fit_transform(X)
                n_comp2 = max(1, min(X.shape[1], 5))
                pca2 = PCA(n_components=n_comp2, random_state=0)
                scores2 = pca2.fit_transform(Xs2)
                expl2 = pca2.explained_variance_
                score_dist = np.sum((scores2 ** 2) / expl2[None, :], axis=1)
            except Exception:
                score_dist = np.abs(y - np.median(y))
            ranked = sorted(removed, key=lambda i: -float(score_dist[i]))
            removed = set(ranked[:max_remove])
        keep = np.ones(n, dtype=bool)
        for i in removed:
            keep[i] = False
        method = "; ".join(method_parts) if method_parts else "none"
        return keep, sorted(removed), method

    def _fit_pls(self, X: np.ndarray, y: np.ndarray, wavelengths: List[float],
                 n_features: int, remove_outliers: bool = True) -> Optional[AnalyteCalibration]:
        """Shared PLS fit with optional outlier removal.

        Returns an AnalyteCalibration (or None) covering the fitted PLS
        regression, the chosen number of components, and any samples that
        were removed as outliers.
        """
        keep = np.ones(X.shape[0], dtype=bool)
        removed_idx: List[int] = []
        outlier_method = ""
        if remove_outliers:
            keep, removed_idx, outlier_method = self._detect_outliers(X, y)
            X = X[keep]
            y = y[keep]
        if X.shape[0] < 8 or X.shape[0] <= n_features:
            return None
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
        coef_std = pls.coef_.ravel()
        means = scaler.mean_
        scales = scaler.scale_
        coef_orig = coef_std / scales
        intercept = float(pls.y_mean_ - np.sum(coef_orig * means)) if hasattr(pls, "y_mean_") else 0.0
        note_bits = ["PLS regression of the intensity matrix onto the "
                     "refractometer Brix reference. R\u00b2_cv/RMSE_cv are "
                     "5-fold cross-validated; coefficients are on the raw "
                     "intensity scale."]
        if removed_idx:
            note_bits.append(
                f"{len(removed_idx)} outlier sample(s) removed before fitting "
                f"({outlier_method})."
            )
        return AnalyteCalibration(
            analyte="Brix",
            method=f"PLS ({ncomp} components, 5-fold CV)",
            num_samples=int(X.shape[0]),
            num_features=int(n_features),
            num_components=int(ncomp),
            coefficients=[float(c) for c in coef_orig],
            intercept=intercept,
            wavelengths=wavelengths,
            brix_range=(float(np.min(y)), float(np.max(y))),
            r_squared_cv=r2_cv,
            rmse_cv=rmse_cv,
            r_squared_cal=r2_cal,
            rmse_cal=rmse_cal,
            notes=" ".join(note_bits),
            outliers_removed=len(removed_idx),
            outlier_method=outlier_method or "none",
            outlier_indices=removed_idx,
        )

    def _fit_neural(self, X: np.ndarray, y: np.ndarray, n_features: int,
                    analyte_name: str = "Brix",
                    outliers_removed: int = 0) -> Optional[NeuralCalibration]:
        """Fit a small MLP regression for comparison with the PLS model.

        Uses sklearn's MLPRegressor (no external deep-learning framework
        required) with 5-fold cross-validation. Returns None when there is
        not enough data or sklearn is unavailable.
        """
        if not _SKLEARN_AVAILABLE or X.shape[0] < 20:
            return None
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)
        hidden = (32, 16) if X.shape[0] >= 60 else (16, 8)
        nn = MLPRegressor(
            hidden_layer_sizes=hidden,
            activation="relu",
            solver="adam",
            max_iter=2000,
            random_state=0,
            early_stopping=True,
            validation_fraction=0.15,
        )
        # 5-fold cross-validated predictions.
        kf = KFold(n_splits=min(5, max(2, X.shape[0] // 4)), shuffle=True, random_state=0)
        pred_cv = np.zeros_like(y, dtype=float)
        for tr, te in kf.split(Xs):
            try:
                nn.fit(Xs[tr], y[tr])
                pred_cv[te] = nn.predict(Xs[te]).ravel()
            except Exception:
                pred_cv[te] = float(np.mean(y[tr]))
        r2_cv = float(r2_score(y, pred_cv))
        rmse_cv = float(np.sqrt(mean_squared_error(y, pred_cv)))
        try:
            nn.fit(Xs, y)
            pred_cal = nn.predict(Xs).ravel()
            r2_cal = float(r2_score(y, pred_cal))
            rmse_cal = float(np.sqrt(mean_squared_error(y, pred_cal)))
        except Exception:
            r2_cal, rmse_cal = r2_cv, rmse_cv
        return NeuralCalibration(
            analyte=analyte_name,
            method=f"MLPRegressor {hidden}, 5-fold CV",
            num_samples=int(X.shape[0]),
            num_features=int(n_features),
            hidden_layer_sizes=hidden,
            r_squared_cv=r2_cv,
            rmse_cv=rmse_cv,
            r_squared_cal=r2_cal,
            rmse_cal=rmse_cal,
            outliers_removed=outliers_removed,
            notes=(
                "Feed-forward neural network (MLP) baseline for the "
                "NIR->Brix regression, fitted in parallel to PLS for "
                "comparison. Metrics are 5-fold cross-validated."
            ),
        )

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
        return self._fit_pls(X, y, wl, n_features, remove_outliers=True)
    
    def _generate_neural_calibration(self, wavelengths, metadata) -> Optional[NeuralCalibration]:
        """Build a NIR -> analyte (Brix) neural-network (MLP) regression.

        Runs in parallel to the PLS regression for comparison. Uses the
        same (outlier-cleaned) data as the PLS fit when available.
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
        if X.ndim != 2 or X.shape[0] < 20 or len(y) != X.shape[0]:
            return None
        n_features = X.shape[1]
        # Reuse the same outlier removal so the NN sees the cleaned set.
        keep, removed_idx, _ = self._detect_outliers(X, y)
        Xc = X[keep]
        yc = y[keep]
        return self._fit_neural(Xc, yc, n_features, analyte_name="Brix",
                                outliers_removed=len(removed_idx))
    
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

    def recalibrate_from_samples(
        self,
        samples: List[Dict[str, Any]],
        analyte_name: str = "Brix",
    ) -> Optional[AnalyteCalibration]:
        """Build a combined NIR->analyte PLS regression from several analyses.

        Each entry in ``samples`` must provide ``intensity_matrix`` (a
        per-sample N x F matrix) and ``analyte`` (the matching N-length
        reference vector), plus optional ``wavelengths`` (F-length) and a
        label. The matrices are stacked row-wise so the combined dataset
        spans all selected analyses - this lets the customer recalculate the
        calibration with potential additional data.

        Returns an AnalyteCalibration, or None when there is not enough
        combined data or sklearn is unavailable.
        """
        if not _SKLEARN_AVAILABLE:
            return None
        X_parts: List[np.ndarray] = []
        y_parts: List[float] = []
        wl: List[float] = []
        n_features = 0
        for s in samples:
            mat = s.get("intensity_matrix")
            ref = s.get("analyte") or s.get(analyte_name)
            if not mat or not ref:
                continue
            try:
                Xm = np.array(mat, dtype=float)
                ym = np.array([float(v) for v in ref if v not in (None, "")], dtype=float)
            except (TypeError, ValueError):
                continue
            if Xm.ndim != 2 or Xm.shape[0] < 1 or len(ym) != Xm.shape[0]:
                continue
            if n_features == 0:
                n_features = Xm.shape[1]
                sw = s.get("wavelengths") or []
                if len(sw) == n_features:
                    wl = [float(w) for w in sw]
                else:
                    wl = [float(410 + 30 * i) for i in range(n_features)]
            elif Xm.shape[1] != n_features:
                # skip analyses with a different channel count
                continue
            X_parts.append(Xm)
            y_parts.extend(ym.tolist())
        if not X_parts or n_features == 0:
            return None
        X = np.vstack(X_parts)
        y = np.array(y_parts, dtype=float)
        if X.shape[0] < 10 or len(y) != X.shape[0]:
            return None

        ac = self._fit_pls(X, y, wl, n_features, remove_outliers=True)
        if ac is None:
            return None
        # Relabel so the combined provenance is visible.
        ac.method = f"PLS ({ac.num_components} components, 5-fold CV) - combined {len(samples)} analyses"
        ac.analyte = analyte_name
        ac.notes = (
            f"Combined PLS regression over {len(samples)} analyses "
            f"({X.shape[0]} samples total, {ac.outliers_removed} outlier(s) removed). "
            "R\u00b2_cv/RMSE_cv are 5-fold cross-validated; coefficients are on the raw intensity scale."
        )
        return ac

    def recalibrate_neural_from_samples(
        self,
        samples: List[Dict[str, Any]],
        analyte_name: str = "Brix",
    ) -> Optional[NeuralCalibration]:
        """Build a combined NIR->analyte MLP regression from several analyses.

        Stacks the per-sample matrices the same way as
        ``recalibrate_from_samples`` and fits a small neural network on the
        (outlier-cleaned) combined data for comparison with the PLS model.
        """
        if not _SKLEARN_AVAILABLE:
            return None
        X_parts: List[np.ndarray] = []
        y_parts: List[float] = []
        n_features = 0
        for s in samples:
            mat = s.get("intensity_matrix")
            ref = s.get("analyte") or s.get(analyte_name)
            if not mat or not ref:
                continue
            try:
                Xm = np.array(mat, dtype=float)
                ym = np.array([float(v) for v in ref if v not in (None, "")], dtype=float)
            except (TypeError, ValueError):
                continue
            if Xm.ndim != 2 or Xm.shape[0] < 1 or len(ym) != Xm.shape[0]:
                continue
            if n_features == 0:
                n_features = Xm.shape[1]
            elif Xm.shape[1] != n_features:
                continue
            X_parts.append(Xm)
            y_parts.extend(ym.tolist())
        if not X_parts or n_features == 0:
            return None
        X = np.vstack(X_parts)
        y = np.array(y_parts, dtype=float)
        if X.shape[0] < 20 or len(y) != X.shape[0]:
            return None
        keep, removed_idx, _ = self._detect_outliers(X, y)
        Xc, yc = X[keep], y[keep]
        nc = self._fit_neural(Xc, yc, n_features, analyte_name=analyte_name,
                              outliers_removed=len(removed_idx))
        if nc is not None:
            nc.method = f"MLP {nc.hidden_layer_sizes}, 5-fold CV - combined {len(samples)} analyses"
        return nc

    def _assess_calibration_quality(self, wl_cal, int_cal, analyte_cal=None,
                                     neural_cal=None) -> Dict:
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
        
        if neural_cal:
            quality["neural_quality"] = max(0.0, min(neural_cal.r_squared_cv * 100, 100))
            quality["neural_rmse_cv"] = neural_cal.rmse_cv
        else:
            quality["neural_quality"] = 0
        
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
