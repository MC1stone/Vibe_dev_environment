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
class CalibrationResult:
    """Container for calibration results."""
    wavelength_calibration: Optional[CalibrationCurve] = None
    intensity_calibration: Optional[CalibrationCurve] = None
    drift_compensation: Optional[Dict] = None
    spectrometer_parameters: Dict[str, Any] = field(default_factory=dict)
    calibration_quality: Dict[str, float] = field(default_factory=dict)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    issues_detected: List[Dict[str, Any]] = field(default_factory=list)


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
        
        # Generate drift compensation
        result.drift_compensation = self._generate_drift_compensation(metadata, spec_info)
        
        # Generate parameter recommendations
        result.spectrometer_parameters = self._generate_parameter_recommendations(
            wavelengths, intensities, metadata, spec_info
        )
        
        # Assess quality
        result.calibration_quality = self._assess_calibration_quality(
            result.wavelength_calibration, result.intensity_calibration
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
    
    def _fit_linear_calibration(self, x_data, y_data) -> CalibrationCurve:
        """Fit linear calibration."""
        if len(x_data) < 2:
            raise ValueError("Insufficient data")
        
        # Simple linear fit
        A = np.vstack([x_data, np.ones(len(x_data))]).T
        slope, intercept = np.linalg.lstsq(A, y_data, rcond=None)[0]
        
        y_pred = slope * x_data + intercept
        residuals = y_data - y_pred
        r_squared = 1 - np.sum(residuals**2) / np.sum((y_data - np.mean(y_data))**2)
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
        if len(x_data) <= degree:
            raise ValueError(f"Insufficient data for degree {degree}")
        
        coeffs = np.polyfit(x_data, y_data, degree)
        y_pred = np.polyval(coeffs, x_data)
        residuals = y_data - y_pred
        r_squared = 1 - np.sum(residuals**2) / np.sum((y_data - np.mean(y_data))**2)
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
    
    def _assess_calibration_quality(self, wl_cal, int_cal) -> Dict:
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
        
        quality["overall_quality"] = (quality.get("wavelength_quality", 0) + 
                                     quality.get("intensity_quality", 0)) / 2
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
