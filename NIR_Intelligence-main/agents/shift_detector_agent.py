#!/usr/bin/env python3
"""
NIR Intelligence Platform - ShiftDetectorAgent
Agent for detecting and analyzing wavelength shifts, intensity drifts, and other spectrometer issues
"""

import logging
import json
import tempfile
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
from scipy import signal, fft, stats, interpolate
from scipy.optimize import curve_fit
from scipy.spatial.distance import euclidean
from sklearn.preprocessing import StandardScaler
from .base_agent import BaseAgent, AgentOutput, AgentStatus, ErrorSeverity, AgentError


@dataclass
class ShiftDetectionMethod:
    """Configuration for shift detection methods"""
    name: str
    description: str
    threshold: float = 0.0
    confidence_weight: float = 1.0
    enabled: bool = True


@dataclass
class SpectralShiftResult:
    """Result of spectral shift detection"""
    shift_type: str  # 'wavelength', 'intensity', 'baseline', 'phase'
    shift_value: float  # in nm or percentage
    confidence: float  # 0-1
    detection_method: str
    affected_range: Tuple[float, float] = (0.0, 0.0)
    severity: str = "low"  # 'low', 'medium', 'high', 'critical'
    correction_suggestion: Optional[str] = None
    quality_impact: float = 0.0  # Impact on data quality (0-100)


@dataclass
class IntensityDriftResult:
    """Result of intensity drift detection"""
    drift_type: str  # 'linear', 'exponential', 'random'
    drift_value: float  # percentage change
    confidence: float  # 0-1
    detection_method: str
    affected_wavelengths: List[float] = field(default_factory=list)
    severity: str = "low"
    correction_suggestion: Optional[str] = None


@dataclass
class BaselineAnalysisResult:
    """Result of baseline analysis"""
    baseline_type: str  # 'flat', 'curved', 'drifted', 'noisy'
    baseline_offset: float = 0.0
    baseline_slope: float = 0.0
    confidence: float = 0.0
    detection_method: str = ""
    severity: str = "low"
    correction_suggestion: Optional[str] = None


@dataclass
class SpectrometerIssue:
    """Comprehensive spectrometer issue detection result"""
    issue_type: str
    description: str
    severity: str = "low"  # 'low', 'medium', 'high', 'critical'
    confidence: float = 0.0  # 0-1
    detection_method: str = ""
    affected_data: Dict[str, Any] = field(default_factory=dict)
    correction_recommendation: str = ""
    quality_impact: float = 0.0  # 0-100


@dataclass
class ShiftDetectionReport:
    """Comprehensive shift detection report"""
    sample_id: str
    timestamp: str
    wavelength_range: Tuple[float, float]
    data_points: int
    
    # Shift detection results
    wavelength_shifts: List[SpectralShiftResult] = field(default_factory=list)
    intensity_drifts: List[IntensityDriftResult] = field(default_factory=list)
    baseline_issues: List[BaselineAnalysisResult] = field(default_factory=list)
    other_issues: List[SpectrometerIssue] = field(default_factory=list)
    
    # Overall assessment
    overall_shift_detected: bool = False
    overall_shift_value: float = 0.0
    overall_confidence: float = 0.0
    overall_severity: str = "low"
    
    # Quality metrics
    quality_score: float = 100.0  # 0-100
    quality_grade: str = "excellent"
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    calibration_required: bool = False
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class ShiftDetectorAgent(BaseAgent):
    """
    Agent for detecting and analyzing wavelength shifts, intensity drifts, and other spectrometer issues
    
    Features:
    - Wavelength shift detection using multiple methods (FFT correlation, peak matching, derivative analysis)
    - Intensity drift detection (linear, exponential, random patterns)
    - Baseline analysis and correction recommendations
    - Multi-reference comparison for calibration verification
    - Statistical analysis of spectral consistency
    - Quality impact assessment
    - Comprehensive reporting and recommendations
    """
    
    def __init__(self, **kwargs):
        super().__init__(name="ShiftDetectorAgent", version="2.0.0", **kwargs)
        self.dependencies = ['numpy', 'pandas', 'scipy', 'scikit-learn']
        self.logger = logging.getLogger(f"Agent.ShiftDetectorAgent")
        
        # Configuration
        self.wavelength_range = kwargs.get('wavelength_range', (700, 2500))  # nm
        self.min_data_points = kwargs.get('min_data_points', 50)
        self.shift_threshold = kwargs.get('shift_threshold', 0.5)  # nm - minimum detectable shift
        self.drift_threshold = kwargs.get('drift_threshold', 0.01)  # percentage - minimum detectable drift
        self.confidence_threshold = kwargs.get('confidence_threshold', 0.7)  # minimum confidence for reporting
        
        # Detection methods configuration
        self.detection_methods = {
            'fft_correlation': ShiftDetectionMethod(
                name="FFT Correlation",
                description="Detects wavelength shifts using FFT-based cross-correlation",
                threshold=0.1,
                confidence_weight=1.2,
                enabled=True
            ),
            'peak_matching': ShiftDetectionMethod(
                name="Peak Matching",
                description="Detects shifts by matching spectral peaks with reference",
                threshold=0.5,
                confidence_weight=1.1,
                enabled=True
            ),
            'derivative_analysis': ShiftDetectionMethod(
                name="Derivative Analysis",
                description="Detects shifts using first and second derivative analysis",
                threshold=0.3,
                confidence_weight=0.9,
                enabled=True
            ),
            'cross_correlation': ShiftDetectionMethod(
                name="Cross-Correlation",
                description="Direct cross-correlation of spectral data",
                threshold=0.2,
                confidence_weight=1.0,
                enabled=True
            ),
            'statistical_analysis': ShiftDetectionMethod(
                name="Statistical Analysis",
                description="Statistical comparison with reference data",
                threshold=0.15,
                confidence_weight=0.8,
                enabled=True
            )
        }
        
        # Reference data
        self.reference_spectra = kwargs.get('reference_spectra', {})
        self.standard_wavelengths = kwargs.get('standard_wavelengths', None)
        self.calibration_data = kwargs.get('calibration_data', {})
        
        # Processing configuration
        self.processing_config = kwargs.get('processing', {
            'smoothing_window': 5,
            'baseline_correction': True,
            'noise_filtering': True,
            'normalize_before_analysis': True,
            'use_derivatives': True,
            'min_peak_height': 0.1,
            'max_peaks': 10
        })
        
        # Initialize agent-specific attributes
        self._initialize_attributes()
        
        self.logger.info(f"ShiftDetectorAgent initialized with wavelength range: {self.wavelength_range}")
    
    def _initialize_attributes(self):
        """Initialize agent-specific attributes"""
        self.detection_results: Dict[str, ShiftDetectionReport] = {}
        self.stats = {
            'analyses_performed': 0,
            'shifts_detected': 0,
            'drifts_detected': 0,
            'baseline_issues_detected': 0,
            'processing_time': 0.0,
            'errors': 0
        }
        
        # Load reference data
        self._load_reference_data()
    
    def _load_reference_data(self):
        """Load reference spectral data for comparison"""
        try:
            reference_files = [
                Path("data/reference_spectra.json"),
                Path("data/calibration_data.json"),
                Path("nir_test_env/reference_spectra.json"),
                Path("config/calibration.json")
            ]
            
            for ref_file in reference_files:
                if ref_file.exists():
                    with open(ref_file, "r") as f:
                        data = json.load(f)
                        if 'reference_spectra' in data:
                            self.reference_spectra = data['reference_spectra']
                        if 'calibration_data' in data:
                            self.calibration_data = data['calibration_data']
                        if 'standard_wavelengths' in data:
                            self.standard_wavelengths = np.array(data['standard_wavelengths'])
                    self.logger.info(f"Loaded reference data from {ref_file}")
                    break
                    
            # If no reference data found, create default standard wavelengths
            if self.standard_wavelengths is None:
                self.standard_wavelengths = np.linspace(
                    self.wavelength_range[0], 
                    self.wavelength_range[1], 
                    1000
                )
                
        except Exception as e:
            self.logger.warning(f"Could not load reference data: {e}")
    
    def initialize(self) -> AgentOutput:
        """Initialize the shift detector agent"""
        self.status = AgentStatus.READY
        self.logger.info("ShiftDetectorAgent initialized and ready for shift detection")
        
        return AgentOutput(
            agent_name=self.name,
            status=self.status,
            version=self.version,
            dependencies=self.dependencies,
            data={
                "wavelength_range": self.wavelength_range,
                "min_data_points": self.min_data_points,
                "shift_threshold": self.shift_threshold,
                "drift_threshold": self.drift_threshold,
                "detection_methods": {k: v.name for k, v in self.detection_methods.items()},
                "processing_config": self.processing_config,
                "reference_spectra_count": len(self.reference_spectra),
                "calibration_data_available": bool(self.calibration_data)
            }
        )
    
    def validate_spectral_data(self, spectral_data: Dict[str, Any]) -> List[str]:
        """Validate spectral data structure and content"""
        errors = []
        
        # Check required fields
        required_fields = ["wavelengths", "intensities", "sample_id"]
        for field in required_fields:
            if field not in spectral_data:
                errors.append(f"Missing required field: {field}")
        
        # Check data types and shapes
        if "wavelengths" in spectral_data and "intensities" in spectral_data:
            wavelengths = spectral_data["wavelengths"]
            intensities = spectral_data["intensities"]
            
            if len(wavelengths) != len(intensities):
                errors.append("Wavelengths and intensities arrays must have the same length")
            
            if len(wavelengths) < self.min_data_points:
                errors.append(f"Insufficient data points: {len(wavelengths)} < {self.min_data_points}")
                
            # Check wavelength range
            if wavelengths:
                min_wl = min(wavelengths)
                max_wl = max(wavelengths)
                if min_wl < self.wavelength_range[0] or max_wl > self.wavelength_range[1]:
                    errors.append(f"Wavelengths outside expected range {self.wavelength_range}")
        
        return errors
    
    def preprocess_spectral_data(self, wavelengths: np.ndarray, intensities: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Preprocess spectral data for shift detection"""
        try:
            config = self.processing_config
            
            # Convert to numpy arrays if not already
            wavelengths = np.array(wavelengths, dtype=float)
            intensities = np.array(intensities, dtype=float)
            
            # Smoothing
            if config.get('smoothing_window', 0) > 1:
                window_size = config['smoothing_window']
                if window_size < len(intensities):
                    series = pd.Series(intensities).rolling(window=window_size, center=True).mean()
                    intensities = series.fillna(series.bfill()).fillna(series.ffill()).values
            
            # Baseline correction
            if config.get('baseline_correction', False):
                intensities = self._correct_baseline(wavelengths, intensities)
            
            # Noise filtering
            if config.get('noise_filtering', False):
                intensities = self._filter_noise(intensities)
            
            # Normalization
            if config.get('normalize_before_analysis', False):
                if np.max(intensities) > 0:
                    intensities = intensities / np.max(intensities)
                    
            return wavelengths, intensities
            
        except Exception as e:
            self.logger.error(f"Error preprocessing spectral data: {e}")
            return wavelengths, intensities
    
    def _correct_baseline(self, wavelengths: np.ndarray, intensities: np.ndarray) -> np.ndarray:
        """Correct baseline using polynomial fitting"""
        try:
            # Use simple linear baseline correction
            x = np.arange(len(intensities))
            baseline = np.polyfit(x, intensities, 1)[0] * x + np.polyfit(x, intensities, 1)[1]
            return intensities - baseline
        except Exception as e:
            self.logger.warning(f"Baseline correction failed: {e}")
            return intensities
    
    def _filter_noise(self, intensities: np.ndarray) -> np.ndarray:
        """Apply noise filtering to spectral data"""
        try:
            # Simple moving average filter
            window_size = min(3, len(intensities) // 10)
            if window_size > 1:
                series = pd.Series(intensities).rolling(window=window_size, center=True).mean()
                return series.fillna(series.bfill()).fillna(series.ffill()).values
            return intensities
        except Exception as e:
            self.logger.warning(f"Noise filtering failed: {e}")
            return intensities
    
    def detect_wavelength_shift_fft(self, wavelengths: np.ndarray, intensities: np.ndarray, 
                                   reference_wavelengths: np.ndarray, reference_intensities: np.ndarray) -> Optional[SpectralShiftResult]:
        """Detect wavelength shift using FFT-based cross-correlation"""
        try:
            # Interpolate both spectra to common wavelength grid
            common_wavelengths = np.linspace(
                max(wavelengths.min(), reference_wavelengths.min()),
                min(wavelengths.max(), reference_wavelengths.max()),
                1000
            )
            
            # Interpolate intensities
            interp_func = interpolate.interp1d(wavelengths, intensities, bounds_error=False, fill_value=0)
            interp_ref_func = interpolate.interp1d(reference_wavelengths, reference_intensities, bounds_error=False, fill_value=0)
            
            test_intensities = interp_func(common_wavelengths)
            ref_intensities = interp_ref_func(common_wavelengths)
            
            # Normalize
            test_intensities = (test_intensities - np.mean(test_intensities)) / np.std(test_intensities)
            ref_intensities = (ref_intensities - np.mean(ref_intensities)) / np.std(ref_intensities)
            
            # Compute FFT
            test_fft = fft.fft(test_intensities)
            ref_fft = fft.fft(ref_intensities)
            
            # Cross-correlation in frequency domain
            cross_corr = fft.ifft(test_fft * np.conj(ref_fft))
            
            # Find peak in cross-correlation
            peak_idx = np.argmax(np.abs(cross_corr))
            
            # Calculate shift (convert index to wavelength shift)
            wavelength_spacing = common_wavelengths[1] - common_wavelengths[0]
            shift_nm = (peak_idx - len(cross_corr) // 2) * wavelength_spacing
            
            # Calculate confidence based on peak sharpness
            peak_magnitude = np.abs(cross_corr[peak_idx])
            mean_magnitude = np.mean(np.abs(cross_corr))
            confidence = min(1.0, peak_magnitude / (mean_magnitude + 1e-10))
            
            if abs(shift_nm) > self.shift_threshold and confidence > self.confidence_threshold:
                severity = self._get_severity_from_shift(abs(shift_nm))
                return SpectralShiftResult(
                    shift_type="wavelength",
                    shift_value=shift_nm,
                    confidence=confidence,
                    detection_method="fft_correlation",
                    affected_range=(common_wavelengths[0], common_wavelengths[-1]),
                    severity=severity,
                    correction_suggestion=f"Recalibrate spectrometer: shift of {shift_nm:.2f} nm detected",
                    quality_impact=min(100, abs(shift_nm) * 10)  # 10% quality impact per nm shift
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"FFT shift detection failed: {e}")
            return None
    
    def detect_wavelength_shift_peak_matching(self, wavelengths: np.ndarray, intensities: np.ndarray,
                                             reference_wavelengths: np.ndarray, reference_intensities: np.ndarray) -> Optional[SpectralShiftResult]:
        """Detect wavelength shift by matching spectral peaks"""
        try:
            # Find peaks in test spectrum
            test_peaks, test_properties = signal.find_peaks(
                intensities, 
                height=self.processing_config.get('min_peak_height', 0.1),
                distance=5,
                prominence=0.05
            )
            
            # Find peaks in reference spectrum
            ref_peaks, ref_properties = signal.find_peaks(
                reference_intensities,
                height=self.processing_config.get('min_peak_height', 0.1),
                distance=5,
                prominence=0.05
            )
            
            if len(test_peaks) < 2 or len(ref_peaks) < 2:
                return None
            
            # Limit number of peaks
            max_peaks = self.processing_config.get('max_peaks', 10)
            test_peaks = test_peaks[:max_peaks]
            ref_peaks = ref_peaks[:max_peaks]
            
            # Calculate shifts for each peak pair
            shifts = []
            for test_peak in test_peaks:
                for ref_peak in ref_peaks:
                    # Find closest reference peak
                    shift_nm = wavelengths[test_peak] - reference_wavelengths[ref_peak]
                    shifts.append(shift_nm)
            
            if not shifts:
                return None
                
            # Calculate average shift
            avg_shift = np.mean(shifts)
            std_shift = np.std(shifts)
            
            # Confidence based on consistency of shifts
            confidence = 1.0 / (1.0 + std_shift / (abs(avg_shift) + 1e-10))
            
            if abs(avg_shift) > self.shift_threshold and confidence > self.confidence_threshold:
                severity = self._get_severity_from_shift(abs(avg_shift))
                return SpectralShiftResult(
                    shift_type="wavelength",
                    shift_value=avg_shift,
                    confidence=confidence,
                    detection_method="peak_matching",
                    affected_range=(wavelengths[0], wavelengths[-1]),
                    severity=severity,
                    correction_suggestion=f"Check wavelength calibration: average peak shift of {avg_shift:.2f} nm",
                    quality_impact=min(100, abs(avg_shift) * 8)
                )
                
            return None
            
        except Exception as e:
            self.logger.error(f"Peak matching shift detection failed: {e}")
            return None
    
    def detect_wavelength_shift_derivative(self, wavelengths: np.ndarray, intensities: np.ndarray,
                                          reference_wavelengths: np.ndarray, reference_intensities: np.ndarray) -> Optional[SpectralShiftResult]:
        """Detect wavelength shift using derivative analysis"""
        try:
            # Calculate first derivatives
            test_deriv = np.gradient(intensities, wavelengths)
            ref_deriv = np.gradient(reference_intensities, reference_wavelengths)
            
            # Find zero crossings (peaks) in derivatives
            test_zero_crossings = np.where(np.diff(np.sign(test_deriv)))[0]
            ref_zero_crossings = np.where(np.diff(np.sign(ref_deriv)))[0]
            
            if len(test_zero_crossings) < 2 or len(ref_zero_crossings) < 2:
                return None
            
            # Match zero crossings
            shifts = []
            for test_zc in test_zero_crossings:
                for ref_zc in ref_zero_crossings:
                    shift_nm = wavelengths[test_zc] - reference_wavelengths[ref_zc]
                    shifts.append(shift_nm)
            
            if not shifts:
                return None
                
            avg_shift = np.mean(shifts)
            std_shift = np.std(shifts)
            confidence = 1.0 / (1.0 + std_shift / (abs(avg_shift) + 1e-10))
            
            if abs(avg_shift) > self.shift_threshold and confidence > self.confidence_threshold:
                severity = self._get_severity_from_shift(abs(avg_shift))
                return SpectralShiftResult(
                    shift_type="wavelength",
                    shift_value=avg_shift,
                    confidence=confidence * 0.9,  # Slightly lower confidence for derivative method
                    detection_method="derivative_analysis",
                    affected_range=(wavelengths[0], wavelengths[-1]),
                    severity=severity,
                    correction_suggestion=f"Derivative analysis suggests wavelength shift of {avg_shift:.2f} nm",
                    quality_impact=min(100, abs(avg_shift) * 6)
                )
                
            return None
            
        except Exception as e:
            self.logger.error(f"Derivative shift detection failed: {e}")
            return None
    
    def detect_intensity_drift(self, wavelengths: np.ndarray, intensities: np.ndarray) -> List[IntensityDriftResult]:
        """Detect intensity drift patterns in spectral data"""
        results = []
        
        try:
            # Linear drift detection
            linear_drift = self._detect_linear_drift(wavelengths, intensities)
            if linear_drift:
                results.append(linear_drift)
            
            # Exponential drift detection
            exp_drift = self._detect_exponential_drift(wavelengths, intensities)
            if exp_drift:
                results.append(exp_drift)
            
            # Random drift detection
            random_drift = self._detect_random_drift(intensities)
            if random_drift:
                results.append(random_drift)
                
        except Exception as e:
            self.logger.error(f"Intensity drift detection failed: {e}")
            
        return results
    
    def _detect_linear_drift(self, wavelengths: np.ndarray, intensities: np.ndarray) -> Optional[IntensityDriftResult]:
        """Detect linear intensity drift"""
        try:
            # Fit linear trend
            slope, intercept, r_value, p_value, std_err = stats.linregress(wavelengths, intensities)
            
            # Calculate percentage change across wavelength range
            wl_range = wavelengths[-1] - wavelengths[0]
            intensity_change = slope * wl_range
            percentage_change = (intensity_change / (np.mean(intensities) + 1e-10)) * 100
            
            if abs(percentage_change) > self.drift_threshold * 100:  # Convert threshold to percentage
                confidence = abs(r_value)
                severity = self._get_severity_from_drift(abs(percentage_change))
                
                return IntensityDriftResult(
                    drift_type="linear",
                    drift_value=percentage_change,
                    confidence=confidence,
                    detection_method="linear_regression",
                    affected_wavelengths=[wavelengths[0], wavelengths[-1]],
                    severity=severity,
                    correction_suggestion=f"Apply intensity correction: linear drift of {percentage_change:.1f}% detected"
                )
                
            return None
            
        except Exception as e:
            self.logger.warning(f"Linear drift detection failed: {e}")
            return None
    
    def _detect_exponential_drift(self, wavelengths: np.ndarray, intensities: np.ndarray) -> Optional[IntensityDriftResult]:
        """Detect exponential intensity drift"""
        try:
            # Fit exponential trend: y = a * exp(b * x)
            # Ensure intensities are positive for log transform
            positive_intensities = np.maximum(intensities, 1e-10)
            log_intensities = np.log(positive_intensities)
            
            # Fit linear trend to log data
            slope, intercept, r_value, p_value, std_err = stats.linregress(wavelengths, log_intensities)
            
            # Calculate percentage change
            b = slope
            percentage_change = (np.exp(b * (wavelengths[-1] - wavelengths[0])) - 1) * 100
            
            if abs(percentage_change) > self.drift_threshold * 100:
                confidence = abs(r_value)
                severity = self._get_severity_from_drift(abs(percentage_change))
                
                return IntensityDriftResult(
                    drift_type="exponential",
                    drift_value=percentage_change,
                    confidence=confidence * 0.9,  # Slightly lower confidence
                    detection_method="exponential_regression",
                    affected_wavelengths=[wavelengths[0], wavelengths[-1]],
                    severity=severity,
                    correction_suggestion=f"Apply logarithmic correction: exponential drift of {percentage_change:.1f}% detected"
                )
                
            return None
            
        except Exception as e:
            self.logger.warning(f"Exponential drift detection failed: {e}")
            return None
    
    def _detect_random_drift(self, intensities: np.ndarray) -> Optional[IntensityDriftResult]:
        """Detect random intensity variations"""
        try:
            # Calculate coefficient of variation
            cv = np.std(intensities) / (np.mean(intensities) + 1e-10)
            
            # If CV is high, there might be random drift
            if cv > 0.15:  # 15% coefficient of variation threshold
                # Calculate percentage of points that deviate significantly
                mean_intensity = np.mean(intensities)
                std_intensity = np.std(intensities)
                outliers = np.sum(np.abs(intensities - mean_intensity) > 2 * std_intensity)
                outlier_percentage = (outliers / len(intensities)) * 100
                
                if outlier_percentage > 5:  # More than 5% outliers
                    confidence = min(1.0, outlier_percentage / 20.0)
                    severity = "high" if outlier_percentage > 15 else "medium"
                    
                    return IntensityDriftResult(
                        drift_type="random",
                        drift_value=outlier_percentage,
                        confidence=confidence,
                        detection_method="statistical_analysis",
                        severity=severity,
                        correction_suggestion=f"Investigate data quality: {outlier_percentage:.1f}% outlier points detected"
                    )
                    
            return None
            
        except Exception as e:
            self.logger.warning(f"Random drift detection failed: {e}")
            return None
    
    def analyze_baseline(self, wavelengths: np.ndarray, intensities: np.ndarray) -> List[BaselineAnalysisResult]:
        """Analyze baseline characteristics"""
        results = []
        
        try:
            # Flat baseline detection
            flat_result = self._analyze_flat_baseline(intensities)
            if flat_result:
                results.append(flat_result)
            
            # Curved baseline detection
            curved_result = self._analyze_curved_baseline(wavelengths, intensities)
            if curved_result:
                results.append(curved_result)
            
            # Drifted baseline detection
            drifted_result = self._analyze_drifted_baseline(wavelengths, intensities)
            if drifted_result:
                results.append(drifted_result)
                
        except Exception as e:
            self.logger.error(f"Baseline analysis failed: {e}")
            
        return results
    
    def _analyze_flat_baseline(self, intensities: np.ndarray) -> Optional[BaselineAnalysisResult]:
        """Analyze if baseline is flat"""
        try:
            # Calculate standard deviation of baseline (lowest 10% of intensities)
            sorted_intensities = np.sort(intensities)
            baseline_intensities = sorted_intensities[:len(sorted_intensities) // 10]
            baseline_std = np.std(baseline_intensities)
            
            if baseline_std < 0.01:  # Very flat baseline
                return BaselineAnalysisResult(
                    baseline_type="flat",
                    baseline_offset=float(np.mean(baseline_intensities)),
                    confidence=0.9,
                    detection_method="statistical_analysis",
                    severity="low",
                    correction_suggestion="Baseline appears flat and stable"
                )
                
            return None
            
        except Exception as e:
            self.logger.warning(f"Flat baseline analysis failed: {e}")
            return None
    
    def _analyze_curved_baseline(self, wavelengths: np.ndarray, intensities: np.ndarray) -> Optional[BaselineAnalysisResult]:
        """Analyze if baseline is curved"""
        try:
            # Fit quadratic polynomial to baseline
            sorted_indices = np.argsort(intensities)
            baseline_indices = sorted_indices[:len(sorted_indices) // 10]  # Lowest 10%
            baseline_wavelengths = wavelengths[baseline_indices]
            baseline_intensities = intensities[baseline_indices]
            
            # Fit quadratic: y = ax^2 + bx + c
            coeffs = np.polyfit(baseline_wavelengths, baseline_intensities, 2)
            a, b, c = coeffs
            
            # Calculate curvature
            curvature = abs(a)
            
            if curvature > 1e-6:  # Significant curvature
                confidence = min(1.0, curvature * 1e4)  # Scale for confidence
                severity = "medium" if curvature > 1e-5 else "low"
                
                return BaselineAnalysisResult(
                    baseline_type="curved",
                    baseline_offset=c,
                    baseline_slope=b,
                    confidence=confidence,
                    detection_method="polynomial_fitting",
                    severity=severity,
                    correction_suggestion=f"Apply baseline correction: curvature detected (a={a:.2e})"
                )
                
            return None
            
        except Exception as e:
            self.logger.warning(f"Curved baseline analysis failed: {e}")
            return None
    
    def _analyze_drifted_baseline(self, wavelengths: np.ndarray, intensities: np.ndarray) -> Optional[BaselineAnalysisResult]:
        """Analyze if baseline has drift"""
        try:
            # Fit linear trend to baseline
            sorted_indices = np.argsort(intensities)
            baseline_indices = sorted_indices[:len(sorted_indices) // 10]  # Lowest 10%
            baseline_wavelengths = wavelengths[baseline_indices]
            baseline_intensities = intensities[baseline_indices]
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(baseline_wavelengths, baseline_intensities)
            
            if abs(slope) > 1e-5:  # Significant slope
                confidence = abs(r_value)
                severity = "high" if abs(slope) > 1e-4 else "medium"
                
                return BaselineAnalysisResult(
                    baseline_type="drifted",
                    baseline_offset=intercept,
                    baseline_slope=slope,
                    confidence=confidence,
                    detection_method="linear_regression",
                    severity=severity,
                    correction_suggestion=f"Apply baseline correction: drift of {slope:.2e} per nm detected"
                )
                
            return None
            
        except Exception as e:
            self.logger.warning(f"Drifted baseline analysis failed: {e}")
            return None
    
    def _get_severity_from_shift(self, shift_nm: float) -> str:
        """Determine severity based on shift magnitude"""
        if shift_nm >= 5.0:
            return "critical"
        elif shift_nm >= 2.0:
            return "high"
        elif shift_nm >= 1.0:
            return "medium"
        else:
            return "low"
    
    def _get_severity_from_drift(self, drift_percentage: float) -> str:
        """Determine severity based on drift percentage"""
        if drift_percentage >= 20:
            return "critical"
        elif drift_percentage >= 10:
            return "high"
        elif drift_percentage >= 5:
            return "medium"
        else:
            return "low"
    
    def _calculate_overall_assessment(self, shifts: List[SpectralShiftResult], 
                                     drifts: List[IntensityDriftResult],
                                     baseline_issues: List[BaselineAnalysisResult]) -> Tuple[bool, float, str]:
        """Calculate overall assessment from individual detections"""
        all_detections = shifts + drifts + baseline_issues
        
        if not all_detections:
            return False, 0.0, "low"
        
        # Calculate weighted average shift/drift
        total_shift = 0.0
        total_weight = 0.0
        max_severity = "low"
        
        for detection in all_detections:
            if hasattr(detection, 'shift_value'):
                total_shift += abs(detection.shift_value) * detection.confidence
                total_weight += detection.confidence
            elif hasattr(detection, 'drift_value'):
                total_shift += abs(detection.drift_value) * detection.confidence / 100  # Normalize percentage
                total_weight += detection.confidence
            
            # Track maximum severity
            severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            if severity_order.get(detection.severity, 0) > severity_order.get(max_severity, 0):
                max_severity = detection.severity
        
        overall_shift = total_shift / total_weight if total_weight > 0 else 0.0
        overall_confidence = np.mean([d.confidence for d in all_detections])
        
        return True, overall_shift, max_severity
    
    def _calculate_quality_score(self, shifts: List[SpectralShiftResult], 
                                drifts: List[IntensityDriftResult],
                                baseline_issues: List[BaselineAnalysisResult]) -> Tuple[float, str]:
        """Calculate quality score based on detected issues"""
        quality_impact = 0.0
        
        # Sum quality impacts
        for shift in shifts:
            quality_impact += shift.quality_impact
        
        for drift in drifts:
            # Convert percentage drift to quality impact
            quality_impact += min(100, abs(drift.drift_value) * 0.5)
        
        for baseline in baseline_issues:
            if baseline.severity == "critical":
                quality_impact += 30
            elif baseline.severity == "high":
                quality_impact += 20
            elif baseline.severity == "medium":
                quality_impact += 10
            else:
                quality_impact += 5
        
        # Cap at 100
        quality_impact = min(100, quality_impact)
        quality_score = 100 - quality_impact
        
        # Determine grade
        if quality_score >= 90:
            grade = "excellent"
        elif quality_score >= 75:
            grade = "good"
        elif quality_score >= 50:
            grade = "fair"
        elif quality_score >= 25:
            grade = "poor"
        else:
            grade = "invalid"
        
        return quality_score, grade
    
    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute the shift detector agent's primary function"""
        import time
        
        start_time = time.time()
        
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting ShiftDetectorAgent execution")
            
            # Extract spectral data from context
            spectral_data = context.get('spectral_data', {})
            sample_id = context.get('sample_id', 'unknown')
            
            # Validate input data
            validation_errors = self.validate_spectral_data(spectral_data)
            if validation_errors:
                for error in validation_errors:
                    self.log_error(error, ErrorSeverity.HIGH)
                return self._create_success_output({
                    "status": "error",
                    "message": "Invalid spectral data",
                    "errors": validation_errors
                })
            
            # Extract wavelengths and intensities
            wavelengths = np.array(spectral_data["wavelengths"])
            intensities = np.array(spectral_data["intensities"])
            
            # Preprocess data
            wavelengths, intensities = self.preprocess_spectral_data(wavelengths, intensities)
            
            # Initialize results
            wavelength_shifts = []
            intensity_drifts = []
            baseline_issues = []
            other_issues = []
            
            # Detect wavelength shifts using multiple methods
            if self.reference_spectra or (self.standard_wavelengths is not None and len(self.standard_wavelengths) > 0):
                # Use first reference spectrum if available
                ref_data = next(iter(self.reference_spectra.values()), None)
                if ref_data and 'wavelengths' in ref_data and 'intensities' in ref_data:
                    ref_wavelengths = np.array(ref_data['wavelengths'])
                    ref_intensities = np.array(ref_data['intensities'])
                    
                    # FFT-based detection
                    if self.detection_methods['fft_correlation'].enabled:
                        fft_result = self.detect_wavelength_shift_fft(
                            wavelengths, intensities, ref_wavelengths, ref_intensities
                        )
                        if fft_result:
                            wavelength_shifts.append(fft_result)
                    
                    # Peak matching detection
                    if self.detection_methods['peak_matching'].enabled:
                        peak_result = self.detect_wavelength_shift_peak_matching(
                            wavelengths, intensities, ref_wavelengths, ref_intensities
                        )
                        if peak_result:
                            wavelength_shifts.append(peak_result)
                    
                    # Derivative analysis detection
                    if self.detection_methods['derivative_analysis'].enabled:
                        deriv_result = self.detect_wavelength_shift_derivative(
                            wavelengths, intensities, ref_wavelengths, ref_intensities
                        )
                        if deriv_result:
                            wavelength_shifts.append(deriv_result)
            
            # Detect intensity drifts
            intensity_drifts = self.detect_intensity_drift(wavelengths, intensities)
            
            # Analyze baseline
            baseline_issues = self.analyze_baseline(wavelengths, intensities)
            
            # Calculate overall assessment
            overall_detected, overall_shift, overall_severity = self._calculate_overall_assessment(
                wavelength_shifts, intensity_drifts, baseline_issues
            )
            
            # Calculate quality score
            quality_score, quality_grade = self._calculate_quality_score(
                wavelength_shifts, intensity_drifts, baseline_issues
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                wavelength_shifts, intensity_drifts, baseline_issues, overall_shift
            )
            
            # Create comprehensive report
            report = ShiftDetectionReport(
                sample_id=sample_id,
                timestamp=datetime.now().isoformat(),
                wavelength_range=(float(wavelengths[0]), float(wavelengths[-1])),
                data_points=len(wavelengths),
                wavelength_shifts=wavelength_shifts,
                intensity_drifts=intensity_drifts,
                baseline_issues=baseline_issues,
                other_issues=other_issues,
                overall_shift_detected=overall_detected,
                overall_shift_value=overall_shift,
                overall_confidence=np.mean([s.confidence for s in wavelength_shifts] + [d.confidence for d in intensity_drifts] + [b.confidence for b in baseline_issues]) if (len(wavelength_shifts) > 0 or len(intensity_drifts) > 0 or len(baseline_issues) > 0) else 0.0,
                overall_severity=overall_severity,
                quality_score=quality_score,
                quality_grade=quality_grade,
                recommendations=recommendations,
                calibration_required=overall_severity in ["high", "critical"],
                metadata=context.get('metadata', {})
            )
            
            # Store results
            self.detection_results[sample_id] = report
            self.stats['analyses_performed'] += 1
            self.stats['shifts_detected'] += len(wavelength_shifts)
            self.stats['drifts_detected'] += len(intensity_drifts)
            self.stats['baseline_issues_detected'] += len(baseline_issues)
            
            self.status = AgentStatus.COMPLETED
            self.logger.info(f"Shift detection completed for sample {sample_id}")
            
            # Update processing time
            self.stats['processing_time'] += time.time() - start_time
            
            return self._create_success_output({
                "status": "completed",
                "message": "Shift detection analysis completed successfully",
                "sample_id": sample_id,
                "report": report.__dict__,
                "stats": self.stats
            })
            
        except Exception as e:
            self.stats['errors'] += 1
            return self._handle_error(e)
    
    def _generate_recommendations(self, shifts: List[SpectralShiftResult], 
                                 drifts: List[IntensityDriftResult],
                                 baseline_issues: List[BaselineAnalysisResult],
                                 overall_shift: float) -> List[str]:
        """Generate recommendations based on detected issues"""
        recommendations = []
        
        # Wavelength shift recommendations
        if shifts:
            avg_shift = np.mean([s.shift_value for s in shifts])
            if abs(avg_shift) >= 1.0:
                recommendations.append(f"Recalibrate spectrometer: significant wavelength shift of {avg_shift:.2f} nm detected")
            elif abs(avg_shift) >= 0.5:
                recommendations.append(f"Check wavelength calibration: minor shift of {avg_shift:.2f} nm detected")
        
        # Intensity drift recommendations
        for drift in drifts:
            if drift.drift_type == "linear":
                recommendations.append(f"Apply linear intensity correction for {abs(drift.drift_value):.1f}% drift")
            elif drift.drift_type == "exponential":
                recommendations.append(f"Apply logarithmic intensity correction for exponential drift")
            elif drift.drift_type == "random":
                recommendations.append(f"Investigate data collection conditions: {drift.drift_value:.1f}% random variations detected")
        
        # Baseline recommendations
        for baseline in baseline_issues:
            if baseline.baseline_type == "curved":
                recommendations.append(f"Apply polynomial baseline correction (curvature detected)")
            elif baseline.baseline_type == "drifted":
                recommendations.append(f"Apply linear baseline correction (drift of {baseline.baseline_slope:.2e} per nm)")
        
        # General recommendations
        if overall_shift >= 2.0:
            recommendations.append("Perform full spectrometer recalibration")
        elif overall_shift >= 1.0:
            recommendations.append("Verify calibration with reference standards")
        
        if not shifts and not drifts and not baseline_issues:
            recommendations.append("Spectral data quality is excellent - no issues detected")
        
        return recommendations
    
    def validate(self) -> List[AgentError]:
        """Validate agent configuration and state"""
        errors = super().validate()
        
        # Check required dependencies
        for dep in self.dependencies:
            try:
                __import__(dep)
            except ImportError:
                self.log_error(
                    f"Missing dependency: {dep}",
                    ErrorSeverity.HIGH,
                    {"dependency": dep},
                    f"Install with: pip install {dep}"
                )
        
        # Check wavelength range validity
        if self.wavelength_range[0] >= self.wavelength_range[1]:
            self.log_error(
                "Invalid wavelength range",
                ErrorSeverity.HIGH,
                {"range": self.wavelength_range},
                "Set valid wavelength range with min < max"
            )
        
        return self.errors


if __name__ == "__main__":
    # Allow direct execution for testing
    agent = ShiftDetectorAgent()
    output = agent.initialize()
    print(f"ShiftDetectorAgent initialized: {output.status.name}")
    
    # Test with sample data
    test_context = {
        "sample_id": "test_sample_001",
        "spectral_data": {
            "wavelengths": list(range(700, 2500, 10)),
            "intensities": [abs(np.sin(i * 0.01)) + 0.1 * (i - 1600) for i in range(700, 2500, 10)],
            "metadata": {"instrument": "test_spectrometer"}
        },
        "metadata": {"test": True}
    }
    
    result = agent.execute(test_context)
    print(f"Execution result: {result.status.name}")
    if result.data.get("report"):
        report = result.data["report"]
        print(f"Shifts detected: {len(report.get('wavelength_shifts', []))}")
        print(f"Drifts detected: {len(report.get('intensity_drifts', []))}")
        print(f"Quality score: {report.get('quality_score', 0)}")
