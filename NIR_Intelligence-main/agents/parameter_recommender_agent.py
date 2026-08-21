#!/usr/bin/env python3
"""
NIR Intelligence Platform - ParameterRecommenderAgent
Agent for recommending optimal spectrometer parameters based on spectral data analysis
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
from scipy import signal, fft, stats, optimize, interpolate
from sklearn.preprocessing import StandardScaler
from .base_agent import BaseAgent, AgentOutput, AgentStatus, ErrorSeverity, AgentError


@dataclass
class SpectrometerParameter:
    """Spectrometer parameter definition"""
    name: str
    description: str
    unit: str = ""
    min_value: float = 0.0
    max_value: float = 1.0
    default_value: float = 0.5
    parameter_type: str = "continuous"  # 'continuous', 'discrete', 'boolean'
    possible_values: List[Any] = field(default_factory=list)


@dataclass
class ParameterRecommendation:
    """Recommendation for a specific spectrometer parameter"""
    parameter: str
    current_value: Any
    recommended_value: Any
    reason: str
    impact: str  # 'low', 'medium', 'high', 'critical'
    confidence: float  # 0-1
    optimization_direction: str = "increase"  # 'increase', 'decrease', 'set_to'
    expected_improvement: float = 0.0  # Percentage improvement expected
    validation_required: bool = False


@dataclass
class ParameterOptimizationResult:
    """Result of parameter optimization analysis"""
    parameter: str
    optimal_value: Any
    optimization_method: str
    objective_function_value: float
    confidence: float  # 0-1
    convergence_achieved: bool = True
    iterations: int = 0
    improvement: float = 0.0  # Percentage improvement


@dataclass
class SpectrometerConfiguration:
    """Complete spectrometer configuration"""
    configuration_name: str
    parameters: Dict[str, Any]
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    quality_score: float = 0.0
    timestamp: str = ""
    notes: str = ""


@dataclass
class ParameterRecommendationReport:
    """Comprehensive parameter recommendation report"""
    sample_id: str
    timestamp: str
    spectrometer_type: str = "unknown"
    wavelength_range: Tuple[float, float] = (0.0, 0.0)
    
    # Current configuration
    current_configuration: Dict[str, Any] = field(default_factory=dict)
    
    # Recommendations
    parameter_recommendations: List[ParameterRecommendation] = field(default_factory=list)
    optimization_results: List[ParameterOptimizationResult] = field(default_factory=list)
    
    # Overall assessment
    overall_quality_score: float = 0.0  # 0-100
    overall_grade: str = "excellent"
    configuration_optimized: bool = False
    expected_improvement: float = 0.0  # Overall expected improvement percentage
    
    # Priority recommendations
    high_priority_recommendations: List[ParameterRecommendation] = field(default_factory=list)
    medium_priority_recommendations: List[ParameterRecommendation] = field(default_factory=list)
    low_priority_recommendations: List[ParameterRecommendation] = field(default_factory=list)
    
    # Implementation guidance
    implementation_steps: List[str] = field(default_factory=list)
    validation_requirements: List[str] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class ParameterRecommenderAgent(BaseAgent):
    """
    Agent for recommending optimal spectrometer parameters based on spectral data analysis
    
    Features:
    - Comprehensive parameter analysis for NIR spectrometers
    - Signal-to-noise ratio optimization recommendations
    - Integration time and averaging parameter optimization
    - Wavelength range and resolution recommendations
    - Temperature and environmental condition compensation
    - Multi-objective optimization for parameter combinations
    - Performance prediction and validation requirements
    - Implementation guidance and step-by-step recommendations
    """
    
    def __init__(self, **kwargs):
        super().__init__(name="ParameterRecommenderAgent", version="2.0.0", **kwargs)
        self.dependencies = ['numpy', 'pandas', 'scipy', 'scikit-learn']
        self.logger = logging.getLogger(f"Agent.ParameterRecommenderAgent")
        
        # Configuration
        self.wavelength_range = kwargs.get('wavelength_range', (700, 2500))  # nm
        self.min_data_points = kwargs.get('min_data_points', 50)
        self.snr_threshold = kwargs.get('snr_threshold', 100.0)  # Minimum acceptable SNR
        self.quality_threshold = kwargs.get('quality_threshold', 75.0)  # Minimum quality score
        
        # Supported spectrometer types and their parameters
        self.spectrometer_types = kwargs.get('spectrometer_types', {
            'generic': {
                'description': 'Generic NIR spectrometer',
                'parameters': {
                    'integration_time': SpectrometerParameter(
                        name="Integration Time",
                        description="Time for each spectral measurement",
                        unit="ms",
                        min_value=1,
                        max_value=1000,
                        default_value=100,
                        parameter_type="continuous"
                    ),
                    'scans_to_average': SpectrometerParameter(
                        name="Scans to Average",
                        description="Number of scans to average for each measurement",
                        unit="count",
                        min_value=1,
                        max_value=100,
                        default_value=10,
                        parameter_type="discrete"
                    ),
                    'wavelength_range': SpectrometerParameter(
                        name="Wavelength Range",
                        description="Spectral range of the spectrometer",
                        unit="nm",
                        min_value=600,
                        max_value=3000,
                        default_value=1100,
                        parameter_type="continuous"
                    ),
                    'spectral_resolution': SpectrometerParameter(
                        name="Spectral Resolution",
                        description="Resolution of the spectrometer",
                        unit="nm",
                        min_value=0.1,
                        max_value=20,
                        default_value=2.0,
                        parameter_type="continuous"
                    ),
                    'gain': SpectrometerParameter(
                        name="Gain",
                        description="Detector gain setting",
                        unit="dB",
                        min_value=0,
                        max_value=40,
                        default_value=20,
                        parameter_type="continuous"
                    ),
                    'laser_power': SpectrometerParameter(
                        name="Laser Power",
                        description="Power of the light source",
                        unit="mW",
                        min_value=1,
                        max_value=100,
                        default_value=50,
                        parameter_type="continuous"
                    ),
                    'temperature_compensation': SpectrometerParameter(
                        name="Temperature Compensation",
                        description="Enable temperature compensation",
                        unit="",
                        min_value=0,
                        max_value=1,
                        default_value=1,
                        parameter_type="boolean",
                        possible_values=[True, False]
                    ),
                    'dark_correction': SpectrometerParameter(
                        name="Dark Correction",
                        description="Enable dark current correction",
                        unit="",
                        min_value=0,
                        max_value=1,
                        default_value=1,
                        parameter_type="boolean",
                        possible_values=[True, False]
                    )
                }
            },
            'diy': {
                'description': 'DIY NIR spectrometer',
                'parameters': {
                    'integration_time': SpectrometerParameter(
                        name="Integration Time",
                        description="Time for each spectral measurement",
                        unit="ms",
                        min_value=10,
                        max_value=5000,
                        default_value=500,
                        parameter_type="continuous"
                    ),
                    'scans_to_average': SpectrometerParameter(
                        name="Scans to Average",
                        description="Number of scans to average",
                        unit="count",
                        min_value=1,
                        max_value=50,
                        default_value=20,
                        parameter_type="discrete"
                    ),
                    'boxcar_width': SpectrometerParameter(
                        name="Boxcar Width",
                        description="Smoothing window size",
                        unit="points",
                        min_value=1,
                        max_value=20,
                        default_value=5,
                        parameter_type="discrete"
                    )
                }
            }
        })
        
        # Optimization configuration
        self.optimization_config = kwargs.get('optimization', {
            'max_iterations': 100,
            'tolerance': 1e-6,
            'method': 'L-BFGS-B',
            'population_size': 20,
            'mutation_rate': 0.1,
            'crossover_rate': 0.8,
            'elite_size': 2
        })
        
        # Quality metrics weights
        self.quality_weights = kwargs.get('quality_weights', {
            'snr': 0.3,
            'resolution': 0.2,
            'coverage': 0.2,
            'stability': 0.15,
            'speed': 0.15
        })
        
        # Reference data
        self.reference_configurations = kwargs.get('reference_configurations', {})
        self.performance_data = kwargs.get('performance_data', {})
        
        # Initialize agent-specific attributes
        self._initialize_attributes()
        
        self.logger.info(f"ParameterRecommenderAgent initialized for wavelength range: {self.wavelength_range}")
    
    def _initialize_attributes(self):
        """Initialize agent-specific attributes"""
        self.recommendation_results: Dict[str, ParameterRecommendationReport] = {}
        self.stats = {
            'analyses_performed': 0,
            'recommendations_generated': 0,
            'optimizations_performed': 0,
            'processing_time': 0.0,
            'errors': 0
        }
        
        # Load reference data
        self._load_reference_data()
    
    def _load_reference_data(self):
        """Load reference configuration data"""
        try:
            reference_files = [
                Path("data/reference_configurations.json"),
                Path("data/performance_data.json"),
                Path("nir_test_env/reference_configs.json"),
                Path("config/spectrometer_configs.json")
            ]
            
            for ref_file in reference_files:
                if ref_file.exists():
                    with open(ref_file, "r") as f:
                        data = json.load(f)
                        if 'reference_configurations' in data:
                            self.reference_configurations = data['reference_configurations']
                        if 'performance_data' in data:
                            self.performance_data = data['performance_data']
                    self.logger.info(f"Loaded reference configurations from {ref_file}")
                    break
                    
        except Exception as e:
            self.logger.warning(f"Could not load reference data: {e}")
    
    def initialize(self) -> AgentOutput:
        """Initialize the parameter recommender agent"""
        self.status = AgentStatus.READY
        self.logger.info("ParameterRecommenderAgent initialized and ready for parameter optimization")
        
        return AgentOutput(
            agent_name=self.name,
            status=self.status,
            version=self.version,
            dependencies=self.dependencies,
            data={
                "wavelength_range": self.wavelength_range,
                "min_data_points": self.min_data_points,
                "snr_threshold": self.snr_threshold,
                "quality_threshold": self.quality_threshold,
                "spectrometer_types": list(self.spectrometer_types.keys()),
                "optimization_config": self.optimization_config,
                "quality_weights": self.quality_weights,
                "reference_configurations_count": len(self.reference_configurations)
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
    
    def calculate_snr(self, intensities: np.ndarray) -> float:
        """Calculate signal-to-noise ratio from spectral data"""
        try:
            signal = np.mean(intensities)
            noise = np.std(intensities)
            return signal / (noise + 1e-10)
        except Exception as e:
            self.logger.warning(f"SNR calculation failed: {e}")
            return 0.0
    
    def calculate_spectral_resolution(self, wavelengths: np.ndarray, intensities: np.ndarray) -> float:
        """Estimate spectral resolution from spectral data"""
        try:
            # Use FWHM (Full Width at Half Maximum) of a prominent peak
            peaks, properties = signal.find_peaks(intensities, height=0.5)
            
            if peaks.size > 0:
                # Take the highest peak
                highest_peak_idx = np.argmax(properties['peak_heights'])
                peak_idx = peaks[highest_peak_idx]
                peak_height = properties['peak_heights'][highest_peak_idx]
                
                # Find half maximum
                half_max = peak_height / 2
                
                # Find indices where intensity crosses half_max
                crossings = np.where(intensities >= half_max)[0]
                if len(crossings) >= 2:
                    left_idx = crossings[0]
                    right_idx = crossings[-1]
                    
                    # Calculate FWHM in wavelength units
                    fwhm = wavelengths[right_idx] - wavelengths[left_idx]
                    return fwhm
            
            # If no peaks found, return average wavelength spacing
            if len(wavelengths) > 1:
                return np.mean(np.diff(wavelengths))
            return 0.0
            
        except Exception as e:
            self.logger.warning(f"Spectral resolution calculation failed: {e}")
            return 0.0
    
    def calculate_spectral_coverage(self, wavelengths: np.ndarray, target_range: Tuple[float, float] = (700, 2500)) -> float:
        """Calculate spectral coverage percentage"""
        try:
            min_wl, max_wl = target_range
            actual_min = wavelengths[0]
            actual_max = wavelengths[-1]
            
            # Calculate coverage
            total_range = max_wl - min_wl
            actual_range = actual_max - actual_min
            
            # Calculate overlap
            overlap_min = max(actual_min, min_wl)
            overlap_max = min(actual_max, max_wl)
            overlap_range = max(0, overlap_max - overlap_min)
            
            coverage = (overlap_range / total_range) * 100
            return coverage
            
        except Exception as e:
            self.logger.warning(f"Spectral coverage calculation failed: {e}")
            return 0.0
    
    def analyze_current_configuration(self, spectral_data: Dict[str, Any], 
                                    current_config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current spectrometer configuration and performance"""
        try:
            wavelengths = np.array(spectral_data["wavelengths"])
            intensities = np.array(spectral_data["intensities"])
            
            analysis = {
                'snr': self.calculate_snr(intensities),
                'spectral_resolution': self.calculate_spectral_resolution(wavelengths, intensities),
                'spectral_coverage': self.calculate_spectral_coverage(wavelengths),
                'data_quality_score': self._calculate_data_quality_score(wavelengths, intensities),
                'stability_score': self._calculate_stability_score(intensities),
                'speed_score': self._calculate_speed_score(current_config)
            }
            
            # Calculate overall quality score
            analysis['overall_quality'] = sum(
                analysis[metric] * self.quality_weights.get(metric, 0) 
                for metric in analysis
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Configuration analysis failed: {e}")
            return {}
    
    def _calculate_data_quality_score(self, wavelengths: np.ndarray, intensities: np.ndarray) -> float:
        """Calculate data quality score based on spectral characteristics"""
        try:
            score = 0.0
            
            # SNR contribution (0-25 points)
            snr = self.calculate_snr(intensities)
            snr_score = min(25, (snr / 100) * 25) if snr > 0 else 0
            score += snr_score
            
            # Resolution contribution (0-20 points)
            resolution = self.calculate_spectral_resolution(wavelengths, intensities)
            # Lower resolution is better (target < 5nm)
            resolution_score = min(20, max(0, 20 - (resolution / 5) * 20))
            score += resolution_score
            
            # Coverage contribution (0-20 points)
            coverage = self.calculate_spectral_coverage(wavelengths)
            coverage_score = (coverage / 100) * 20
            score += coverage_score
            
            # Dynamic range contribution (0-15 points)
            dynamic_range = np.max(intensities) - np.min(intensities)
            dr_score = min(15, (dynamic_range / 1000) * 15) if dynamic_range > 0 else 0
            score += dr_score
            
            # Noise level contribution (0-20 points)
            noise_level = np.std(intensities)
            noise_score = min(20, max(0, 20 - (noise_level / 0.1) * 20))
            score += noise_score
            
            return min(100, max(0, score))
            
        except Exception as e:
            self.logger.warning(f"Data quality score calculation failed: {e}")
            return 50.0
    
    def _calculate_stability_score(self, intensities: np.ndarray) -> float:
        """Calculate stability score based on spectral consistency"""
        try:
            # Calculate coefficient of variation
            cv = np.std(intensities) / (np.mean(intensities) + 1e-10)
            
            # Lower CV means higher stability
            stability_score = max(0, 100 - (cv * 1000))
            return min(100, stability_score)
            
        except Exception as e:
            self.logger.warning(f"Stability score calculation failed: {e}")
            return 75.0
    
    def _calculate_speed_score(self, config: Dict[str, Any]) -> float:
        """Calculate speed score based on acquisition parameters"""
        try:
            integration_time = config.get('integration_time', 100)
            scans_to_average = config.get('scans_to_average', 10)
            
            # Calculate total acquisition time
            total_time = integration_time * scans_to_average
            
            # Normalize to 0-100 scale (lower time = higher score)
            # Assuming typical range: 10ms to 10000ms
            normalized_time = total_time / 10000.0
            speed_score = max(0, 100 - (normalized_time * 100))
            
            return speed_score
            
        except Exception as e:
            self.logger.warning(f"Speed score calculation failed: {e}")
            return 50.0
    
    def recommend_integration_time(self, spectral_data: Dict[str, Any], 
                                  current_config: Dict[str, Any]) -> ParameterRecommendation:
        """Recommend optimal integration time"""
        try:
            intensities = np.array(spectral_data["intensities"])
            current_integration_time = current_config.get('integration_time', 100)
            
            # Calculate current SNR
            current_snr = self.calculate_snr(intensities)
            
            # Target SNR
            target_snr = self.snr_threshold
            
            if current_snr >= target_snr:
                # Current SNR is good, can potentially reduce integration time
                snr_ratio = current_snr / target_snr
                time_reduction_factor = min(0.5, snr_ratio)  # Don't reduce by more than 50%
                recommended_time = max(
                    self.spectrometer_types['generic']['parameters']['integration_time'].min_value,
                    int(current_integration_time * (1 - time_reduction_factor))
                )
                
                improvement = (current_integration_time - recommended_time) / current_integration_time * 100
                
                return ParameterRecommendation(
                    parameter="integration_time",
                    current_value=current_integration_time,
                    recommended_value=recommended_time,
                    reason=f"Current SNR ({current_snr:.1f}) exceeds target ({target_snr:.1f}), can reduce integration time",
                    impact="medium",
                    confidence=0.8,
                    optimization_direction="decrease",
                    expected_improvement=improvement,
                    validation_required=True
                )
            else:
                # Current SNR is low, need to increase integration time
                snr_ratio = target_snr / current_snr
                time_increase_factor = min(4.0, snr_ratio)  # Don't increase by more than 4x
                recommended_time = min(
                    self.spectrometer_types['generic']['parameters']['integration_time'].max_value,
                    int(current_integration_time * time_increase_factor)
                )
                
                improvement = (recommended_time - current_integration_time) / current_integration_time * 100
                
                return ParameterRecommendation(
                    parameter="integration_time",
                    current_value=current_integration_time,
                    recommended_value=recommended_time,
                    reason=f"Current SNR ({current_snr:.1f}) below target ({target_snr:.1f}), need to increase integration time",
                    impact="high",
                    confidence=0.9,
                    optimization_direction="increase",
                    expected_improvement=improvement,
                    validation_required=True
                )
                
        except Exception as e:
            self.logger.error(f"Integration time recommendation failed: {e}")
            return ParameterRecommendation(
                parameter="integration_time",
                current_value=current_config.get('integration_time', 100),
                recommended_value=100,
                reason="Error in recommendation calculation",
                impact="low",
                confidence=0.1,
                optimization_direction="set_to",
                expected_improvement=0.0,
                validation_required=True
            )
    
    def recommend_scans_to_average(self, spectral_data: Dict[str, Any], 
                                    current_config: Dict[str, Any]) -> ParameterRecommendation:
        """Recommend optimal number of scans to average"""
        try:
            intensities = np.array(spectral_data["intensities"])
            current_scans = current_config.get('scans_to_average', 10)
            
            # Calculate noise level
            noise_level = np.std(intensities)
            mean_intensity = np.mean(intensities)
            
            # Target noise reduction
            target_noise_reduction = 0.5  # 50% noise reduction
            
            # Noise reduces with sqrt(N) where N is number of scans
            current_noise_reduction = 1.0 / np.sqrt(current_scans)
            required_scans = int((1.0 / (target_noise_reduction * current_noise_reduction)) ** 2)
            
            # Constrain to reasonable range
            min_scans = self.spectrometer_types['generic']['parameters']['scans_to_average'].min_value
            max_scans = self.spectrometer_types['generic']['parameters']['scans_to_average'].max_value
            recommended_scans = max(min_scans, min(max_scans, required_scans))
            
            if recommended_scans > current_scans:
                improvement = (recommended_scans - current_scans) / current_scans * 100
                return ParameterRecommendation(
                    parameter="scans_to_average",
                    current_value=current_scans,
                    recommended_value=recommended_scans,
                    reason=f"Increase scans to achieve better noise reduction (current: {current_noise_reduction:.2%}, target: {target_noise_reduction:.2%})",
                    impact="medium",
                    confidence=0.85,
                    optimization_direction="increase",
                    expected_improvement=improvement * 0.5,  # Noise reduction is sqrt(N)
                    validation_required=True
                )
            else:
                improvement = (current_scans - recommended_scans) / current_scans * 100
                return ParameterRecommendation(
                    parameter="scans_to_average",
                    current_value=current_scans,
                    recommended_value=recommended_scans,
                    reason=f"Current scans provide sufficient noise reduction, can be reduced",
                    impact="low",
                    confidence=0.7,
                    optimization_direction="decrease",
                    expected_improvement=improvement,
                    validation_required=True
                )
                
        except Exception as e:
            self.logger.error(f"Scans to average recommendation failed: {e}")
            return ParameterRecommendation(
                parameter="scans_to_average",
                current_value=current_config.get('scans_to_average', 10),
                recommended_value=10,
                reason="Error in recommendation calculation",
                impact="low",
                confidence=0.1,
                optimization_direction="set_to",
                expected_improvement=0.0,
                validation_required=True
            )
    
    def recommend_gain_setting(self, spectral_data: Dict[str, Any], 
                               current_config: Dict[str, Any]) -> ParameterRecommendation:
        """Recommend optimal gain setting"""
        try:
            intensities = np.array(spectral_data["intensities"])
            current_gain = current_config.get('gain', 20)
            
            # Calculate current signal level
            max_intensity = np.max(intensities)
            min_intensity = np.min(intensities)
            signal_range = max_intensity - min_intensity
            
            # Ideal signal range should be 70-80% of full scale
            ideal_range = 0.75  # 75% of full scale
            
            # Calculate current utilization - use practical range for float data
            if np.issubdtype(intensities.dtype, np.integer):
                max_val = np.iinfo(intensities.dtype).max
                min_val = np.iinfo(intensities.dtype).min
            else:
                # For float data, use the actual data range as reference
                max_val = np.max(intensities) * 1.1  # 10% headroom
                min_val = np.min(intensities) * 0.9  # 10% headroom
                if max_val == min_val:
                    max_val = min_val + 1.0  # Avoid division by zero
            
            range_span = max_val - min_val
            if range_span > 0:
                current_utilization = signal_range / range_span
            else:
                current_utilization = 0.0
            
            if current_utilization < ideal_range * 0.8:
                # Signal is too low, increase gain
                gain_increase = (ideal_range / current_utilization) - 1
                recommended_gain = min(
                    self.spectrometer_types['generic']['parameters']['gain'].max_value,
                    current_gain * (1 + gain_increase)
                )
                
                return ParameterRecommendation(
                    parameter="gain",
                    current_value=current_gain,
                    recommended_value=int(recommended_gain),
                    reason=f"Signal utilization low ({current_utilization:.1%}), increase gain to improve SNR",
                    impact="high",
                    confidence=0.85,
                    optimization_direction="increase",
                    expected_improvement=gain_increase * 50,  # Approximate SNR improvement
                    validation_required=True
                )
            elif current_utilization > ideal_range * 1.2:
                # Signal is too high, decrease gain to avoid saturation
                gain_decrease = 1 - (ideal_range / current_utilization)
                recommended_gain = max(
                    self.spectrometer_types['generic']['parameters']['gain'].min_value,
                    current_gain * (1 - gain_decrease)
                )
                
                return ParameterRecommendation(
                    parameter="gain",
                    current_value=current_gain,
                    recommended_value=int(recommended_gain),
                    reason=f"Signal utilization high ({current_utilization:.1%}), decrease gain to avoid saturation",
                    impact="high",
                    confidence=0.9,
                    optimization_direction="decrease",
                    expected_improvement=0.0,  # No SNR improvement, just avoiding saturation
                    validation_required=True
                )
            else:
                return ParameterRecommendation(
                    parameter="gain",
                    current_value=current_gain,
                    recommended_value=current_gain,
                    reason="Current gain setting is optimal",
                    impact="low",
                    confidence=0.95,
                    optimization_direction="set_to",
                    expected_improvement=0.0,
                    validation_required=False
                )
                
        except Exception as e:
            self.logger.error(f"Gain recommendation failed: {e}")
            return ParameterRecommendation(
                parameter="gain",
                current_value=current_config.get('gain', 20),
                recommended_value=20,
                reason="Error in recommendation calculation",
                impact="low",
                confidence=0.1,
                optimization_direction="set_to",
                expected_improvement=0.0,
                validation_required=True
            )
    
    def recommend_wavelength_range(self, spectral_data: Dict[str, Any], 
                                   current_config: Dict[str, Any]) -> ParameterRecommendation:
        """Recommend optimal wavelength range"""
        try:
            wavelengths = np.array(spectral_data["wavelengths"])
            intensities = np.array(spectral_data["intensities"])
            
            current_min_wl = wavelengths[0]
            current_max_wl = wavelengths[-1]
            
            # Find useful spectral range (where signal is above noise floor)
            noise_floor = np.percentile(intensities, 10)  # 10th percentile as noise floor
            signal_threshold = noise_floor * 1.5  # 50% above noise floor
            
            # Find indices where signal is above threshold
            useful_indices = np.where(intensities > signal_threshold)[0]
            
            if len(useful_indices) > 0:
                useful_min_idx = useful_indices[0]
                useful_max_idx = useful_indices[-1]
                
                useful_min_wl = wavelengths[useful_min_idx]
                useful_max_wl = wavelengths[useful_max_idx]
                
                # Recommend expanding range if significant signal outside current range
                if useful_min_wl < current_min_wl + 50:  # 50nm buffer
                    recommended_min_wl = max(
                        self.wavelength_range[0],
                        useful_min_wl - 20  # Add 20nm buffer
                    )
                else:
                    recommended_min_wl = current_min_wl
                    
                if useful_max_wl > current_max_wl - 50:  # 50nm buffer
                    recommended_max_wl = min(
                        self.wavelength_range[1],
                        useful_max_wl + 20  # Add 20nm buffer
                    )
                else:
                    recommended_max_wl = current_max_wl
                
                if recommended_min_wl != current_min_wl or recommended_max_wl != current_max_wl:
                    return ParameterRecommendation(
                        parameter="wavelength_range",
                        current_value=(current_min_wl, current_max_wl),
                        recommended_value=(recommended_min_wl, recommended_max_wl),
                        reason=f"Expand wavelength range to capture useful signal from {useful_min_wl:.0f}-{useful_max_wl:.0f} nm",
                        impact="medium",
                        confidence=0.8,
                        optimization_direction="set_to",
                        expected_improvement=10.0,  # 10% improvement in data coverage
                        validation_required=True
                    )
                else:
                    return ParameterRecommendation(
                        parameter="wavelength_range",
                        current_value=(current_min_wl, current_max_wl),
                        recommended_value=(current_min_wl, current_max_wl),
                        reason="Current wavelength range is optimal",
                        impact="low",
                        confidence=0.9,
                        optimization_direction="set_to",
                        expected_improvement=0.0,
                        validation_required=False
                    )
            else:
                # No useful signal found, recommend default range
                return ParameterRecommendation(
                    parameter="wavelength_range",
                    current_value=(current_min_wl, current_max_wl),
                    recommended_value=self.wavelength_range,
                    reason="No useful signal detected, recommend standard NIR range",
                    impact="high",
                    confidence=0.7,
                    optimization_direction="set_to",
                    expected_improvement=0.0,
                    validation_required=True
                )
                
        except Exception as e:
            self.logger.error(f"Wavelength range recommendation failed: {e}")
            return ParameterRecommendation(
                parameter="wavelength_range",
                current_value=current_config.get('wavelength_range', self.wavelength_range),
                recommended_value=self.wavelength_range,
                reason="Error in recommendation calculation",
                impact="low",
                confidence=0.1,
                optimization_direction="set_to",
                expected_improvement=0.0,
                validation_required=True
            )
    
    def recommend_temperature_compensation(self, spectral_data: Dict[str, Any], 
                                          current_config: Dict[str, Any]) -> ParameterRecommendation:
        """Recommend temperature compensation settings"""
        try:
            # Check if temperature compensation is enabled
            temp_comp_enabled = current_config.get('temperature_compensation', True)
            
            # For NIR spectroscopy, temperature compensation is usually beneficial
            if not temp_comp_enabled:
                return ParameterRecommendation(
                    parameter="temperature_compensation",
                    current_value=False,
                    recommended_value=True,
                    reason="Temperature compensation improves measurement stability in NIR spectroscopy",
                    impact="high",
                    confidence=0.95,
                    optimization_direction="set_to",
                    expected_improvement=15.0,  # 15% improvement in stability
                    validation_required=False
                )
            else:
                return ParameterRecommendation(
                    parameter="temperature_compensation",
                    current_value=True,
                    recommended_value=True,
                    reason="Temperature compensation is properly enabled",
                    impact="low",
                    confidence=1.0,
                    optimization_direction="set_to",
                    expected_improvement=0.0,
                    validation_required=False
                )
                
        except Exception as e:
            self.logger.error(f"Temperature compensation recommendation failed: {e}")
            return ParameterRecommendation(
                parameter="temperature_compensation",
                current_value=current_config.get('temperature_compensation', True),
                recommended_value=True,
                reason="Error in recommendation calculation",
                impact="low",
                confidence=0.1,
                optimization_direction="set_to",
                expected_improvement=0.0,
                validation_required=False
            )
    
    def generate_comprehensive_recommendations(self, spectral_data: Dict[str, Any], 
                                              current_config: Dict[str, Any],
                                              spectrometer_type: str = 'generic') -> ParameterRecommendationReport:
        """Generate comprehensive parameter recommendations"""
        import time
        
        start_time = time.time()
        
        try:
            sample_id = spectral_data.get('sample_id', 'unknown')
            wavelengths = np.array(spectral_data["wavelengths"])
            
            # Analyze current configuration
            current_analysis = self.analyze_current_configuration(spectral_data, current_config)
            
            # Generate individual parameter recommendations
            recommendations = []
            
            # Integration time recommendation
            integration_rec = self.recommend_integration_time(spectral_data, current_config)
            recommendations.append(integration_rec)
            
            # Scans to average recommendation
            scans_rec = self.recommend_scans_to_average(spectral_data, current_config)
            recommendations.append(scans_rec)
            
            # Gain setting recommendation
            if 'gain' in current_config or 'gain' in self.spectrometer_types[spectrometer_type]['parameters']:
                gain_rec = self.recommend_gain_setting(spectral_data, current_config)
                recommendations.append(gain_rec)
            
            # Wavelength range recommendation
            wavelength_rec = self.recommend_wavelength_range(spectral_data, current_config)
            recommendations.append(wavelength_rec)
            
            # Temperature compensation recommendation
            temp_rec = self.recommend_temperature_compensation(spectral_data, current_config)
            recommendations.append(temp_rec)
            
            # Dark correction recommendation (always enable for NIR)
            dark_corr_rec = ParameterRecommendation(
                parameter="dark_correction",
                current_value=current_config.get('dark_correction', True),
                recommended_value=True,
                reason="Dark current correction is essential for accurate NIR measurements",
                impact="high",
                confidence=1.0,
                optimization_direction="set_to",
                expected_improvement=20.0,
                validation_required=False
            )
            recommendations.append(dark_corr_rec)
            
            # Categorize recommendations by priority
            high_priority = []
            medium_priority = []
            low_priority = []
            
            for rec in recommendations:
                if rec.impact in ["high", "critical"]:
                    high_priority.append(rec)
                elif rec.impact == "medium":
                    medium_priority.append(rec)
                else:
                    low_priority.append(rec)
            
            # Calculate overall improvement potential
            total_improvement = sum(rec.expected_improvement for rec in recommendations)
            
            # Determine if configuration is optimized
            configuration_optimized = len(high_priority) == 0 and len(medium_priority) == 0
            
            # Generate implementation steps
            implementation_steps = self._generate_implementation_steps(recommendations)
            
            # Generate validation requirements
            validation_requirements = self._generate_validation_requirements(recommendations)
            
            # Determine overall grade
            overall_quality = current_analysis.get('overall_quality', 50)
            if overall_quality >= 90:
                grade = "excellent"
            elif overall_quality >= 75:
                grade = "good"
            elif overall_quality >= 50:
                grade = "fair"
            else:
                grade = "poor"
            
            # Create comprehensive report
            report = ParameterRecommendationReport(
                sample_id=sample_id,
                timestamp=datetime.now().isoformat(),
                spectrometer_type=spectrometer_type,
                wavelength_range=(float(wavelengths[0]), float(wavelengths[-1])),
                current_configuration=current_config,
                parameter_recommendations=recommendations,
                optimization_results=[],  # Would be populated by optimization algorithms
                overall_quality_score=overall_quality,
                overall_grade=grade,
                configuration_optimized=configuration_optimized,
                expected_improvement=total_improvement,
                high_priority_recommendations=high_priority,
                medium_priority_recommendations=medium_priority,
                low_priority_recommendations=low_priority,
                implementation_steps=implementation_steps,
                validation_requirements=validation_requirements,
                metadata=spectral_data.get('metadata', {})
            )
            
            # Store results
            self.recommendation_results[sample_id] = report
            self.stats['analyses_performed'] += 1
            self.stats['recommendations_generated'] += len(recommendations)
            self.stats['processing_time'] += time.time() - start_time
            
            return report
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Comprehensive recommendation generation failed: {e}")
            
            # Return minimal report on error
            return ParameterRecommendationReport(
                sample_id=spectral_data.get('sample_id', 'error'),
                timestamp=datetime.now().isoformat(),
                spectrometer_type=spectrometer_type,
                current_configuration=current_config,
                parameter_recommendations=[],
                overall_quality_score=0.0,
                overall_grade="error",
                configuration_optimized=False,
                expected_improvement=0.0,
                metadata={"error": str(e)}
            )
    
    def _generate_implementation_steps(self, recommendations: List[ParameterRecommendation]) -> List[str]:
        """Generate step-by-step implementation guidance"""
        steps = []
        
        # Group recommendations by parameter type
        high_priority = [r for r in recommendations if r.impact in ["high", "critical"]]
        medium_priority = [r for r in recommendations if r.impact == "medium"]
        low_priority = [r for r in recommendations if r.impact == "low"]
        
        if high_priority:
            steps.append("HIGH PRIORITY: Address critical parameter issues first")
            for rec in high_priority:
                if rec.validation_required:
                    steps.append(f"  - {rec.parameter}: Change from {rec.current_value} to {rec.recommended_value} (requires validation)")
                else:
                    steps.append(f"  - {rec.parameter}: Change from {rec.current_value} to {rec.recommended_value}")
        
        if medium_priority:
            steps.append("MEDIUM PRIORITY: Optimize performance parameters")
            for rec in medium_priority:
                if rec.validation_required:
                    steps.append(f"  - {rec.parameter}: Change from {rec.current_value} to {rec.recommended_value} (requires validation)")
                else:
                    steps.append(f"  - {rec.parameter}: Change from {rec.current_value} to {rec.recommended_value}")
        
        if low_priority:
            steps.append("LOW PRIORITY: Fine-tune for optimal performance")
            for rec in low_priority:
                steps.append(f"  - {rec.parameter}: Consider changing from {rec.current_value} to {rec.recommended_value}")
        
        steps.append("After making changes, re-run analysis to verify improvements")
        
        return steps
    
    def _generate_validation_requirements(self, recommendations: List[ParameterRecommendation]) -> List[str]:
        """Generate validation requirements for parameter changes"""
        requirements = []
        
        validation_needed = [r for r in recommendations if r.validation_required]
        
        if validation_needed:
            requirements.append("VALIDATION REQUIRED: The following parameter changes require validation:")
            for rec in validation_needed:
                requirements.append(f"  - {rec.parameter}: {rec.reason}")
            
            requirements.append("")
            requirements.append("Validation procedures:")
            requirements.append("  1. Run test measurements with current and new parameters")
            requirements.append("  2. Compare SNR, resolution, and stability metrics")
            requirements.append("  3. Verify that measurements are within expected ranges")
            requirements.append("  4. Check for saturation or clipping in the new configuration")
            requirements.append("  5. Document any changes and their impact on measurement quality")
        else:
            requirements.append("No specific validation required for recommended changes")
        
        return requirements
    
    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute the parameter recommender agent's primary function"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting ParameterRecommenderAgent execution")
            
            # Extract data from context
            spectral_data = context.get('spectral_data', {})
            current_config = context.get('current_config', {})
            spectrometer_type = context.get('spectrometer_type', 'generic')
            
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
            
            # Generate comprehensive recommendations
            report = self.generate_comprehensive_recommendations(
                spectral_data, current_config, spectrometer_type
            )
            
            self.status = AgentStatus.COMPLETED
            self.logger.info(f"Parameter recommendation completed for sample {spectral_data.get('sample_id', 'unknown')}")
            
            return self._create_success_output({
                "status": "completed",
                "message": "Parameter recommendation analysis completed successfully",
                "sample_id": spectral_data.get('sample_id', 'unknown'),
                "report": report.__dict__,
                "stats": self.stats
            })
            
        except Exception as e:
            self.stats['errors'] += 1
            return self._handle_error(e)
    
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
    agent = ParameterRecommenderAgent()
    output = agent.initialize()
    print(f"ParameterRecommenderAgent initialized: {output.status.name}")
    
    # Test with sample data
    test_context = {
        "sample_id": "test_sample_001",
        "spectral_data": {
            "wavelengths": list(range(700, 2500, 10)),
            "intensities": [abs(np.sin(i * 0.01)) * 1000 + np.random.normal(0, 50) for i in range(700, 2500, 10)],
            "metadata": {"instrument": "test_spectrometer"}
        },
        "current_config": {
            "integration_time": 100,
            "scans_to_average": 10,
            "gain": 20,
            "wavelength_range": (700, 2500),
            "temperature_compensation": True,
            "dark_correction": True
        },
        "spectrometer_type": "generic",
        "metadata": {"test": True}
    }
    
    result = agent.execute(test_context)
    print(f"Execution result: {result.status.name}")
    if result.data.get("report"):
        report = result.data["report"]
        print(f"Recommendations generated: {len(report.get('parameter_recommendations', []))}")
        print(f"Overall quality score: {report.get('overall_quality_score', 0)}")
        print(f"Expected improvement: {report.get('expected_improvement', 0)}%")
        print(f"High priority recommendations: {len(report.get('high_priority_recommendations', []))}")
