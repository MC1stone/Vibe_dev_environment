# NIR Intelligence Platform - Enhanced Data Preparation Agent
# Handles NIR spectroscopy data loading, cleaning, preprocessing, and quality assessment

import json
import os
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import numpy as np
import pandas as pd
from scipy import signal as scipy_signal

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


class DataQualityGrade(Enum):
    """Quality grading for spectral data and metadata"""
    EXCELLENT = "A"
    GOOD = "B"
    FAIR = "C"
    POOR = "D"
    UNACCEPTABLE = "F"


class FileType(Enum):
    """Supported file types for NIR data"""
    CSV = ".csv"
    JSON = ".json"
    HDF5 = ".h5"
    JDX = ".jdx"
    SPC = ".spc"
    TXT = ".txt"
    ZIP = ".zip"
    PNG = ".png"
    JPG = ".jpg"
    JPEG = ".jpeg"
    WAV = ".wav"
    MP3 = ".mp3"
    XML = ".xml"
    YAML = ".yaml"
    YML = ".yml"


@dataclass
class MetadataQualityResult:
    """Result of metadata quality assessment"""
    completeness_score: float
    standards_compliance: float
    quality_grade: DataQualityGrade
    missing_required_fields: List[str]
    missing_optional_fields: List[str]
    enhancement_suggestions: List[str]
    standards_checked: List[str]
    detailed_scores: Dict[str, float]


@dataclass 
class SpectrometerIssue:
    """Detected spectrometer issue"""
    issue_type: str
    severity: str
    description: str
    affected_wavelengths: List[float]
    recommended_action: str
    confidence: float


@dataclass
class ParameterRecommendation:
    """Parameter recommendation for spectrometer"""
    parameter_name: str
    current_value: Optional[Any]
    recommended_value: Any
    reasoning: str
    priority: str
    impact: str


class EnhancedDataPreparationAgent(BaseAgent):
    """Enhanced agent for preparing NIR spectroscopy data with comprehensive quality assessment"""

    # Supported file extensions
    SPECTRAL_EXTENSIONS = [".csv", ".json", ".h5", ".jdx", ".spc", ".txt"]
    METADATA_EXTENSIONS = [".json", ".xml", ".yaml", ".yml"]
    IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg"]
    AUDIO_EXTENSIONS = [".wav", ".mp3"]
    ARCHIVE_EXTENSIONS = [".zip"]

    # Required metadata fields according to various standards
    REQUIRED_METADATA_FIELDS = {
        "basic": ["sample_id", "timestamp"],
        "instrument": ["instrument_type", "instrument_model", "serial_number"],
        "measurement": ["wavelength_range", "resolution", "integration_time", "scan_count"],
        "environment": ["temperature", "humidity"],
        "operator": ["operator_name", "organization"],
        "location": ["location", "gps_coordinates"]
    }

    # Optional metadata fields
    OPTIONAL_METADATA_FIELDS = [
        "sample_description", "sample_preparation", "sample_thickness",
        "light_source", "detector_type", "aperture_size",
        "reference_material", "dark_correction_applied",
        "white_reference_applied", "baseline_correction_applied",
        "smoothing_applied", "derivative_order", "notes", "project_name"
    ]

    # Standards for metadata quality assessment
    METADATA_STANDARDS = {
        "ASTM_E1655": ["wavelength_range", "resolution", "integration_time", "instrument_model"],
        "ISO_12099": ["sample_id", "timestamp", "operator_name", "instrument_type"],
        "EURACHEM": ["sample_description", "sample_preparation", "temperature", "humidity"],
        "NIR_PUBLIC_DATABASE": ["sample_id", "instrument_model", "wavelength_range", 
                               "resolution", "sample_description", "operator_name"]
    }

    def __init__(self, **kwargs):
        super().__init__(name="EnhancedDataPreparationAgent", version="2.0.0", **kwargs)
        
        # Dependencies
        self.dependencies = ["pandas", "numpy", "scipy"]
        
        # Configuration
        self.input_directory = kwargs.get("input_directory", "data/raw")
        self.output_directory = kwargs.get("output_directory", "data/processed")
        self.temp_directory = kwargs.get("temp_directory", "data/temp")
        self.default_format = kwargs.get("default_format", "HDF5")
        self.batch_size = kwargs.get("batch_size", 1000)
        self.max_file_size = kwargs.get("max_file_size", 100 * 1024 * 1024)  # 100MB
        
        # Preprocessing methods
        self.preprocessing_methods = kwargs.get("preprocessing_methods", [
            "SNV", "MSC", "Savitzky-Golay", "BaselineCorrection", "Detrending"
        ])
        
        # Quality assessment parameters
        self.quality_thresholds = kwargs.get("quality_thresholds", {
            "completeness": {"excellent": 0.95, "good": 0.85, "fair": 0.70, "poor": 0.50},
            "standards_compliance": {"excellent": 0.90, "good": 0.80, "fair": 0.60, "poor": 0.40},
            "overall": {"excellent": 90, "good": 80, "fair": 70, "poor": 60}
        })
        
        # Spectrometer issue detection parameters
        self.issue_detection_params = kwargs.get("issue_detection_params", {
            "shift_detection": {"threshold": 0.5, "window_size": 10},
            "noise_detection": {"threshold": 0.1, "window_size": 5},
            "outlier_detection": {"z_score_threshold": 3.0},
            "saturation_detection": {"max_intensity": 1.0, "min_intensity": 0.0}
        })
        
        # Initialize directories
        self._initialize_directories()
        
        # Track processing statistics
        self.processing_stats = {
            "total_files_processed": 0,
            "total_samples_processed": 0,
            "average_quality_score": 0.0,
            "issues_detected": 0,
            "recommendations_made": 0
        }

    def _initialize_directories(self) -> bool:
        """Initialize all required directories"""
        try:
            directories = [
                self.input_directory,
                self.output_directory,
                self.temp_directory,
                os.path.join(self.output_directory, "processed"),
                os.path.join(self.output_directory, "metadata"),
                os.path.join(self.output_directory, "images"),
                os.path.join(self.output_directory, "audio"),
                os.path.join(self.output_directory, "reports"),
                os.path.join(self.temp_directory, "extracted")
            ]
            
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
            
            self.logger.info("Initialized directories")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to initialize directories: {str(e)}", ErrorSeverity.HIGH)
            return False

    def _get_all_required_fields(self) -> List[str]:
        """Get all required metadata fields from all categories"""
        required_fields = []
        for category_fields in self.REQUIRED_METADATA_FIELDS.values():
            required_fields.extend(category_fields)
        return list(set(required_fields))

    def _get_file_type(self, file_path: str) -> Optional[FileType]:
        """Determine the type of a file based on its extension"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in self.SPECTRAL_EXTENSIONS:
            return FileType(ext)
        elif ext in self.METADATA_EXTENSIONS:
            if ext == ".json":
                return FileType.JSON
            elif ext == ".xml":
                return FileType.XML
            elif ext in [".yaml", ".yml"]:
                return FileType.YAML
        elif ext in self.IMAGE_EXTENSIONS:
            if ext == ".png":
                return FileType.PNG
            elif ext in [".jpg", ".jpeg"]:
                return FileType.JPG
        elif ext in self.AUDIO_EXTENSIONS:
            if ext == ".wav":
                return FileType.WAV
            elif ext == ".mp3":
                return FileType.MP3
        elif ext in self.ARCHIVE_EXTENSIONS:
            return FileType.ZIP
        
        return None

    def _validate_input_directory(self) -> bool:
        """Validate input directory exists and contains files"""
        if not os.path.exists(self.input_directory):
            self.log_error(
                f"Input directory not found: {self.input_directory}",
                ErrorSeverity.CRITICAL,
                {"suggested_fix": f"Create directory: mkdir -p {self.input_directory}"}
            )
            return False

        all_extensions = (self.SPECTRAL_EXTENSIONS + self.METADATA_EXTENSIONS + 
                        self.IMAGE_EXTENSIONS + self.AUDIO_EXTENSIONS + self.ARCHIVE_EXTENSIONS)
        
        files = [
            f for f in os.listdir(self.input_directory) 
            if any(f.lower().endswith(ext) for ext in all_extensions)
        ]
        
        if not files:
            self.log_error(
                f"No supported data files found in {self.input_directory}",
                ErrorSeverity.CRITICAL,
                {
                    "suggested_fix": f"Place supported files in {self.input_directory}",
                    "supported_extensions": all_extensions
                }
            )
            return False

        self.logger.info(f"Found {len(files)} data files in {self.input_directory}")
        return True

    def _extract_zip_file(self, zip_path: str) -> Optional[Dict[str, str]]:
        """Extract a ZIP file and return the paths of extracted files"""
        try:
            extract_dir = os.path.join(self.temp_directory, "extracted", 
                                     os.path.splitext(os.path.basename(zip_path))[0])
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                total_size = sum(info.file_size for info in zip_ref.infolist())
                if total_size > self.max_file_size:
                    self.log_error(
                        f"ZIP file too large: {total_size} bytes > {self.max_file_size} bytes",
                        ErrorSeverity.MEDIUM
                    )
                    return None
                
                zip_ref.extractall(extract_dir)
            
            extracted_files = {}
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, extract_dir)
                    extracted_files[rel_path] = file_path
            
            self.logger.info(f"Extracted {len(extracted_files)} files from {zip_path}")
            return extracted_files
            
        except zipfile.BadZipFile:
            self.log_error(f"Invalid ZIP file: {zip_path}", ErrorSeverity.MEDIUM)
            return None
        except Exception as e:
            self.log_error(f"Failed to extract ZIP file {zip_path}: {str(e)}", ErrorSeverity.MEDIUM)
            return None

    def _load_spectral_data(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load spectral data from various file formats"""
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == ".csv":
                return self._load_csv_spectral(file_path)
            elif file_ext == ".json":
                return self._load_json_spectral(file_path)
            elif file_ext == ".h5":
                return self._load_hdf5_spectral(file_path)
            elif file_ext in (".jdx", ".spc", ".txt"):
                return self._load_text_spectral(file_path)
            else:
                self.log_error(f"Unsupported spectral file format: {file_ext}", 
                             ErrorSeverity.MEDIUM, {"file": file_path})
                return None
                
        except Exception as e:
            self.log_error(f"Failed to load spectral data from {file_path}: {str(e)}", 
                         ErrorSeverity.MEDIUM)
            return None

    def _load_csv_spectral(self, file_path: str) -> Dict[str, Any]:
        """Load spectral data from CSV file"""
        df = pd.read_csv(file_path)
        
        wavelength_col = None
        intensity_col = None
        
        wavelength_patterns = ['wavelength', 'wave', 'lambda', 'nm', 'wavenumber']
        intensity_patterns = ['intensity', 'absorbance', 'reflectance', 'transmittance', 'value']
        
        # Identify spectral columns
        for col in df.columns:
            col_lower = col.lower()
            if any(pattern in col_lower for pattern in wavelength_patterns):
                wavelength_col = col
            elif any(pattern in col_lower for pattern in intensity_patterns):
                intensity_col = col
        
        # If spectral columns not found by pattern, try to identify them by data type
        if not wavelength_col and not intensity_col:
            # Look for numeric columns that could be spectral data
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if len(numeric_cols) >= 2:
                # Assume first numeric column is wavelength, second is intensity
                wavelength_col = numeric_cols[0]
                intensity_col = numeric_cols[1]
            elif len(numeric_cols) == 1 and len(df.columns) >= 2:
                # If only one numeric column, it's probably intensity, first column is wavelength
                wavelength_col = df.columns[0]
                intensity_col = numeric_cols[0]
        
        # Fallback to position-based assignment
        if not wavelength_col and len(df.columns) >= 1:
            wavelength_col = df.columns[0]
        if not intensity_col and len(df.columns) >= 2:
            intensity_col = df.columns[1]
        
        # Convert spectral columns to numeric
        if wavelength_col and intensity_col:
            df[wavelength_col] = pd.to_numeric(df[wavelength_col], errors='coerce')
            df[intensity_col] = pd.to_numeric(df[intensity_col], errors='coerce')
        
        # Extract metadata from non-spectral columns
        metadata = {}
        
        # Identify non-spectral columns (columns that are not wavelength or intensity)
        non_spectral_cols = [col for col in df.columns 
                           if col not in [wavelength_col, intensity_col]]
        
        for col in non_spectral_cols:
            # Get the first non-null value from this column (likely the metadata)
            first_non_null = df[col].first_valid_index()
            
            if first_non_null is not None:
                first_value = df.loc[first_non_null, col]
                
                # Check if this value looks like metadata (not numeric or looks like a wavelength/intensity)
                try:
                    # If the first value can be converted to a number, check if it looks like spectral data
                    first_numeric = float(first_value)
                    
                    # If the first value is a number that could be a wavelength or intensity, 
                    # check if most of the column contains similar numeric values
                    numeric_series = pd.to_numeric(df[col], errors='coerce')
                    valid_numeric_count = numeric_series.notna().sum()
                    
                    if valid_numeric_count > len(df) * 0.8:  # Most values are numeric
                        # This is likely spectral data, not metadata
                        continue
                    else:
                        # Only the first few values are metadata, rest are empty
                        metadata[col] = first_value
                        
                except (ValueError, TypeError):
                    # Not a number, so it's likely metadata
                    metadata[col] = first_value
        

        
        return {
            "data": df,
            "source_file": file_path,
            "format": ".csv",
            "wavelength_column": wavelength_col,
            "intensity_column": intensity_col,
            "metadata": metadata
        }

    def _load_json_spectral(self, file_path: str) -> Dict[str, Any]:
        """Load spectral data from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            if 'spectra' in data:
                df = pd.DataFrame(data['spectra'])
            elif 'data' in data:
                df = pd.DataFrame(data['data'])
            else:
                df = pd.DataFrame([data])
        else:
            df = pd.DataFrame()
        
        metadata = {}
        if isinstance(data, dict):
            for key, value in data.items():
                if key not in ['spectra', 'data'] and not isinstance(value, (list, dict)):
                    metadata[key] = value
        
        return {
            "data": df,
            "source_file": file_path,
            "format": ".json",
            "wavelength_column": "wavelength" if "wavelength" in df.columns else None,
            "intensity_column": "intensity" if "intensity" in df.columns else None,
            "metadata": metadata
        }

    def _load_hdf5_spectral(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load spectral data from HDF5 file"""
        try:
            import h5py
            with h5py.File(file_path, 'r') as f:
                spectral_data = None
                metadata = {}
                
                def find_spectral(name, obj):
                    nonlocal spectral_data
                    if isinstance(obj, h5py.Dataset):
                        if len(obj.shape) == 2 and obj.shape[1] >= 2:
                            spectral_data = obj
                
                f.visititems(find_spectral)
                
                if spectral_data is not None:
                    data = np.array(spectral_data)
                    df = pd.DataFrame(data, columns=[f'col_{i}' for i in range(data.shape[1])])
                    
                    wavelength_col = df.columns[0]
                    intensity_col = df.columns[1]
                    
                    return {
                        "data": df,
                        "source_file": file_path,
                        "format": ".h5",
                        "wavelength_column": wavelength_col,
                        "intensity_column": intensity_col,
                        "metadata": metadata
                    }
                else:
                    self.log_error(f"No spectral data found in HDF5 file: {file_path}", 
                                 ErrorSeverity.MEDIUM)
                    return None
                    
        except ImportError:
            self.log_error("HDF5 support not available (h5py not installed)", 
                         ErrorSeverity.MEDIUM)
            return None

    def _load_text_spectral(self, file_path: str) -> Dict[str, Any]:
        """Load spectral data from text-based formats (JDX, SPC, TXT)"""
        try:
            for delimiter in [r'\s+', '\t', ',', ';']:
                try:
                    df = pd.read_csv(file_path, sep=delimiter, header=None, 
                                   names=['wavelength', 'intensity'])
                    if len(df.columns) >= 2:
                        break
                except pd.errors.ParserError:
                    continue
            else:
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                    data = []
                    for line in lines:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            try:
                                wavelength = float(parts[0])
                                intensity = float(parts[1])
                                data.append({'wavelength': wavelength, 'intensity': intensity})
                            except ValueError:
                                continue
                    df = pd.DataFrame(data)
            
            if df.empty:
                self.log_error(f"Could not parse spectral data from {file_path}", 
                             ErrorSeverity.MEDIUM)
                return None
            
            return {
                "data": df,
                "source_file": file_path,
                "format": os.path.splitext(file_path)[1].lower(),
                "wavelength_column": "wavelength",
                "intensity_column": "intensity",
                "metadata": {}
            }
            
        except Exception as e:
            self.log_error(f"Failed to load text spectral file {file_path}: {str(e)}", 
                         ErrorSeverity.MEDIUM)
            return None

    def _extract_metadata_from_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract metadata from DataFrame columns"""
        metadata = {}
        spectral_columns = {'wavelength', 'intensity', 'absorbance', 'reflectance', 
                          'transmittance', 'value', 'wave', 'lambda', 'nm'}
        
        for col in df.columns:
            col_lower = col.lower()
            if col_lower not in spectral_columns:
                # Get non-null values
                non_null_values = df[col].dropna()
                
                if len(non_null_values) == 0:
                    continue
                    
                unique_values = non_null_values.unique()
                
                # If most values are null/empty, this is likely a metadata column
                # with metadata only in the first row
                if len(non_null_values) <= 1:
                    metadata[col] = unique_values[0] if len(unique_values) > 0 else None
                elif len(unique_values) == 1:
                    metadata[col] = unique_values[0]
                else:
                    # Only include if it's a reasonable number of unique values for metadata
                    if len(unique_values) <= 10:
                        metadata[col] = list(unique_values)
        
        return metadata

    def _validate_data_structure(self, data: Dict[str, Any]) -> bool:
        """Validate the structure of loaded spectral data"""
        try:
            df = data["data"]
            
            if df.empty:
                self.log_error(
                    f"Empty data in {data['source_file']}",
                    ErrorSeverity.HIGH,
                    {"file": data["source_file"]}
                )
                return False
            
            wavelength_col = data.get("wavelength_column", "wavelength")
            intensity_col = data.get("intensity_column", "intensity")
            
            if wavelength_col not in df.columns:
                for col in df.columns:
                    if 'wavelength' in col.lower() or 'wave' in col.lower():
                        wavelength_col = col
                        data["wavelength_column"] = wavelength_col
                        break
                else:
                    self.log_error(
                        f"Wavelength column not found in {data['source_file']}",
                        ErrorSeverity.HIGH,
                        {"file": data["source_file"], "available_columns": list(df.columns)}
                    )
                    return False
            
            if intensity_col not in df.columns:
                for col in df.columns:
                    if any(pattern in col.lower() for pattern in ['intensity', 'absorbance', 'reflectance', 'value']):
                        intensity_col = col
                        data["intensity_column"] = intensity_col
                        break
                else:
                    self.log_error(
                        f"Intensity column not found in {data['source_file']}",
                        ErrorSeverity.HIGH,
                        {"file": data["source_file"], "available_columns": list(df.columns)}
                    )
                    return False
            
            if not pd.api.types.is_numeric_dtype(df[wavelength_col]):
                try:
                    df[wavelength_col] = pd.to_numeric(df[wavelength_col], errors='coerce')
                except Exception:
                    self.log_error(
                        f"Wavelength column '{wavelength_col}' is not numeric in {data['source_file']}",
                        ErrorSeverity.MEDIUM,
                        {"file": data["source_file"]}
                    )
                    return False
            
            if not pd.api.types.is_numeric_dtype(df[intensity_col]):
                try:
                    df[intensity_col] = pd.to_numeric(df[intensity_col], errors='coerce')
                except Exception:
                    self.log_error(
                        f"Intensity column '{intensity_col}' is not numeric in {data['source_file']}",
                        ErrorSeverity.MEDIUM,
                        {"file": data["source_file"]}
                    )
                    return False
            
            self.logger.info(f"Data structure validated for {data['source_file']}")
            return True
            
        except Exception as e:
            self.log_error(f"Data validation failed: {str(e)}", ErrorSeverity.HIGH)
            return False

    def _assess_metadata_quality(self, metadata: Dict[str, Any], 
                                 source_file: str = "") -> MetadataQualityResult:
        """Assess the quality of metadata according to various standards"""
        try:
            all_required_fields = self._get_all_required_fields()
            
            present_required = []
            missing_required = []
            
            for field in all_required_fields:
                if field in metadata:
                    present_required.append(field)
                else:
                    missing_required.append(field)
            
            present_optional = []
            missing_optional = []
            
            for field in self.OPTIONAL_METADATA_FIELDS:
                if field in metadata:
                    present_optional.append(field)
                else:
                    missing_optional.append(field)
            
            total_required = len(all_required_fields)
            total_optional = len(self.OPTIONAL_METADATA_FIELDS)
            
            completeness_score = (len(present_required) + len(present_optional) * 0.5) / (total_required + total_optional * 0.5)
            
            standards_compliance_scores = {}
            for standard_name, required_fields in self.METADATA_STANDARDS.items():
                standard_score = sum(1 for field in required_fields if field in metadata) / len(required_fields)
                standards_compliance_scores[standard_name] = standard_score
            
            overall_standards_compliance = np.mean(list(standards_compliance_scores.values()))
            
            enhancement_suggestions = []
            
            if missing_required:
                enhancement_suggestions.append(
                    f"Add missing required fields: {', '.join(missing_required[:5])}{'...' if len(missing_required) > 5 else ''}"
                )
            
            if missing_optional and len(present_optional) < total_optional * 0.5:
                enhancement_suggestions.append(
                    f"Consider adding optional fields for better data documentation: {', '.join(missing_optional[:5])}{'...' if len(missing_optional) > 5 else ''}"
                )
            
            if completeness_score < 0.7:
                enhancement_suggestions.append(
                    "Metadata completeness is low. Add more metadata fields for better data quality."
                )
            
            if overall_standards_compliance < 0.6:
                enhancement_suggestions.append(
                    "Metadata does not comply with major standards. Review standards requirements."
                )
            
            if completeness_score >= self.quality_thresholds["completeness"]["excellent"] and \
               overall_standards_compliance >= self.quality_thresholds["standards_compliance"]["excellent"]:
                quality_grade = DataQualityGrade.EXCELLENT
            elif completeness_score >= self.quality_thresholds["completeness"]["good"] and \
                 overall_standards_compliance >= self.quality_thresholds["standards_compliance"]["good"]:
                quality_grade = DataQualityGrade.GOOD
            elif completeness_score >= self.quality_thresholds["completeness"]["fair"] and \
                 overall_standards_compliance >= self.quality_thresholds["standards_compliance"]["fair"]:
                quality_grade = DataQualityGrade.FAIR
            elif completeness_score >= self.quality_thresholds["completeness"]["poor"] and \
                 overall_standards_compliance >= self.quality_thresholds["standards_compliance"]["poor"]:
                quality_grade = DataQualityGrade.POOR
            else:
                quality_grade = DataQualityGrade.UNACCEPTABLE
            
            return MetadataQualityResult(
                completeness_score=completeness_score,
                standards_compliance=overall_standards_compliance,
                quality_grade=quality_grade,
                missing_required_fields=missing_required,
                missing_optional_fields=missing_optional,
                enhancement_suggestions=enhancement_suggestions,
                standards_checked=list(standards_compliance_scores.keys()),
                detailed_scores={
                    **standards_compliance_scores,
                    "completeness": completeness_score,
                    "required_fields_present": len(present_required) / total_required if total_required > 0 else 1.0,
                    "optional_fields_present": len(present_optional) / total_optional if total_optional > 0 else 0.0
                }
            )
            
        except Exception as e:
            self.log_error(f"Metadata quality assessment failed: {str(e)}", ErrorSeverity.MEDIUM)
            return MetadataQualityResult(
                completeness_score=0.0,
                standards_compliance=0.0,
                quality_grade=DataQualityGrade.UNACCEPTABLE,
                missing_required_fields=[],
                missing_optional_fields=[],
                enhancement_suggestions=[f"Error in quality assessment: {str(e)}"],
                standards_checked=[],
                detailed_scores={}
            )

    def _detect_spectrometer_issues(self, data: Dict[str, Any]) -> List[SpectrometerIssue]:
        """Detect potential spectrometer issues in the spectral data"""
        issues = []
        
        try:
            df = data["data"]
            wavelength_col = data["wavelength_column"]
            intensity_col = data["intensity_column"]
            
            wavelengths = df[wavelength_col].values
            intensities = df[intensity_col].values
            
            # 1. Check for wavelength spacing consistency
            if len(wavelengths) > 10:
                wavelength_diffs = np.diff(wavelengths)
                std_dev = np.std(wavelength_diffs)
                mean_diff = np.mean(wavelength_diffs)
                
                if mean_diff > 0 and std_dev / mean_diff > 0.1:
                    issues.append(SpectrometerIssue(
                        issue_type="irregular_wavelength_spacing",
                        severity="medium",
                        description=f"Wavelength spacing is irregular (std dev: {std_dev:.2f}, mean: {mean_diff:.2f})",
                        affected_wavelengths=[float(wavelengths[0]), float(wavelengths[-1])],
                        recommended_action="Check spectrometer wavelength calibration",
                        confidence=0.8
                    ))
            
            # 2. Check for noise
            if len(intensities) > 10:
                intensity_diffs = np.diff(intensities)
                noise_level = np.std(intensity_diffs)
                signal_level = np.mean(np.abs(intensities))
                
                if signal_level > 0:
                    signal_to_noise = signal_level / noise_level
                    
                    if signal_to_noise < 10:
                        issues.append(SpectrometerIssue(
                            issue_type="high_noise_level",
                            severity="high" if signal_to_noise < 5 else "medium",
                            description=f"Low signal-to-noise ratio: {signal_to_noise:.2f}",
                            affected_wavelengths=[float(wavelengths[0]), float(wavelengths[-1])],
                            recommended_action="Increase integration time or improve light source",
                            confidence=0.9
                        ))
            
            # 3. Check for outliers
            if len(intensities) > 5:
                z_scores = np.abs((intensities - np.mean(intensities)) / np.std(intensities))
                outlier_indices = np.where(z_scores > self.issue_detection_params["outlier_detection"]["z_score_threshold"])[0]
                
                if len(outlier_indices) > 0:
                    outlier_percentage = len(outlier_indices) / len(intensities) * 100
                    
                    if outlier_percentage > 5:
                        affected_wavelengths = [float(wavelengths[i]) for i in outlier_indices[:5]]
                        issues.append(SpectrometerIssue(
                            issue_type="excessive_outliers",
                            severity="high" if outlier_percentage > 10 else "medium",
                            description=f"Found {len(outlier_indices)} outliers ({outlier_percentage:.1f}% of data)",
                            affected_wavelengths=affected_wavelengths,
                            recommended_action="Check for contamination or instrument issues",
                            confidence=0.85
                        ))
            
            # 4. Check for saturation
            max_intensity = np.max(intensities)
            saturation_threshold = self.issue_detection_params["saturation_detection"]["max_intensity"]
            
            if max_intensity >= saturation_threshold:
                saturation_indices = np.where(intensities >= saturation_threshold)[0]
                affected_wavelengths = [float(wavelengths[i]) for i in saturation_indices[:5]]
                
                issues.append(SpectrometerIssue(
                    issue_type="saturation",
                    severity="high",
                    description=f"Intensity saturation detected at {len(saturation_indices)} wavelength points",
                    affected_wavelengths=affected_wavelengths,
                    recommended_action="Reduce integration time or check detector",
                    confidence=0.9
                ))
            
            # 5. Check for baseline issues
            if len(intensities) > 10:
                baseline_estimate = np.mean(intensities[:10])
                
                if baseline_estimate > 0.1:
                    issues.append(SpectrometerIssue(
                        issue_type="high_baseline",
                        severity="medium",
                        description=f"High baseline level detected: {baseline_estimate:.3f}",
                        affected_wavelengths=[float(wavelengths[0]), float(wavelengths[9])],
                        recommended_action="Apply baseline correction",
                        confidence=0.7
                    ))
            
            self.logger.info(f"Detected {len(issues)} potential spectrometer issues")
            
        except Exception as e:
            self.log_error(f"Spectrometer issue detection failed: {str(e)}", ErrorSeverity.MEDIUM)
        
        return issues

    def _generate_parameter_recommendations(self, data: Dict[str, Any], 
                                          metadata: Dict[str, Any]) -> List[ParameterRecommendation]:
        """Generate parameter recommendations for the spectrometer"""
        recommendations = []
        
        try:
            df = data["data"]
            wavelength_col = data["wavelength_column"]
            intensity_col = data["intensity_column"]
            
            wavelengths = df[wavelength_col].values
            intensities = df[intensity_col].values
            
            # 1. Integration time recommendation
            if len(intensities) > 0:
                max_intensity = np.max(intensities)
                
                if max_intensity >= 0.95:
                    recommendations.append(ParameterRecommendation(
                        parameter_name="integration_time",
                        current_value=metadata.get("integration_time"),
                        recommended_value="Reduce by 20-30%",
                        reasoning="Intensity values are close to saturation",
                        priority="high",
                        impact="Prevents saturation and improves data quality"
                    ))
                elif max_intensity < 0.3:
                    recommendations.append(ParameterRecommendation(
                        parameter_name="integration_time",
                        current_value=metadata.get("integration_time"),
                        recommended_value="Increase by 50-100%",
                        reasoning="Signal levels are low, indicating insufficient integration time",
                        priority="high",
                        impact="Improves signal-to-noise ratio"
                    ))
            
            # 2. Resolution recommendation
            if len(wavelengths) > 1:
                wavelength_range = float(wavelengths.max() - wavelengths.min())
                num_points = len(wavelengths)
                resolution = wavelength_range / (num_points - 1) if num_points > 1 else 0
                
                if resolution > 10:
                    recommendations.append(ParameterRecommendation(
                        parameter_name="spectral_resolution",
                        current_value=f"{resolution:.1f} nm",
                        recommended_value="< 5 nm",
                        reasoning=f"Current resolution ({resolution:.1f} nm) may be insufficient for detailed analysis",
                        priority="medium",
                        impact="Improves ability to resolve spectral features"
                    ))
            
            # 3. Scan count recommendation
            if len(intensities) > 0:
                noise_level = np.std(intensities)
                signal_level = np.mean(np.abs(intensities))
                
                if signal_level > 0:
                    signal_to_noise = signal_level / noise_level
                    
                    if 0 < signal_to_noise < 100:
                        current_scans = metadata.get("scan_count", 1)
                        recommended_scans = max(16, int(current_scans * 2))
                        
                        recommendations.append(ParameterRecommendation(
                            parameter_name="scan_count",
                            current_value=current_scans,
                            recommended_value=recommended_scans,
                            reasoning=f"Low signal-to-noise ratio ({signal_to_noise:.1f}) suggests more scans would help",
                            priority="medium",
                            impact="Improves signal-to-noise ratio through averaging"
                        ))
            
            # 4. Wavelength range recommendation
            if len(wavelengths) > 0:
                min_wavelength = float(wavelengths.min())
                max_wavelength = float(wavelengths.max())
                
                if min_wavelength > 700 or max_wavelength < 2500:
                    recommendations.append(ParameterRecommendation(
                        parameter_name="wavelength_range",
                        current_value=f"{min_wavelength:.0f}-{max_wavelength:.0f} nm",
                        recommended_value="700-2500 nm",
                        reasoning="Typical NIR spectroscopy covers 700-2500 nm range",
                        priority="low",
                        impact="Ensures comprehensive spectral coverage"
                    ))
            
            # 5. Environmental recommendations
            temperature = metadata.get("temperature")
            humidity = metadata.get("humidity")
            
            if temperature is not None:
                if temperature < 15 or temperature > 30:
                    recommendations.append(ParameterRecommendation(
                        parameter_name="environmental_temperature",
                        current_value=f"{temperature}°C",
                        recommended_value="15-30°C",
                        reasoning="Temperature outside optimal range may affect instrument performance",
                        priority="medium",
                        impact="Improves instrument stability and measurement consistency"
                    ))
            
            if humidity is not None:
                if humidity < 30 or humidity > 70:
                    recommendations.append(ParameterRecommendation(
                        parameter_name="environmental_humidity",
                        current_value=f"{humidity}%",
                        recommended_value="30-70%",
                        reasoning="Humidity outside optimal range may affect measurements",
                        priority="medium",
                        impact="Reduces environmental interference"
                    ))
            
            self.logger.info(f"Generated {len(recommendations)} parameter recommendations")
            
        except Exception as e:
            self.log_error(f"Parameter recommendation generation failed: {str(e)}", ErrorSeverity.LOW)
        
        return recommendations

    def _preprocess_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Apply preprocessing methods to the data"""
        try:
            df = data["data"].copy()
            wavelength_col = data["wavelength_column"]
            intensity_col = data["intensity_column"]
            preprocessing_results = {}

            original_intensity_col = f"{intensity_col}_original"
            df[original_intensity_col] = df[intensity_col].copy()

            if "SNV" in self.preprocessing_methods:
                df[f"{intensity_col}_snv"] = self._apply_snv(df[intensity_col])
                preprocessing_results["SNV"] = True
                self.logger.info("Applied SNV preprocessing")

            if "MSC" in self.preprocessing_methods:
                df[f"{intensity_col}_msc"] = self._apply_msc(df[intensity_col])
                preprocessing_results["MSC"] = True
                self.logger.info("Applied MSC preprocessing")

            if "Savitzky-Golay" in self.preprocessing_methods:
                window_size = self.issue_detection_params.get("smoothing", {}).get("window_size", 5)
                poly_order = self.issue_detection_params.get("smoothing", {}).get("polyorder", 2)
                df[f"{intensity_col}_sg"] = self._apply_savitzky_golay(
                    df[intensity_col], window_size=window_size, poly_order=poly_order
                )
                preprocessing_results["Savitzky-Golay"] = True
                self.logger.info(f"Applied Savitzky-Golay smoothing")

            if "BaselineCorrection" in self.preprocessing_methods:
                df[f"{intensity_col}_baseline_corrected"] = self._apply_baseline_correction(df[intensity_col])
                preprocessing_results["BaselineCorrection"] = True
                self.logger.info("Applied baseline correction")

            if "Detrending" in self.preprocessing_methods:
                df[f"{intensity_col}_detrended"] = self._apply_detrending(df[intensity_col])
                preprocessing_results["Detrending"] = True
                self.logger.info("Applied detrending")

            data["preprocessing"] = preprocessing_results
            data["processed_data"] = df
            data["intensity_columns"] = {
                "original": intensity_col,
                "snv": f"{intensity_col}_snv" if "SNV" in preprocessing_results else None,
                "msc": f"{intensity_col}_msc" if "MSC" in preprocessing_results else None,
                "savitzky_golay": f"{intensity_col}_sg" if "Savitzky-Golay" in preprocessing_results else None,
                "baseline_corrected": f"{intensity_col}_baseline_corrected" if "BaselineCorrection" in preprocessing_results else None,
                "detrended": f"{intensity_col}_detrended" if "Detrending" in preprocessing_results else None
            }

            return data

        except Exception as e:
            self.log_error(f"Data preprocessing failed: {str(e)}", ErrorSeverity.MEDIUM)
            return None

    def _apply_snv(self, spectrum: pd.Series) -> pd.Series:
        """Apply Standard Normal Variate (SNV) preprocessing"""
        mean = spectrum.mean()
        std = spectrum.std()
        if std == 0:
            return spectrum - mean
        return (spectrum - mean) / std

    def _apply_msc(self, spectrum: pd.Series) -> pd.Series:
        """Apply Multiplicative Scatter Correction (MSC)"""
        reference = spectrum.mean()
        if reference == 0:
            return spectrum.copy()
        return spectrum / reference

    def _apply_savitzky_golay(self, spectrum: pd.Series, window_size: int = 5, poly_order: int = 2) -> pd.Series:
        """Apply Savitzky-Golay smoothing"""
        try:
            if window_size % 2 == 0:
                window_size += 1
            smoothed = scipy_signal.savgol_filter(
                spectrum.values, 
                window_length=window_size, 
                polyorder=poly_order
            )
            return pd.Series(smoothed, index=spectrum.index)
        except Exception:
            return spectrum.rolling(window=window_size, center=True).mean()

    def _apply_baseline_correction(self, spectrum: pd.Series) -> pd.Series:
        """Apply baseline correction using polynomial fitting"""
        try:
            x = np.arange(len(spectrum))
            y = spectrum.values
            coefficients = np.polyfit(x, y, 2)
            baseline = np.polyval(coefficients, x)
            corrected = y - baseline
            return pd.Series(corrected, index=spectrum.index)
        except Exception:
            return spectrum - spectrum.min()

    def _apply_detrending(self, spectrum: pd.Series) -> pd.Series:
        """Apply detrending to remove linear trends"""
        try:
            x = np.arange(len(spectrum))
            y = spectrum.values
            coefficients = np.polyfit(x, y, 1)
            trend = np.polyval(coefficients, x)
            detrended = y - trend
            return pd.Series(detrended, index=spectrum.index)
        except Exception:
            return spectrum.copy()

    def _process_single_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Process a single file through the complete preparation pipeline"""
        try:
            self.logger.info(f"Processing file: {file_path}")
            
            file_type = self._get_file_type(file_path)
            if file_type is None:
                self.log_error(f"Unsupported file type: {file_path}", ErrorSeverity.MEDIUM)
                return None
            
            result = {
                "file_path": file_path,
                "file_type": file_type.value,
                "processing_timestamp": datetime.now().isoformat(),
                "success": False,
                "error": None
            }
            
            # Handle ZIP files by extracting first
            if file_type == FileType.ZIP:
                extracted_files = self._extract_zip_file(file_path)
                if extracted_files is None:
                    result["error"] = "Failed to extract ZIP file"
                    return result
                
                # Process each extracted file
                processed_files = []
                for rel_path, full_path in extracted_files.items():
                    file_result = self._process_single_file(full_path)
                    if file_result:
                        file_result["extracted_from"] = file_path
                        file_result["original_path"] = rel_path
                        processed_files.append(file_result)
                
                result["extracted_files"] = processed_files
                result["success"] = True
                return result
            
            # Load spectral data
            spectral_data = self._load_spectral_data(file_path)
            if spectral_data is None:
                result["error"] = "Failed to load spectral data"
                return result
            
            # Validate data structure
            if not self._validate_data_structure(spectral_data):
                result["error"] = "Invalid data structure"
                return result
            
            # Extract metadata
            metadata = spectral_data.get("metadata", {})
            
            # Assess metadata quality
            metadata_quality = self._assess_metadata_quality(metadata, file_path)
            
            # Detect spectrometer issues
            spectrometer_issues = self._detect_spectrometer_issues(spectral_data)
            
            # Generate parameter recommendations
            parameter_recommendations = self._generate_parameter_recommendations(
                spectral_data, metadata
            )
            
            # Preprocess data
            processed_data = self._preprocess_data(spectral_data)
            if processed_data is None:
                result["error"] = "Data preprocessing failed"
                return result
            
            # Update result with all processing information
            result.update({
                "success": True,
                "spectral_data": {
                    "wavelength_column": spectral_data["wavelength_column"],
                    "intensity_column": spectral_data["intensity_column"],
                    "num_points": len(spectral_data["data"]),
                    "wavelength_range": {
                        "min": float(spectral_data["data"][spectral_data["wavelength_column"]].min()),
                        "max": float(spectral_data["data"][spectral_data["wavelength_column"]].max())
                    }
                },
                "metadata": metadata,
                "metadata_quality": {
                    "completeness_score": metadata_quality.completeness_score,
                    "standards_compliance": metadata_quality.standards_compliance,
                    "quality_grade": metadata_quality.quality_grade.value,
                    "missing_required_fields": metadata_quality.missing_required_fields,
                    "missing_optional_fields": metadata_quality.missing_optional_fields,
                    "enhancement_suggestions": metadata_quality.enhancement_suggestions,
                    "detailed_scores": metadata_quality.detailed_scores
                },
                "spectrometer_issues": [
                    {
                        "issue_type": issue.issue_type,
                        "severity": issue.severity,
                        "description": issue.description,
                        "affected_wavelengths": issue.affected_wavelengths,
                        "recommended_action": issue.recommended_action,
                        "confidence": issue.confidence
                    }
                    for issue in spectrometer_issues
                ],
                "parameter_recommendations": [
                    {
                        "parameter_name": rec.parameter_name,
                        "current_value": rec.current_value,
                        "recommended_value": rec.recommended_value,
                        "reasoning": rec.reasoning,
                        "priority": rec.priority,
                        "impact": rec.impact
                    }
                    for rec in parameter_recommendations
                ],
                "preprocessing": processed_data.get("preprocessing", {}),
                "processed_data_info": {
                    "available_intensity_columns": list(processed_data.get("intensity_columns", {}).values()),
                    "preprocessing_methods_applied": list(processed_data.get("preprocessing", {}).keys())
                }
            })
            
            # Update processing statistics
            self.processing_stats["total_files_processed"] += 1
            self.processing_stats["total_samples_processed"] += len(spectral_data["data"])
            self.processing_stats["issues_detected"] += len(spectrometer_issues)
            self.processing_stats["recommendations_made"] += len(parameter_recommendations)
            
            self.logger.info(f"Successfully processed file: {file_path}")
            return result
            
        except Exception as e:
            self.log_error(f"Failed to process file {file_path}: {str(e)}", ErrorSeverity.HIGH)
            result["error"] = str(e)
            return result

    def _save_processed_data(self, processed_data: Dict[str, Any], output_format: str = "HDF5") -> Optional[str]:
        """Save processed data to the specified format"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sample_id = processed_data.get("metadata", {}).get("sample_id", "unknown")
            
            if output_format.upper() == "HDF5":
                output_path = os.path.join(
                    self.output_directory, "processed", 
                    f"{sample_id}_{timestamp}.h5"
                )
                self._save_to_hdf5(processed_data, output_path)
                return output_path
            elif output_format.upper() == "CSV":
                output_path = os.path.join(
                    self.output_directory, "processed", 
                    f"{sample_id}_{timestamp}.csv"
                )
                self._save_to_csv(processed_data, output_path)
                return output_path
            elif output_format.upper() == "JSON":
                output_path = os.path.join(
                    self.output_directory, "processed", 
                    f"{sample_id}_{timestamp}.json"
                )
                self._save_to_json(processed_data, output_path)
                return output_path
            else:
                self.log_error(f"Unsupported output format: {output_format}", ErrorSeverity.MEDIUM)
                return None
                
        except Exception as e:
            self.log_error(f"Failed to save processed data: {str(e)}", ErrorSeverity.MEDIUM)
            return None

    def _save_to_hdf5(self, data: Dict[str, Any], file_path: str) -> bool:
        """Save processed data to HDF5 format"""
        try:
            import h5py
            
            with h5py.File(file_path, 'w') as f:
                # Save metadata
                metadata_group = f.create_group("metadata")
                for key, value in data.get("metadata", {}).items():
                    try:
                        metadata_group.create_dataset(key, data=str(value))
                    except Exception:
                        continue
                
                # Save spectral data
                df = data.get("processed_data", data.get("data"))
                if isinstance(df, pd.DataFrame):
                    spectral_group = f.create_group("spectral_data")
                    for col in df.columns:
                        spectral_group.create_dataset(col, data=df[col].values)
                
                # Save quality assessment
                quality_group = f.create_group("quality_assessment")
                metadata_quality = data.get("metadata_quality", {})
                if metadata_quality:
                    quality_group.attrs["completeness_score"] = metadata_quality.get("completeness_score", 0.0)
                    quality_group.attrs["standards_compliance"] = metadata_quality.get("standards_compliance", 0.0)
                    quality_group.attrs["quality_grade"] = metadata_quality.get("quality_grade", "F")
                
                # Save preprocessing info
                preprocessing = data.get("preprocessing", {})
                if preprocessing:
                    preproc_group = f.create_group("preprocessing")
                    for method, applied in preprocessing.items():
                        preproc_group.attrs[method] = applied
            
            return True
            
        except ImportError:
            self.log_error("HDF5 support not available (h5py not installed)", ErrorSeverity.MEDIUM)
            return False
        except Exception as e:
            self.log_error(f"Failed to save to HDF5: {str(e)}", ErrorSeverity.MEDIUM)
            return False

    def _save_to_csv(self, data: Dict[str, Any], file_path: str) -> bool:
        """Save processed data to CSV format"""
        try:
            df = data.get("processed_data", data.get("data"))
            if isinstance(df, pd.DataFrame):
                df.to_csv(file_path, index=False)
                return True
            return False
        except Exception as e:
            self.log_error(f"Failed to save to CSV: {str(e)}", ErrorSeverity.MEDIUM)
            return False

    def _save_to_json(self, data: Dict[str, Any], file_path: str) -> bool:
        """Save processed data to JSON format"""
        try:
            # Convert DataFrames to dictionaries for JSON serialization
            output_data = {}
            for key, value in data.items():
                if isinstance(value, pd.DataFrame):
                    output_data[key] = value.to_dict(orient='records')
                elif isinstance(value, np.ndarray):
                    output_data[key] = value.tolist()
                else:
                    output_data[key] = value
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, default=str)
            
            return True
            
        except Exception as e:
            self.log_error(f"Failed to save to JSON: {str(e)}", ErrorSeverity.MEDIUM)
            return False

    def _generate_processing_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a comprehensive processing report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "agent_name": self.name,
            "agent_version": self.version,
            "total_files_processed": len(results),
            "successful_files": len([r for r in results if r.get("success", False)]),
            "failed_files": len([r for r in results if not r.get("success", False)]),
            "processing_statistics": self.processing_stats.copy(),
            "file_results": [],
            "summary": {}
        }
        
        # Process each file result
        for result in results:
            file_summary = {
                "file_path": result.get("file_path", "unknown"),
                "file_type": result.get("file_type", "unknown"),
                "success": result.get("success", False),
                "error": result.get("error")
            }
            
            if result.get("success", False):
                file_summary["metadata_quality"] = result.get("metadata_quality", {})
                file_summary["spectrometer_issues_count"] = len(result.get("spectrometer_issues", []))
                file_summary["parameter_recommendations_count"] = len(result.get("parameter_recommendations", []))
                file_summary["spectral_data"] = result.get("spectral_data", {})
            
            report["file_results"].append(file_summary)
        
        # Generate overall summary
        successful_results = [r for r in results if r.get("success", False)]
        if successful_results:
            avg_completeness = np.mean([
                r.get("metadata_quality", {}).get("completeness_score", 0) 
                for r in successful_results
            ])
            avg_standards_compliance = np.mean([
                r.get("metadata_quality", {}).get("standards_compliance", 0) 
                for r in successful_results
            ])
            
            report["summary"] = {
                "average_metadata_completeness": avg_completeness,
                "average_standards_compliance": avg_standards_compliance,
                "total_spectrometer_issues": sum(len(r.get("spectrometer_issues", [])) for r in successful_results),
                "total_parameter_recommendations": sum(len(r.get("parameter_recommendations", [])) for r in successful_results),
                "overall_quality_grade": self._calculate_overall_grade(avg_completeness, avg_standards_compliance)
            }
        
        return report

    def _calculate_overall_grade(self, completeness: float, standards_compliance: float) -> str:
        """Calculate overall quality grade based on completeness and standards compliance"""
        overall_score = (completeness * 0.6) + (standards_compliance * 0.4)
        
        if overall_score >= 0.9:
            return "A"
        elif overall_score >= 0.8:
            return "B"
        elif overall_score >= 0.7:
            return "C"
        elif overall_score >= 0.6:
            return "D"
        else:
            return "F"

    def execute(self, context: Dict[str, Any] = None) -> AgentOutput:
        """
        Execute the Enhanced Data Preparation Agent's complete workflow.
        
        This method orchestrates the entire data preparation pipeline including:
        1. Input validation
        2. File discovery and processing
        3. Spectral data loading and validation
        4. Metadata quality assessment
        5. Spectrometer issue detection
        6. Parameter recommendation generation
        7. Data preprocessing
        8. Results saving and reporting
        
        Args:
            context: Dictionary containing execution context with optional parameters:
                - input_directory: Override default input directory
                - output_directory: Override default output directory
                - file_paths: Specific files to process (overrides directory scan)
                - output_format: Format for saving processed data (HDF5, CSV, JSON)
                - save_processed_data: Whether to save processed data (default: True)
                - generate_report: Whether to generate processing report (default: True)
                
        Returns:
            AgentOutput containing processing results, statistics, and any errors
        """
        self.status = AgentStatus.PROCESSING
        self.clear_errors()
        
        try:
            # Update configuration from context
            if context:
                if "input_directory" in context:
                    self.input_directory = context["input_directory"]
                if "output_directory" in context:
                    self.output_directory = context["output_directory"]
                if "temp_directory" in context:
                    self.temp_directory = context["temp_directory"]
                if "preprocessing_methods" in context:
                    self.preprocessing_methods = context["preprocessing_methods"]
                if "quality_thresholds" in context:
                    self.quality_thresholds = context["quality_thresholds"]
                if "issue_detection_params" in context:
                    self.issue_detection_params = context["issue_detection_params"]
            
            # Re-initialize directories with potentially updated paths
            self._initialize_directories()
            
            # Validate input
            if not self._validate_input_directory():
                return self._create_success_output({
                    "status": "failed",
                    "error": "Input validation failed",
                    "errors": [e.message for e in self.errors]
                })
            
            # Get files to process
            file_paths = context.get("file_paths") if context else None
            if file_paths:
                # Use provided file paths
                files_to_process = [
                    os.path.join(self.input_directory, f) if not os.path.isabs(f) else f
                    for f in file_paths
                    if os.path.exists(f if os.path.isabs(f) else os.path.join(self.input_directory, f))
                ]
            else:
                # Discover files in input directory
                all_extensions = (self.SPECTRAL_EXTENSIONS + self.METADATA_EXTENSIONS + 
                                self.IMAGE_EXTENSIONS + self.AUDIO_EXTENSIONS + self.ARCHIVE_EXTENSIONS)
                files_to_process = [
                    os.path.join(self.input_directory, f)
                    for f in os.listdir(self.input_directory)
                    if any(f.lower().endswith(ext) for ext in all_extensions)
                ]
            
            if not files_to_process:
                return self._create_success_output({
                    "status": "no_files_found",
                    "input_directory": self.input_directory,
                    "supported_extensions": (self.SPECTRAL_EXTENSIONS + self.METADATA_EXTENSIONS + 
                                           self.IMAGE_EXTENSIONS + self.AUDIO_EXTENSIONS + self.ARCHIVE_EXTENSIONS)
                })
            
            self.logger.info(f"Starting processing of {len(files_to_process)} files")
            
            # Process all files
            processing_results = []
            for file_path in files_to_process:
                result = self._process_single_file(file_path)
                if result:
                    processing_results.append(result)
            
            # Save processed data if requested
            save_data = context.get("save_processed_data", True)
            output_format = context.get("output_format", self.default_format)
            saved_files = []
            
            if save_data:
                for result in processing_results:
                    if result.get("success", False) and "processed_data" in result:
                        saved_path = self._save_processed_data(result, output_format)
                        if saved_path:
                            saved_files.append(saved_path)
            
            # Generate report if requested
            generate_report = context.get("generate_report", True)
            report_data = None
            
            if generate_report:
                report_data = self._generate_processing_report(processing_results)
                
                # Save report to file
                report_path = os.path.join(
                    self.output_directory, "reports",
                    f"processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                try:
                    with open(report_path, 'w', encoding='utf-8') as f:
                        json.dump(report_data, f, indent=2, default=str)
                    self.logger.info(f"Processing report saved to: {report_path}")
                except Exception as e:
                    self.log_error(f"Failed to save processing report: {str(e)}", ErrorSeverity.LOW)
            
            # Prepare final output
            output_data = {
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "files_processed": len(processing_results),
                "successful_files": len([r for r in processing_results if r.get("success", False)]),
                "failed_files": len([r for r in processing_results if not r.get("success", False)]),
                "processing_results": processing_results,
                "saved_files": saved_files,
                "report": report_data,
                "processing_statistics": self.processing_stats,
                "configuration": {
                    "input_directory": self.input_directory,
                    "output_directory": self.output_directory,
                    "preprocessing_methods": self.preprocessing_methods,
                    "quality_thresholds": self.quality_thresholds,
                    "issue_detection_params": self.issue_detection_params
                }
            }
            
            self.status = AgentStatus.COMPLETED
            self.logger.info(f"Data preparation completed. Processed {len(processing_results)} files.")
            
            return self._create_success_output(output_data)
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.log_error(f"Execution failed: {str(e)}", ErrorSeverity.CRITICAL)
            return self._handle_error(e)
