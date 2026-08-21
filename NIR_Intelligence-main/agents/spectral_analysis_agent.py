# NIR Intelligence Platform - Spectral Analysis Agent
# Handles NIR spectral data analysis, preprocessing, and quality assessment

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


class SpectralQuality(Enum):
    """Quality assessment for spectral data"""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    INVALID = "invalid"


class SpectrometerIssue(Enum):
    """Types of spectrometer issues that can be detected"""

    NO_ISSUE = "no_issue"
    WAVELENGTH_SHIFT = "wavelength_shift"
    INTENSITY_DRIFT = "intensity_drift"
    NOISE_HIGH = "high_noise"
    BASELINE_DRIFT = "baseline_drift"
    SATURATION = "saturation"
    LOW_SIGNAL = "low_signal"
    SPIKES = "spikes"
    NON_LINEARITY = "non_linearity"


@dataclass
class SpectralAnalysisResult:
    """Data class for spectral analysis results"""

    sample_id: str
    wavelength_range: Tuple[float, float]
    data_points: int
    quality_score: float  # 0-100
    quality_grade: SpectralQuality
    issues_detected: List[SpectrometerIssue]
    shift_detected: Optional[float] = None  # nm
    noise_level: Optional[float] = None
    signal_to_noise_ratio: Optional[float] = None
    baseline_correction_applied: bool = False
    preprocessing_steps: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpectrometerParameterRecommendation:
    """Recommendations for spectrometer parameter setup"""

    parameter: str
    current_value: Any
    recommended_value: Any
    reason: str
    impact: str  # "low", "medium", "high"
    confidence: float  # 0-1


class SpectralAnalysisAgent(BaseAgent):
    """Agent for NIR spectral data analysis and quality assessment"""

    def __init__(self, **kwargs):
        super().__init__(name="SpectralAnalysisAgent", version="1.0.0", **kwargs)
        self.dependencies = ["numpy", "pandas", "scipy", "scikit-learn"]

        # Configuration
        self.wavelength_range = kwargs.get("wavelength_range", (700, 2500))  # nm
        self.min_data_points = kwargs.get("min_data_points", 100)
        self.quality_thresholds = kwargs.get(
            "quality_thresholds", {"excellent": 90, "good": 75, "fair": 50, "poor": 25}
        )

        # Reference data for comparison (would be loaded from calibration files)
        self.reference_spectra = kwargs.get("reference_spectra", {})
        self.standard_wavelengths = kwargs.get("standard_wavelengths", None)

        # Preprocessing configuration
        self.preprocessing_config = kwargs.get(
            "preprocessing",
            {
                "smoothing": True,
                "baseline_correction": True,
                "noise_removal": True,
                "normalization": True,
                "derivative": False,
            },
        )

        self.logger.info(f"SpectralAnalysisAgent initialized with wavelength range: {self.wavelength_range}")

    def initialize(self) -> AgentOutput:
        """Initialize the spectral analysis agent"""
        self.status = AgentStatus.READY
        self.logger.info("SpectralAnalysisAgent initialized and ready for analysis")

        # Load reference data if available
        self._load_reference_data()

        return AgentOutput(
            agent_name=self.name,
            status=self.status,
            version=self.version,
            dependencies=self.dependencies,
            data={
                "wavelength_range": self.wavelength_range,
                "min_data_points": self.min_data_points,
                "quality_thresholds": self.quality_thresholds,
                "preprocessing_config": self.preprocessing_config,
            },
        )

    def _load_reference_data(self):
        """Load reference spectral data for comparison"""
        try:
            # Try to load from standard locations
            reference_files = [
                Path("data/reference_spectra.json"),
                Path("data/calibration_data.json"),
                Path("nir_test_env/reference_spectra.json"),
            ]

            for ref_file in reference_files:
                if ref_file.exists():
                    with open(ref_file, "r") as f:
                        self.reference_spectra = json.load(f)
                    self.logger.info(f"Loaded reference spectra from {ref_file}")
                    break
        except Exception as e:
            self.logger.warning(f"Could not load reference data: {e}")

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

        return errors

    def detect_wavelength_shift(self, wavelengths: List[float], reference_wavelengths: List[float]) -> Optional[float]:
        """Detect wavelength shift by comparing with reference"""
        try:
            if len(wavelengths) != len(reference_wavelengths):
                return None

            # Simple shift detection by comparing first and last points
            shift_start = wavelengths[0] - reference_wavelengths[0]
            shift_end = wavelengths[-1] - reference_wavelengths[-1]

            # Average shift
            avg_shift = (shift_start + shift_end) / 2

            # Only report significant shifts (> 1nm)
            if abs(avg_shift) > 1.0:
                return avg_shift
            return None

        except Exception as e:
            self.logger.warning(f"Error detecting wavelength shift: {e}")
            return None

    def calculate_noise_level(self, intensities: List[float]) -> float:
        """Calculate noise level in spectral data"""
        try:
            intensities_array = np.array(intensities)
            # Use standard deviation as noise estimate
            noise_level = np.std(intensities_array)
            return float(noise_level)
        except Exception as e:
            self.logger.warning(f"Error calculating noise level: {e}")
            return 0.0

    def calculate_signal_to_noise(self, intensities: List[float]) -> float:
        """Calculate signal-to-noise ratio"""
        try:
            intensities_array = np.array(intensities)
            signal = np.mean(intensities_array)
            noise = np.std(intensities_array)

            if noise == 0:
                return float("inf")
            return signal / noise
        except Exception as e:
            self.logger.warning(f"Error calculating SNR: {e}")
            return 0.0

    def detect_spikes(self, intensities: List[float], threshold: float = 3.0) -> List[int]:
        """Detect spikes in spectral data"""
        try:
            intensities_array = np.array(intensities)
            mean_val = np.mean(intensities_array)
            std_val = np.std(intensities_array)

            spike_indices = []
            for i, intensity in enumerate(intensities_array):
                if abs(intensity - mean_val) > threshold * std_val:
                    spike_indices.append(i)

            return spike_indices
        except Exception as e:
            self.logger.warning(f"Error detecting spikes: {e}")
            return []

    def assess_spectral_quality(self, spectral_data: Dict[str, Any]) -> SpectralAnalysisResult:
        """Assess the quality of spectral data"""
        try:
            wavelengths = spectral_data["wavelengths"]
            intensities = spectral_data["intensities"]
            sample_id = spectral_data.get("sample_id", "unknown")

            # Basic validation
            validation_errors = self.validate_spectral_data(spectral_data)
            if validation_errors:
                return SpectralAnalysisResult(
                    sample_id=sample_id,
                    wavelength_range=(min(wavelengths), max(wavelengths)) if wavelengths else (0, 0),
                    data_points=len(wavelengths),
                    quality_score=0.0,
                    quality_grade=SpectralQuality.INVALID,
                    issues_detected=[SpectrometerIssue.INVALID],
                    recommendations=[f"Fix validation errors: {', '.join(validation_errors)}"],
                )

            # Initialize analysis result
            result = SpectralAnalysisResult(
                sample_id=sample_id,
                wavelength_range=(min(wavelengths), max(wavelengths)),
                data_points=len(wavelengths),
                quality_score=100.0,  # Start with perfect score
                quality_grade=SpectralQuality.EXCELLENT,
                issues_detected=[],
                preprocessing_steps=[],
                recommendations=[],
            )

            # Check wavelength range
            min_wl, max_wl = result.wavelength_range
            expected_min, expected_max = self.wavelength_range

            if min_wl < expected_min or max_wl > expected_max:
                result.issues_detected.append(SpectrometerIssue.WAVELENGTH_SHIFT)
                result.quality_score -= 15
                result.recommendations.append(
                    f"Wavelength range {result.wavelength_range} is outside expected range {self.wavelength_range}"
                )

            # Detect wavelength shift if reference available
            if self.standard_wavelengths and len(self.standard_wavelengths) == len(wavelengths):
                shift = self.detect_wavelength_shift(wavelengths, self.standard_wavelengths)
                if shift:
                    result.shift_detected = shift
                    result.issues_detected.append(SpectrometerIssue.WAVELENGTH_SHIFT)
                    result.quality_score -= 20
                    result.recommendations.append(
                        f"Wavelength shift detected: {shift:.2f} nm. Consider recalibrating spectrometer."
                    )

            # Calculate noise metrics
            result.noise_level = self.calculate_noise_level(intensities)
            result.signal_to_noise_ratio = self.calculate_signal_to_noise(intensities)

            # Check signal-to-noise ratio
            if result.signal_to_noise_ratio and result.signal_to_noise_ratio < 10:
                result.issues_detected.append(SpectrometerIssue.NOISE_HIGH)
                result.quality_score -= 25
                result.recommendations.append(
                    f"Low signal-to-noise ratio: {result.signal_to_noise_ratio:.2f}. "
                    "Consider increasing integration time or improving light source."
                )

            # Detect spikes
            spike_indices = self.detect_spikes(intensities)
            if spike_indices:
                result.issues_detected.append(SpectrometerIssue.SPIKES)
                spike_percentage = len(spike_indices) / len(intensities) * 100
                result.quality_score -= min(15, spike_percentage * 0.5)  # Max 15 points deduction
                result.recommendations.append(
                    f"Detected {len(spike_indices)} spikes ({spike_percentage:.1f}% of data). "
                    "Consider spike removal preprocessing."
                )

            # Check for saturation (values at or near maximum)
            max_intensity = max(intensities)
            if max_intensity >= 65535:  # Common saturation value for 16-bit ADC
                result.issues_detected.append(SpectrometerIssue.SATURATION)
                result.quality_score -= 25
                result.recommendations.append("Saturation detected. Reduce integration time or increase detector gain.")

            # Check for low signal
            min_intensity = min(intensities)
            mean_intensity = np.mean(intensities)
            if mean_intensity < 100:  # Arbitrary low threshold
                result.issues_detected.append(SpectrometerIssue.LOW_SIGNAL)
                result.quality_score -= 20
                result.recommendations.append("Low signal detected. Increase integration time or improve light source.")

            # Apply preprocessing (simulated)
            if self.preprocessing_config.get("baseline_correction"):
                result.preprocessing_steps.append("baseline_correction")
                result.baseline_correction_applied = True

            if self.preprocessing_config.get("smoothing"):
                result.preprocessing_steps.append("smoothing")

            if self.preprocessing_config.get("noise_removal"):
                result.preprocessing_steps.append("noise_removal")

            # Determine quality grade
            if result.quality_score >= self.quality_thresholds.get("excellent", 90):
                result.quality_grade = SpectralQuality.EXCELLENT
            elif result.quality_score >= self.quality_thresholds.get("good", 75):
                result.quality_grade = SpectralQuality.GOOD
            elif result.quality_score >= self.quality_thresholds.get("fair", 50):
                result.quality_grade = SpectralQuality.FAIR
            elif result.quality_score >= self.quality_thresholds.get("poor", 25):
                result.quality_grade = SpectralQuality.POOR
            else:
                result.quality_grade = SpectralQuality.INVALID

            # Add parameter recommendations
            result.recommendations.extend(self._generate_parameter_recommendations(result))

            return result

        except Exception as e:
            self.logger.error(f"Error assessing spectral quality: {e}")
            return SpectralAnalysisResult(
                sample_id=spectral_data.get("sample_id", "unknown"),
                wavelength_range=(0, 0),
                data_points=0,
                quality_score=0.0,
                quality_grade=SpectralQuality.INVALID,
                issues_detected=[SpectrometerIssue.INVALID],
                recommendations=[f"Analysis failed: {str(e)}"],
            )

    def _generate_parameter_recommendations(self, analysis_result: SpectralAnalysisResult) -> List[str]:
        """Generate spectrometer parameter recommendations based on analysis"""
        recommendations = []

        # Wavelength shift recommendations
        if analysis_result.shift_detected:
            shift = analysis_result.shift_detected
            if shift > 0:
                recommendations.append(
                    f"Wavelength calibration: Adjust calibration by -{abs(shift):.2f} nm " "to correct positive shift."
                )
            else:
                recommendations.append(
                    f"Wavelength calibration: Adjust calibration by {abs(shift):.2f} nm " "to correct negative shift."
                )

        # Noise recommendations
        if analysis_result.noise_level and analysis_result.noise_level > 100:
            recommendations.append(
                "High noise detected. Consider: increasing number of scans, "
                "using better shielding, or improving detector cooling."
            )

        # SNR recommendations
        if analysis_result.signal_to_noise_ratio and analysis_result.signal_to_noise_ratio < 50:
            recommendations.append(
                "Low SNR. Consider: increasing integration time, using higher "
                "intensity light source, or improving sample preparation."
            )

        return recommendations

    def generate_spectrometer_parameter_recommendations(
        self, analysis_result: SpectralAnalysisResult
    ) -> List[SpectrometerParameterRecommendation]:
        """Generate detailed spectrometer parameter recommendations"""
        recommendations = []

        # Integration time recommendations
        if analysis_result.signal_to_noise_ratio and analysis_result.signal_to_noise_ratio < 50:
            recommendations.append(
                SpectrometerParameterRecommendation(
                    parameter="integration_time",
                    current_value="unknown",
                    recommended_value="increase by 50%",
                    reason="Low signal-to-noise ratio",
                    impact="high",
                    confidence=0.9,
                )
            )

        # Wavelength calibration recommendations
        if analysis_result.shift_detected:
            recommendations.append(
                SpectrometerParameterRecommendation(
                    parameter="wavelength_calibration",
                    current_value="unknown",
                    recommended_value=f"adjust by {-analysis_result.shift_detected:.2f} nm",
                    reason="Wavelength shift detected",
                    impact="high",
                    confidence=0.95,
                )
            )

        # Baseline correction recommendations
        if not analysis_result.baseline_correction_applied:
            recommendations.append(
                SpectrometerParameterRecommendation(
                    parameter="baseline_correction",
                    current_value="disabled",
                    recommended_value="enabled",
                    reason="Baseline drift may be present",
                    impact="medium",
                    confidence=0.7,
                )
            )

        return recommendations

    def preprocess_spectral_data(self, spectral_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply preprocessing to spectral data"""
        try:
            processed_data = spectral_data.copy()
            wavelengths = spectral_data["wavelengths"]
            intensities = spectral_data["intensities"]

            # Apply preprocessing steps
            if self.preprocessing_config.get("smoothing"):
                # Simple moving average smoothing
                window_size = 3
                intensities = self._apply_moving_average(intensities, window_size)
                processed_data["preprocessing_applied"] = processed_data.get("preprocessing_applied", []) + [
                    "smoothing"
                ]

            if self.preprocessing_config.get("baseline_correction"):
                intensities = self._apply_baseline_correction(intensities)
                processed_data["preprocessing_applied"] = processed_data.get("preprocessing_applied", []) + [
                    "baseline_correction"
                ]

            if self.preprocessing_config.get("normalization"):
                intensities = self._normalize_intensities(intensities)
                processed_data["preprocessing_applied"] = processed_data.get("preprocessing_applied", []) + [
                    "normalization"
                ]

            processed_data["intensities"] = intensities
            return processed_data

        except Exception as e:
            self.logger.error(f"Error preprocessing spectral data: {e}")
            return spectral_data

    def _apply_moving_average(self, data: List[float], window_size: int = 3) -> List[float]:
        """Apply moving average smoothing"""
        if window_size <= 1:
            return data

        smoothed = []
        for i in range(len(data)):
            start = max(0, i - window_size // 2)
            end = min(len(data), i + window_size // 2 + 1)
            window = data[start:end]
            smoothed.append(sum(window) / len(window))
        return smoothed

    def _apply_baseline_correction(self, intensities: List[float]) -> List[float]:
        """Apply simple baseline correction"""
        try:
            intensities_array = np.array(intensities)
            # Simple baseline correction using minimum value
            baseline = np.min(intensities_array)
            corrected = intensities_array - baseline
            return corrected.tolist()
        except Exception as e:
            self.logger.warning(f"Baseline correction failed: {e}")
            return intensities

    def _normalize_intensities(self, intensities: List[float]) -> List[float]:
        """Normalize intensities to 0-1 range"""
        try:
            intensities_array = np.array(intensities)
            min_val = np.min(intensities_array)
            max_val = np.max(intensities_array)

            if max_val - min_val > 0:
                normalized = (intensities_array - min_val) / (max_val - min_val)
                return normalized.tolist()
            return intensities
        except Exception as e:
            self.logger.warning(f"Normalization failed: {e}")
            return intensities

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute spectral analysis workflow"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting spectral analysis execution")

            # Extract spectral data from context
            spectral_data = context.get("spectral_data", {})

            if not spectral_data:
                return self._handle_error(ValueError("No spectral data provided in context"))

            # Validate data
            validation_errors = self.validate_spectral_data(spectral_data)
            if validation_errors:
                self.logger.warning(f"Validation errors: {validation_errors}")
                # Continue with analysis but flag the issues
                spectral_data["validation_warnings"] = validation_errors

            # Preprocess data
            processed_data = self.preprocess_spectral_data(spectral_data)

            # Assess spectral quality
            analysis_result = self.assess_spectral_quality(processed_data)

            # Generate parameter recommendations
            parameter_recommendations = self.generate_spectrometer_parameter_recommendations(analysis_result)

            # Prepare final output
            output_data = {
                "spectral_analysis": analysis_result.__dict__,
                "parameter_recommendations": [rec.__dict__ for rec in parameter_recommendations],
                "processed_data": {
                    "wavelengths": processed_data.get("wavelengths"),
                    "intensities": processed_data.get("intensities"),
                    "preprocessing_applied": processed_data.get("preprocessing_applied", []),
                },
                "validation_warnings": validation_errors,
                "analysis_summary": {
                    "quality_score": analysis_result.quality_score,
                    "quality_grade": analysis_result.quality_grade.value,
                    "issues_detected": [issue.value for issue in analysis_result.issues_detected],
                    "recommendations_count": len(analysis_result.recommendations) + len(parameter_recommendations),
                },
            }

            self.status = AgentStatus.COMPLETED
            self.logger.info(f"Spectral analysis completed for sample: {analysis_result.sample_id}")

            return self._create_success_output(output_data)

        except Exception as e:
            return self._handle_error(e)
