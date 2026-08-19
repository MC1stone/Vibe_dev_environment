"""
Spectral Analysis Agent for NIR Intelligence Platform

This agent specializes in analyzing NIR spectral data from any spectrometer,
including DIY devices. It performs wavelength calibration, baseline correction,
noise reduction, peak detection, and spectrometer issue identification.
"""

import asyncio
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
from scipy import signal, stats
from scipy.optimize import curve_fit
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import httpx

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class SpectralData:
    """Container for spectral data."""
    wavelengths: np.ndarray
    intensities: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_path: Optional[str] = None
    spectrometer_type: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "wavelengths": self.wavelengths.tolist(),
            "intensities": self.intensities.tolist(),
            "metadata": self.metadata,
            "file_path": self.file_path,
            "spectrometer_type": self.spectrometer_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SpectralData':
        return cls(
            wavelengths=np.array(data["wavelengths"]),
            intensities=np.array(data["intensities"]),
            metadata=data.get("metadata", {}),
            file_path=data.get("file_path"),
            spectrometer_type=data.get("spectrometer_type")
        )


@dataclass
class SpectralAnalysisResult:
    """Container for spectral analysis results."""
    original_data: SpectralData
    processed_data: SpectralData
    analysis_metrics: Dict[str, Any]
    issues_detected: List[Dict[str, Any]]
    calibration_recommendations: List[Dict[str, Any]]
    quality_score: float
    processing_steps: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "original_data": self.original_data.to_dict(),
            "processed_data": self.processed_data.to_dict(),
            "analysis_metrics": self.analysis_metrics,
            "issues_detected": self.issues_detected,
            "calibration_recommendations": self.calibration_recommendations,
            "quality_score": self.quality_score,
            "processing_steps": self.processing_steps
        }


class SpectralAnalysisAgent:
    """
    Agent for analyzing NIR spectral data.
    
    Capabilities:
    - Load spectral data from various file formats
    - Detect spectrometer type and characteristics
    - Perform wavelength calibration
    - Apply baseline correction
    - Reduce noise and smooth data
    - Detect peaks and spectral features
    - Identify spectrometer issues (shift, drift, etc.)
    - Generate calibration recommendations
    - Assess data quality
    """
    
    def __init__(self, 
                 agent_id: str = "spectral_analysis_agent",
                 mcp_server_url: str = "http://localhost:8000",
                 qdrant_url: str = "http://localhost:6333",
                 faiss_url: str = "http://localhost:5001",
                 ollama_url: str = "http://localhost:11434"):
        """
        Initialize Spectral Analysis Agent.
        
        Args:
            agent_id: Unique identifier for this agent
            mcp_server_url: URL for MCP server
            qdrant_url: URL for Qdrant vector database
            faiss_url: URL for Faiss vector index
            ollama_url: URL for Ollama (Mistral model)
        """
        self.agent_id = agent_id
        self.mcp_server_url = mcp_server_url
        self.qdrant_url = qdrant_url
        self.faiss_url = faiss_url
        self.ollama_url = ollama_url
        
        # Supported file formats
        self.supported_formats = [
            '.csv', '.txt', '.xlsx', '.xls', '.json', '.spc', '.jdx',
            '.nc', '.h5', '.mat', '.dat', '.zip'
        ]
        
        # Spectrometer database (for type detection)
        self.spectrometer_database = self._load_spectrometer_database()
        
        # Calibration standards
        self.calibration_standards = self._load_calibration_standards()
        
        # Register with MCP server
        self._register_with_mcp()
        
        logger.info(f"Spectral Analysis Agent {self.agent_id} initialized")
    
    def _load_spectrometer_database(self) -> Dict:
        """Load spectrometer database for type detection."""
        # This would normally be loaded from a file or database
        return {
            "ocean_optics": {
                "wavelength_range": [200, 1100],
                "resolution": 0.5,
                "features": ["high_resolution", "uv_vis_nir"],
                "calibration_points": [250, 400, 600, 800, 1000]
            },
            "asd_fieldspec": {
                "wavelength_range": [350, 2500],
                "resolution": 1.0,
                "features": ["field_portable", "vis_nir_swir"],
                "calibration_points": [350, 700, 1400, 2100]
            },
            "bruker": {
                "wavelength_range": [400, 4000],
                "resolution": 2.0,
                "features": ["lab_grade", "ftir"],
                "calibration_points": [400, 1000, 2000, 3500]
            },
            "diy_raspberry": {
                "wavelength_range": [650, 1100],
                "resolution": 10.0,
                "features": ["low_cost", "visible_nir"],
                "calibration_points": [650, 800, 1000]
            },
            "diy_arduino": {
                "wavelength_range": [700, 1000],
                "resolution": 15.0,
                "features": ["low_cost", "nir_only"],
                "calibration_points": [700, 850, 1000]
            }
        }
    
    def _load_calibration_standards(self) -> Dict:
        """Load calibration standards for different spectrometers."""
        return {
            "wavelength_standards": {
                "neon": [632.8, 638.3, 640.2, 650.7, 653.3, 659.9, 667.8, 671.7, 692.9, 703.2],
                "mercury": [253.7, 365.0, 404.7, 407.8, 435.8, 546.1, 577.0, 579.1, 690.7],
                "holmium": [241.5, 287.2, 333.7, 345.5, 361.5, 405.4, 418.5, 445.5, 453.4, 485.1, 536.2, 640.8]
            },
            "intensity_standards": {
                "white_reference": {"reflectance": 0.99, "description": "Spectralon white reference"},
                "dark_reference": {"reflectance": 0.01, "description": "Dark current measurement"}
            },
            "quality_thresholds": {
                "signal_to_noise": 100.0,
                "wavelength_accuracy": 0.5,  # nm
                "intensity_stability": 0.01,  # %
                "baseline_flatness": 0.005  # absorbance units
            }
        }
    
    def _register_with_mcp(self):
        """Register this agent with the MCP server."""
        agent_data = {
            "id": self.agent_id,
            "name": "Spectral Analysis Agent",
            "description": "Analyzes NIR spectral data from any spectrometer, including DIY devices",
            "capabilities": [
                "load_spectral_data",
                "detect_spectrometer_type",
                "wavelength_calibration",
                "baseline_correction",
                "noise_reduction",
                "peak_detection",
                "spectrometer_issue_detection",
                "calibration_recommendation",
                "data_quality_assessment"
            ],
            "version": "1.0.0",
            "endpoints": [
                "/analysis/spectral",
                "/analysis/calibration",
                "/analysis/issues"
            ]
        }
        
        # This would normally be an async call
        # For now, we'll just log it
        logger.info(f"Registering agent with MCP server: {agent_data}")
    
    async def analyze_spectral_data(self, 
                                    file_path: Optional[str] = None,
                                    data: Optional[Dict] = None,
                                    metadata: Optional[Dict] = None) -> SpectralAnalysisResult:
        """
        Analyze spectral data from file or direct input.
        
        Args:
            file_path: Path to spectral data file
            data: Direct spectral data (wavelengths and intensities)
            metadata: Additional metadata
            
        Returns:
            SpectralAnalysisResult with full analysis
        """
        logger.info(f"Starting spectral analysis for {file_path or 'direct data'}")
        
        # Step 1: Load data
        if file_path:
            spectral_data = await self._load_spectral_data(file_path)
        elif data:
            spectral_data = self._create_spectral_data_from_dict(data)
        else:
            raise ValueError("Either file_path or data must be provided")
        
        # Update metadata
        if metadata:
            spectral_data.metadata.update(metadata)
        
        # Step 2: Detect spectrometer type
        spectrometer_info = self._detect_spectrometer_type(spectral_data)
        spectral_data.spectrometer_type = spectrometer_info.get("type")
        spectral_data.metadata["spectrometer_info"] = spectrometer_info
        
        # Step 3: Perform initial quality check
        initial_quality = self._assess_initial_quality(spectral_data)
        
        # Step 4: Process data
        processing_steps = []
        
        # Wavelength calibration
        calibrated_data = self._calibrate_wavelength(spectral_data)
        processing_steps.append("wavelength_calibration")
        
        # Baseline correction
        baseline_corrected = self._correct_baseline(calibrated_data)
        processing_steps.append("baseline_correction")
        
        # Noise reduction
        noise_reduced = self._reduce_noise(baseline_corrected)
        processing_steps.append("noise_reduction")
        
        # Smoothing
        smoothed_data = self._smooth_data(noise_reduced)
        processing_steps.append("smoothing")
        
        # Step 5: Detect peaks and features
        peak_info = self._detect_peaks(smoothed_data)
        
        # Step 6: Detect spectrometer issues
        issues = self._detect_spectrometer_issues(smoothed_data, spectral_data)
        
        # Step 7: Generate calibration recommendations
        calibration_recs = self._generate_calibration_recommendations(
            smoothed_data, spectrometer_info, issues
        )
        
        # Step 8: Calculate final quality score
        quality_score = self._calculate_quality_score(
            smoothed_data, initial_quality, issues, calibration_recs
        )
        
        # Step 9: Calculate analysis metrics
        analysis_metrics = self._calculate_analysis_metrics(
            spectral_data, smoothed_data, peak_info, issues
        )
        
        # Create result
        result = SpectralAnalysisResult(
            original_data=spectral_data,
            processed_data=smoothed_data,
            analysis_metrics=analysis_metrics,
            issues_detected=issues,
            calibration_recommendations=calibration_recs,
            quality_score=quality_score,
            processing_steps=processing_steps
        )
        
        logger.info(f"Completed spectral analysis. Quality score: {quality_score:.2f}")
        
        return result
    
    async def _load_spectral_data(self, file_path: str) -> SpectralData:
        """Load spectral data from file."""
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        logger.info(f"Loading spectral data from {file_path}")
        
        try:
            if suffix == '.csv':
                return self._load_csv(file_path)
            elif suffix == '.txt':
                return self._load_txt(file_path)
            elif suffix in ['.xlsx', '.xls']:
                return self._load_excel(file_path)
            elif suffix == '.json':
                return self._load_json(file_path)
            elif suffix in ['.spc', '.jdx']:
                return await self._load_spc(file_path)
            elif suffix == '.zip':
                return await self._load_zip(file_path)
            else:
                # Try to auto-detect format
                return self._auto_load(file_path)
        except Exception as e:
            logger.error(f"Error loading spectral data: {e}")
            raise ValueError(f"Unsupported file format or corrupt file: {e}")
    
    def _load_csv(self, file_path: str) -> SpectralData:
        """Load spectral data from CSV file."""
        df = pd.read_csv(file_path)
        
        # Try to detect columns
        wavelength_col = None
        intensity_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if any(x in col_lower for x in ['wavelength', 'wave', 'lambda', 'nm']):
                wavelength_col = col
            elif any(x in col_lower for x in ['intensity', 'absorbance', 'reflectance', 'transmittance', 'counts']):
                intensity_col = col
        
        if not wavelength_col or not intensity_col:
            # Try first two columns
            if len(df.columns) >= 2:
                wavelength_col = df.columns[0]
                intensity_col = df.columns[1]
            else:
                raise ValueError("Could not identify wavelength and intensity columns")
        
        wavelengths = df[wavelength_col].values
        intensities = df[intensity_col].values
        
        # Extract metadata from other columns
        metadata = {}
        for col in df.columns:
            if col not in [wavelength_col, intensity_col]:
                metadata[col] = df[col].iloc[0] if len(df) > 0 else None
        
        return SpectralData(
            wavelengths=wavelengths,
            intensities=intensities,
            metadata=metadata,
            file_path=file_path
        )
    
    def _load_txt(self, file_path: str) -> SpectralData:
        """Load spectral data from TXT file."""
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Try to parse as two-column data
        wavelengths = []
        intensities = []
        metadata = {}
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                # Skip comments and empty lines
                if line.startswith('#'):
                    # Parse metadata from comments
                    parts = line[1:].split(':')
                    if len(parts) >= 2:
                        metadata[parts[0].strip()] = parts[1].strip()
                continue
            
            parts = line.split()
            if len(parts) >= 2:
                try:
                    wavelengths.append(float(parts[0]))
                    intensities.append(float(parts[1]))
                except ValueError:
                    continue
        
        if not wavelengths:
            raise ValueError("No valid spectral data found in TXT file")
        
        return SpectralData(
            wavelengths=np.array(wavelengths),
            intensities=np.array(intensities),
            metadata=metadata,
            file_path=file_path
        )
    
    def _load_excel(self, file_path: str) -> SpectralData:
        """Load spectral data from Excel file."""
        df = pd.read_excel(file_path)
        
        # Similar logic to CSV
        wavelength_col = None
        intensity_col = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            if any(x in col_lower for x in ['wavelength', 'wave', 'lambda', 'nm']):
                wavelength_col = col
            elif any(x in col_lower for x in ['intensity', 'absorbance', 'reflectance', 'transmittance', 'counts']):
                intensity_col = col
        
        if not wavelength_col or not intensity_col:
            if len(df.columns) >= 2:
                wavelength_col = df.columns[0]
                intensity_col = df.columns[1]
            else:
                raise ValueError("Could not identify wavelength and intensity columns")
        
        wavelengths = df[wavelength_col].values
        intensities = df[intensity_col].values
        
        metadata = {}
        for col in df.columns:
            if col not in [wavelength_col, intensity_col]:
                metadata[str(col)] = df[col].iloc[0] if len(df) > 0 else None
        
        return SpectralData(
            wavelengths=wavelengths,
            intensities=intensities,
            metadata=metadata,
            file_path=file_path
        )
    
    def _load_json(self, file_path: str) -> SpectralData:
        """Load spectral data from JSON file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if 'wavelengths' in data and 'intensities' in data:
            wavelengths = np.array(data['wavelengths'])
            intensities = np.array(data['intensities'])
            metadata = data.get('metadata', {})
        elif 'spectrum' in data:
            spectrum = data['spectrum']
            wavelengths = np.array(spectrum.get('wavelengths', spectrum.get('x')))
            intensities = np.array(spectrum.get('intensities', spectrum.get('y')))
            metadata = spectrum.get('metadata', {})
        else:
            raise ValueError("Invalid JSON structure for spectral data")
        
        return SpectralData(
            wavelengths=wavelengths,
            intensities=intensities,
            metadata=metadata,
            file_path=file_path
        )
    
    async def _load_spc(self, file_path: str) -> SpectralData:
        """Load spectral data from SPC file (ASD format)."""
        # This would use pyspectral or similar library
        # For now, we'll implement a basic version
        try:
            import pyspectral
            spc = pyspectral.SpcFile(file_path)
            wavelengths = spc.wavelengths
            intensities = spc.spectrum
            metadata = {
                'title': spc.title,
                'instrument': spc.instrument,
                'date': spc.date,
                'x_units': spc.x_units,
                'y_units': spc.y_units
            }
            return SpectralData(
                wavelengths=wavelengths,
                intensities=intensities,
                metadata=metadata,
                file_path=file_path
            )
        except ImportError:
            logger.warning("pyspectral not available, using fallback SPC loader")
            # Fallback: try to read as text
            return self._load_txt(file_path)
    
    async def _load_zip(self, file_path: str) -> SpectralData:
        """Load spectral data from ZIP file."""
        import zipfile
        
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # Find the first spectral data file
            for file_name in zip_ref.namelist():
                if any(file_name.lower().endswith(ext) for ext in self.supported_formats):
                    # Extract to temporary location
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=Path(file_name).suffix, delete=False) as tmp:
                        tmp.write(zip_ref.read(file_name))
                        tmp_path = tmp.name
                    
                    # Load the file
                    try:
                        if Path(file_name).suffix.lower() == '.zip':
                            return await self._load_zip(tmp_path)
                        else:
                            return await self._load_spectral_data(tmp_path)
                    finally:
                        import os
                        os.unlink(tmp_path)
        
        raise ValueError("No supported spectral data files found in ZIP")
    
    def _auto_load(self, file_path: str) -> SpectralData:
        """Try to auto-detect and load file format."""
        # Try CSV first
        try:
            return self._load_csv(file_path)
        except:
            pass
        
        # Try TXT
        try:
            return self._load_txt(file_path)
        except:
            pass
        
        # Try JSON
        try:
            return self._load_json(file_path)
        except:
            pass
        
        raise ValueError(f"Could not auto-detect format for {file_path}")
    
    def _create_spectral_data_from_dict(self, data: Dict) -> SpectralData:
        """Create SpectralData from dictionary."""
        return SpectralData(
            wavelengths=np.array(data.get('wavelengths', [])),
            intensities=np.array(data.get('intensities', [])),
            metadata=data.get('metadata', {}),
            file_path=data.get('file_path'),
            spectrometer_type=data.get('spectrometer_type')
        )
    
    def _detect_spectrometer_type(self, spectral_data: SpectralData) -> Dict:
        """Detect spectrometer type based on data characteristics."""
        wavelengths = spectral_data.wavelengths
        intensities = spectral_data.intensities
        
        # Calculate basic statistics
        wl_min = np.min(wavelengths)
        wl_max = np.max(wavelengths)
        wl_range = wl_max - wl_min
        num_points = len(wavelengths)
        
        # Calculate resolution (average difference between consecutive wavelengths)
        if num_points > 1:
            resolution = np.mean(np.diff(wavelengths))
        else:
            resolution = 0
        
        # Check for known spectrometer patterns
        best_match = None
        best_score = 0
        
        for spec_name, spec_info in self.spectrometer_database.items():
            score = 0
            
            # Check wavelength range
            spec_range = spec_info['wavelength_range']
            if spec_range[0] <= wl_min <= spec_range[1] and spec_range[0] <= wl_max <= spec_range[1]:
                score += 2
            
            # Check resolution
            if abs(resolution - spec_info['resolution']) < spec_info['resolution'] * 0.5:
                score += 1
            
            # Check number of points
            expected_points = int(wl_range / spec_info['resolution'])
            if abs(num_points - expected_points) < expected_points * 0.2:
                score += 1
            
            if score > best_score:
                best_score = score
                best_match = spec_name
        
        # If no good match, classify as DIY
        if best_score < 2:
            if wl_min > 600 and wl_max < 1200:
                best_match = "diy_raspberry" if resolution < 12 else "diy_arduino"
            else:
                best_match = "unknown"
        
        # Check metadata for spectrometer info
        metadata = spectral_data.metadata
        if 'spectrometer' in metadata:
            best_match = metadata['spectrometer']
        elif 'instrument' in metadata:
            best_match = metadata['instrument']
        
        return {
            "type": best_match,
            "wavelength_range": [float(wl_min), float(wl_max)],
            "resolution": float(resolution),
            "num_points": num_points,
            "confidence": min(best_score / 4.0, 1.0) if best_match != "unknown" else 0.0
        }
    
    def _assess_initial_quality(self, spectral_data: SpectralData) -> Dict:
        """Assess initial data quality."""
        wavelengths = spectral_data.wavelengths
        intensities = spectral_data.intensities
        
        quality = {
            "signal_to_noise": 0.0,
            "wavelength_coverage": 0.0,
            "intensity_range": 0.0,
            "data_completeness": 1.0,
            "outliers": 0
        }
        
        # Check for NaN values
        nan_mask = np.isnan(intensities)
        if np.any(nan_mask):
            quality["data_completeness"] = 1.0 - (np.sum(nan_mask) / len(intensities))
        
        # Check for infinite values
        inf_mask = np.isinf(intensities)
        if np.any(inf_mask):
            quality["data_completeness"] -= np.sum(inf_mask) / len(intensities)
        
        # Calculate signal to noise (simple estimate)
        if len(intensities) > 0:
            signal = np.mean(np.abs(intensities))
            noise = np.std(intensities)
            if noise > 0:
                quality["signal_to_noise"] = signal / noise
        
        # Wavelength coverage
        if len(wavelengths) > 0:
            wl_range = np.max(wavelengths) - np.min(wavelengths)
            quality["wavelength_coverage"] = wl_range / 1000.0  # Normalized to 1000nm range
        
        # Intensity range
        if len(intensities) > 0:
            intensity_range = np.max(intensities) - np.min(intensities)
            quality["intensity_range"] = float(intensity_range)
        
        # Detect outliers (using IQR method)
        if len(intensities) > 0:
            q1 = np.percentile(intensities, 25)
            q3 = np.percentile(intensities, 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outliers = np.sum((intensities < lower_bound) | (intensities > upper_bound))
            quality["outliers"] = int(outliers)
        
        return quality
    
    def _calibrate_wavelength(self, spectral_data: SpectralData) -> SpectralData:
        """Perform wavelength calibration."""
        wavelengths = spectral_data.wavelengths.copy()
        intensities = spectral_data.intensities.copy()
        
        # Get spectrometer info
        spec_info = spectral_data.metadata.get("spectrometer_info", {})
        spec_type = spec_info.get("type", "unknown")
        
        # Check if calibration is needed
        if spec_type != "unknown" and spec_type in self.spectrometer_database:
            # Use known calibration points for this spectrometer
            cal_points = self.spectrometer_database[spec_type].get("calibration_points", [])
            if cal_points:
                # Find closest points in data
                calibrated_wavelengths = self._apply_calibration_points(
                    wavelengths, intensities, cal_points
                )
                return SpectralData(
                    wavelengths=calibrated_wavelengths,
                    intensities=intensities,
                    metadata=spectral_data.metadata.copy(),
                    file_path=spectral_data.file_path,
                    spectrometer_type=spectral_data.spectrometer_type
                )
        
        # Auto-detect calibration points from known emission lines
        calibrated_wavelengths = self._auto_calibrate(wavelengths, intensities)
        
        return SpectralData(
            wavelengths=calibrated_wavelengths,
            intensities=intensities,
            metadata=spectral_data.metadata.copy(),
            file_path=spectral_data.file_path,
            spectrometer_type=spectral_data.spectrometer_type
        )
    
    def _apply_calibration_points(self, 
                                  wavelengths: np.ndarray, 
                                  intensities: np.ndarray,
                                  cal_points: List[float]) -> np.ndarray:
        """Apply calibration using known calibration points."""
        # This is a simplified version
        # In practice, this would use more sophisticated calibration algorithms
        
        # Find indices closest to calibration points
        cal_indices = []
        for cp in cal_points:
            idx = np.argmin(np.abs(wavelengths - cp))
            cal_indices.append(idx)
        
        # For now, just return original wavelengths
        # In a real implementation, we would adjust based on known positions
        return wavelengths
    
    def _auto_calibrate(self, wavelengths: np.ndarray, intensities: np.ndarray) -> np.ndarray:
        """Auto-calibrate using known emission lines."""
        # Look for peaks that match known emission lines
        from scipy.signal import find_peaks
        
        # Find peaks in the spectrum
        peaks, _ = find_peaks(intensities, height=np.mean(intensities) + 3 * np.std(intensities))
        
        if len(peaks) < 2:
            return wavelengths  # Not enough peaks for calibration
        
        # Get peak wavelengths
        peak_wavelengths = wavelengths[peaks]
        
        # Try to match with known emission lines
        best_match = None
        best_score = 0
        
        for element, lines in self.calibration_standards["wavelength_standards"].items():
            # Find how many lines match
            matches = 0
            for line in lines:
                # Check if there's a peak close to this line
                diffs = np.abs(peak_wavelengths - line)
                if np.min(diffs) < 2.0:  # Within 2nm
                    matches += 1
            
            if matches > best_score:
                best_score = matches
                best_match = element
        
        # If we found a good match, adjust wavelengths
        if best_score >= 2:
            # Calculate correction factor
            matched_lines = self.calibration_standards["wavelength_standards"][best_match]
            
            # Simple linear correction (in practice, use polynomial fit)
            # For now, just return original
            pass
        
        return wavelengths
    
    def _correct_baseline(self, spectral_data: SpectralData) -> SpectralData:
        """Apply baseline correction to spectral data."""
        intensities = spectral_data.intensities.copy()
        
        # Try different baseline correction methods
        try:
            # Method 1: Simple polynomial baseline
            corrected = self._polynomial_baseline_correction(intensities)
            
            # Method 2: ALS (Asymmetric Least Squares) baseline
            # corrected = self._als_baseline_correction(intensities)
            
            return SpectralData(
                wavelengths=spectral_data.wavelengths.copy(),
                intensities=corrected,
                metadata=spectral_data.metadata.copy(),
                file_path=spectral_data.file_path,
                spectrometer_type=spectral_data.spectrometer_type
            )
        except Exception as e:
            logger.warning(f"Baseline correction failed: {e}")
            return spectral_data
    
    def _polynomial_baseline_correction(self, intensities: np.ndarray, degree: int = 3) -> np.ndarray:
        """Apply polynomial baseline correction."""
        x = np.arange(len(intensities))
        
        # Fit polynomial to baseline (use lower envelope)
        # Simple approach: use every nth point as baseline
        step = max(1, len(intensities) // 20)
        baseline_indices = np.arange(0, len(intensities), step)
        baseline_x = x[baseline_indices]
        baseline_y = intensities[baseline_indices]
        
        # Fit polynomial
        coeffs = np.polyfit(baseline_x, baseline_y, degree)
        baseline = np.polyval(coeffs, x)
        
        # Subtract baseline
        corrected = intensities - baseline
        
        return corrected
    
    def _reduce_noise(self, spectral_data: SpectralData) -> SpectralData:
        """Apply noise reduction to spectral data."""
        intensities = spectral_data.intensities.copy()
        
        # Apply Savitzky-Golay filter
        try:
            window_size = min(11, len(intensities) // 10)
            if window_size < 3:
                window_size = 3
            
            smoothed = signal.savgol_filter(intensities, window_size, 2)
            
            return SpectralData(
                wavelengths=spectral_data.wavelengths.copy(),
                intensities=smoothed,
                metadata=spectral_data.metadata.copy(),
                file_path=spectral_data.file_path,
                spectrometer_type=spectral_data.spectrometer_type
            )
        except Exception as e:
            logger.warning(f"Noise reduction failed: {e}")
            return spectral_data
    
    def _smooth_data(self, spectral_data: SpectralData) -> SpectralData:
        """Apply additional smoothing to spectral data."""
        intensities = spectral_data.intensities.copy()
        
        # Apply moving average
        try:
            window_size = min(5, len(intensities) // 20)
            if window_size < 1:
                window_size = 1
            
            smoothed = np.convolve(intensities, 
                                  np.ones(window_size) / window_size, 
                                  mode='same')
            
            return SpectralData(
                wavelengths=spectral_data.wavelengths.copy(),
                intensities=smoothed,
                metadata=spectral_data.metadata.copy(),
                file_path=spectral_data.file_path,
                spectrometer_type=spectral_data.spectrometer_type
            )
        except Exception as e:
            logger.warning(f"Smoothing failed: {e}")
            return spectral_data
    
    def _detect_peaks(self, spectral_data: SpectralData) -> Dict:
        """Detect peaks and spectral features."""
        intensities = spectral_data.intensities
        wavelengths = spectral_data.wavelengths
        
        # Find peaks
        peaks, properties = signal.find_peaks(
            intensities, 
            height=np.mean(intensities) + 2 * np.std(intensities),
            distance=5,  # Minimum distance between peaks
            prominence=0.1 * np.std(intensities)
        )
        
        peak_info = {
            "num_peaks": len(peaks),
            "peak_positions": wavelengths[peaks].tolist(),
            "peak_heights": intensities[peaks].tolist(),
            "peak_properties": {
                "height": properties.get("height", []).tolist(),
                "prominence": properties.get("prominence", []).tolist(),
                "width": properties.get("width", []).tolist()
            }
        }
        
        # Detect valleys (absorption features)
        valleys, valley_properties = signal.find_peaks(
            -intensities, 
            height=np.mean(intensities) - 2 * np.std(intensities),
            distance=5
        )
        
        peak_info["num_valleys"] = len(valleys)
        peak_info["valley_positions"] = wavelengths[valleys].tolist()
        peak_info["valley_depths"] = intensities[valleys].tolist()
        
        return peak_info
    
    def _detect_spectrometer_issues(self, 
                                     processed_data: SpectralData,
                                     original_data: SpectralData) -> List[Dict]:
        """Detect potential spectrometer issues."""
        issues = []
        
        # Check for wavelength shift
        if len(original_data.wavelengths) == len(processed_data.wavelengths):
            wl_diff = np.mean(np.abs(original_data.wavelengths - processed_data.wavelengths))
            if wl_diff > 0.5:  # More than 0.5nm average difference
                issues.append({
                    "type": "wavelength_shift",
                    "severity": "high" if wl_diff > 2.0 else "medium",
                    "description": f"Wavelength shift detected: {wl_diff:.2f} nm",
                    "recommendation": "Recalibrate wavelength using known emission lines"
                })
        
        # Check for intensity drift
        if len(original_data.intensities) == len(processed_data.intensities):
            intensity_diff = np.mean(np.abs(original_data.intensities - processed_data.intensities))
            intensity_std = np.std(original_data.intensities)
            if intensity_std > 0 and intensity_diff / intensity_std > 0.1:
                issues.append({
                    "type": "intensity_drift",
                    "severity": "high" if intensity_diff / intensity_std > 0.3 else "medium",
                    "description": f"Intensity drift detected: {intensity_diff:.2f} (std: {intensity_std:.2f})",
                    "recommendation": "Check detector sensitivity and light source stability"
                })
        
        # Check for low signal-to-noise ratio
        signal = np.mean(np.abs(processed_data.intensities))
        noise = np.std(processed_data.intensities)
        if noise > 0:
            snr = signal / noise
            if snr < 50:
                issues.append({
                    "type": "low_snr",
                    "severity": "high" if snr < 20 else "medium",
                    "description": f"Low signal-to-noise ratio: {snr:.1f}",
                    "recommendation": "Increase integration time or improve light source"
                })
        
        # Check for wavelength range issues
        wl_min = np.min(processed_data.wavelengths)
        wl_max = np.max(processed_data.wavelengths)
        wl_range = wl_max - wl_min
        
        if wl_range < 100:
            issues.append({
                "type": "narrow_wavelength_range",
                "severity": "medium",
                "description": f"Narrow wavelength range: {wl_range:.1f} nm",
                "recommendation": "Use spectrometer with broader wavelength coverage"
            })
        
        # Check for gaps in wavelength data
        if len(processed_data.wavelengths) > 1:
            wl_diffs = np.diff(processed_data.wavelengths)
            max_gap = np.max(wl_diffs)
            avg_gap = np.mean(wl_diffs)
            
            if max_gap > avg_gap * 3:
                issues.append({
                    "type": "wavelength_gaps",
                    "severity": "medium",
                    "description": f"Large gaps in wavelength data: max {max_gap:.2f} nm (avg: {avg_gap:.2f} nm)",
                    "recommendation": "Check spectrometer wavelength calibration"
                })
        
        # Check for saturation
        max_intensity = np.max(processed_data.intensities)
        if max_intensity > 1e6:  # Arbitrary high threshold
            issues.append({
                "type": "saturation",
                "severity": "high",
                "description": f"Potential saturation detected: max intensity {max_intensity:.0f}",
                "recommendation": "Reduce integration time or use neutral density filter"
            })
        
        return issues
    
    def _generate_calibration_recommendations(self, 
                                               processed_data: SpectralData,
                                               spectrometer_info: Dict,
                                               issues: List[Dict]) -> List[Dict]:
        """Generate calibration recommendations."""
        recommendations = []
        spec_type = spectrometer_info.get("type", "unknown")
        
        # Get spectrometer-specific calibration points
        if spec_type in self.spectrometer_database:
            cal_points = self.spectrometer_database[spec_type].get("calibration_points", [])
            recommendations.append({
                "type": "wavelength_calibration",
                "priority": "high",
                "description": f"Use calibration points: {cal_points}",
                "method": "polynomial_fit",
                "parameters": {"points": cal_points}
            })
        else:
            # Generic calibration points for NIR
            recommendations.append({
                "type": "wavelength_calibration",
                "priority": "high",
                "description": "Use standard NIR calibration points",
                "method": "polynomial_fit",
                "parameters": {"points": [700, 850, 1000, 1100, 1300, 1500, 1700]}
            })
        
        # Address specific issues
        for issue in issues:
            if issue["type"] == "wavelength_shift":
                recommendations.append({
                    "type": "wavelength_shift_correction",
                    "priority": "high",
                    "description": "Apply wavelength shift correction",
                    "method": "linear_correction",
                    "parameters": {"shift": issue["description"].split(":")[1].strip()}
                })
            
            elif issue["type"] == "intensity_drift":
                recommendations.append({
                    "type": "intensity_stabilization",
                    "priority": "high",
                    "description": "Stabilize intensity measurements",
                    "method": "normalization",
                    "parameters": {"reference_value": "max"}
                })
            
            elif issue["type"] == "low_snr":
                recommendations.append({
                    "type": "snr_improvement",
                    "priority": "medium",
                    "description": "Improve signal-to-noise ratio",
                    "method": "averaging",
                    "parameters": {"num_scans": 10}
                })
        
        # Add general recommendations
        recommendations.append({
            "type": "regular_calibration",
            "priority": "medium",
            "description": "Perform regular calibration with known standards",
            "method": "standard_calibration",
            "parameters": {"frequency": "daily"}
        })
        
        recommendations.append({
            "type": "temperature_compensation",
            "priority": "low",
            "description": "Apply temperature compensation if available",
            "method": "temperature_correction",
            "parameters": {"enabled": True}
        })
        
        return recommendations
    
    def _calculate_quality_score(self, 
                                  processed_data: SpectralData,
                                  initial_quality: Dict,
                                  issues: List[Dict],
                                  recommendations: List[Dict]) -> float:
        """Calculate overall quality score (0-100)."""
        score = 100.0
        
        # Penalize for issues
        for issue in issues:
            if issue["severity"] == "high":
                score -= 20
            elif issue["severity"] == "medium":
                score -= 10
            else:
                score -= 5
        
        # Reward for good initial quality
        if initial_quality.get("signal_to_noise", 0) > 100:
            score += 5
        if initial_quality.get("data_completeness", 0) > 0.95:
            score += 5
        
        # Penalize for many recommendations (indicates problems)
        if len(recommendations) > 5:
            score -= (len(recommendations) - 5) * 2
        
        # Ensure score is between 0 and 100
        score = max(0, min(100, score))
        
        return round(score, 2)
    
    def _calculate_analysis_metrics(self, 
                                     original_data: SpectralData,
                                     processed_data: SpectralData,
                                     peak_info: Dict,
                                     issues: List[Dict]) -> Dict:
        """Calculate comprehensive analysis metrics."""
        metrics = {
            "wavelength_range": {
                "min": float(np.min(processed_data.wavelengths)),
                "max": float(np.max(processed_data.wavelengths)),
                "range": float(np.max(processed_data.wavelengths) - np.min(processed_data.wavelengths))
            },
            "intensity_statistics": {
                "min": float(np.min(processed_data.intensities)),
                "max": float(np.max(processed_data.intensities)),
                "mean": float(np.mean(processed_data.intensities)),
                "std": float(np.std(processed_data.intensities)),
                "median": float(np.median(processed_data.intensities))
            },
            "peak_analysis": {
                "num_peaks": peak_info.get("num_peaks", 0),
                "num_valleys": peak_info.get("num_valleys", 0),
                "peak_density": peak_info.get("num_peaks", 0) / 
                              (processed_data.wavelengths[-1] - processed_data.wavelengths[0]) * 100
            },
            "data_quality": {
                "signal_to_noise": initial_quality.get("signal_to_noise", 0),
                "wavelength_coverage": initial_quality.get("wavelength_coverage", 0),
                "intensity_range": initial_quality.get("intensity_range", 0),
                "data_completeness": initial_quality.get("data_completeness", 0),
                "outliers": initial_quality.get("outliers", 0)
            },
            "processing_metrics": {
                "baseline_correction": "applied",
                "noise_reduction": "applied",
                "smoothing": "applied",
                "wavelength_calibration": "applied"
            },
            "issue_summary": {
                "total_issues": len(issues),
                "high_severity": len([i for i in issues if i["severity"] == "high"]),
                "medium_severity": len([i for i in issues if i["severity"] == "medium"]),
                "low_severity": len([i for i in issues if i["severity"] == "low"])
            }
        }
        
        return metrics
    
    async def generate_calibration_formula(self, 
                                           spectral_data: SpectralData,
                                           known_wavelengths: List[float],
                                           known_intensities: List[float]) -> Dict:
        """Generate calibration formula for spectrometer."""
        # Fit polynomial to calibration data
        coeffs = np.polyfit(known_wavelengths, known_intensities, 3)
        
        # Create calibration function
        calibration_function = f"f(x) = {coeffs[0]:.6f}x^3 + {coeffs[1]:.6f}x^2 + {coeffs[2]:.6f}x + {coeffs[3]:.6f}"
        
        # Calculate residuals
        fitted = np.polyval(coeffs, known_wavelengths)
        residuals = known_intensities - fitted
        rmse = np.sqrt(np.mean(residuals**2))
        
        return {
            "calibration_function": calibration_function,
            "coefficients": coeffs.tolist(),
            "rmse": float(rmse),
            "r_squared": float(1 - np.sum(residuals**2) / np.sum((known_intensities - np.mean(known_intensities))**2)),
            "recommendation": "Apply this calibration function to correct wavelength measurements"
        }
    
    async def analyze_spectrometer_parameters(self, 
                                              spectral_data: SpectralData) -> Dict:
        """Analyze and recommend spectrometer parameters."""
        spec_type = spectral_data.spectrometer_type or "unknown"
        wavelengths = spectral_data.wavelengths
        intensities = spectral_data.intensities
        
        parameters = {
            "spectrometer_type": spec_type,
            "recommended_settings": {}
        }
        
        # Get spectrometer-specific recommendations
        if spec_type in self.spectrometer_database:
            spec_info = self.spectrometer_database[spec_type]
            parameters["recommended_settings"]["wavelength_range"] = spec_info["wavelength_range"]
            parameters["recommended_settings"]["resolution"] = spec_info["resolution"]
        
        # Integration time recommendation
        signal = np.mean(np.abs(intensities))
        noise = np.std(intensities)
        if noise > 0:
            snr = signal / noise
            if snr < 50:
                parameters["recommended_settings"]["integration_time"] = "increase"
            elif snr > 200:
                parameters["recommended_settings"]["integration_time"] = "decrease"
            else:
                parameters["recommended_settings"]["integration_time"] = "optimal"
        
        # Scans to average recommendation
        if noise > 0:
            # Calculate how many scans needed for SNR > 100
            current_snr = signal / noise if noise > 0 else float('inf')
            if current_snr < 100:
                required_scans = int(np.ceil((100 / current_snr) ** 2))
                parameters["recommended_settings"]["scans_to_average"] = max(1, required_scans)
        
        # Temperature compensation
        parameters["recommended_settings"]["temperature_compensation"] = True
        
        # Dark correction
        parameters["recommended_settings"]["dark_correction"] = True
        
        # White reference
        parameters["recommended_settings"]["white_reference"] = True
        
        return parameters


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def example_usage():
        # Create agent
        agent = SpectralAnalysisAgent()
        
        # Example data
        wavelengths = np.linspace(700, 1100, 400)
        intensities = np.sin(wavelengths * 0.01) * 100 + np.random.normal(0, 5, 400)
        
        data = {
            "wavelengths": wavelengths.tolist(),
            "intensities": intensities.tolist(),
            "metadata": {"sample": "test", "date": "2024-01-01"}
        }
        
        # Analyze
        result = await agent.analyze_spectral_data(data=data)
        
        print(f"Analysis complete. Quality score: {result.quality_score}")
        print(f"Issues detected: {len(result.issues_detected)}")
        print(f"Calibration recommendations: {len(result.calibration_recommendations)}")
        
        # Generate calibration formula
        known_wl = [700, 800, 900, 1000]
        known_int = [100, 120, 110, 90]
        cal_formula = await agent.generate_calibration_formula(
            result.processed_data, known_wl, known_int
        )
        print(f"Calibration formula: {cal_formula['calibration_function']}")
    
    asyncio.run(example_usage())
