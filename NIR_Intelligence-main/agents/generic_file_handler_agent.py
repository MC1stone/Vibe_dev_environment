# NIR Intelligence Platform - Generic File Handler Agent
# Handles any uploaded file type for metadata extraction, analysis, and processing

import json
import os
import hashlib
import mimetypes
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable, Type
from enum import Enum
import logging

import pandas as pd
import numpy as np

# Try to import python-magic for MIME type detection
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


class FileCategory(Enum):
    """Categories of files for generalized handling"""
    SPECTRAL = "spectral"
    TABULAR = "tabular"
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    ARCHIVE = "archive"
    DOCUMENT = "document"
    BINARY = "binary"
    UNKNOWN = "unknown"


class FileTypeInfo(Enum):
    """Comprehensive file type information"""
    # Spectral data formats
    CSV = (".csv", FileCategory.SPECTRAL, ["text/csv", "application/csv"])
    JSON = (".json", FileCategory.SPECTRAL, ["application/json"])
    HDF5 = (".h5", FileCategory.SPECTRAL, ["application/x-hdf5"])
    JDX = (".jdx", FileCategory.SPECTRAL, ["chemical/x-jcamp-dx"])
    SPC = (".spc", FileCategory.SPECTRAL, ["application/octet-stream"])
    TXT = (".txt", FileCategory.TEXT, ["text/plain"])
    
    # Tabular data
    XLSX = (".xlsx", FileCategory.TABULAR, ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"])
    XLS = (".xls", FileCategory.TABULAR, ["application/vnd.ms-excel"])
    PARQUET = (".parquet", FileCategory.TABULAR, ["application/vnd.apache.parquet"])
    FEATHER = (".feather", FileCategory.TABULAR, ["application/octet-stream"])
    
    # Text formats
    XML = (".xml", FileCategory.TEXT, ["application/xml", "text/xml"])
    YAML = (".yaml", FileCategory.TEXT, ["application/x-yaml", "text/yaml"])
    YML = (".yml", FileCategory.TEXT, ["application/x-yaml", "text/yaml"])
    MARKDOWN = (".md", FileCategory.TEXT, ["text/markdown"])
    
    # Image formats
    PNG = (".png", FileCategory.IMAGE, ["image/png"])
    JPG = (".jpg", FileCategory.IMAGE, ["image/jpeg"])
    JPEG = (".jpeg", FileCategory.IMAGE, ["image/jpeg"])
    GIF = (".gif", FileCategory.IMAGE, ["image/gif"])
    TIFF = (".tiff", FileCategory.IMAGE, ["image/tiff"])
    WEBP = (".webp", FileCategory.IMAGE, ["image/webp"])
    SVG = (".svg", FileCategory.IMAGE, ["image/svg+xml"])
    
    # Audio formats
    WAV = (".wav", FileCategory.AUDIO, ["audio/wav", "audio/x-wav"])
    MP3 = (".mp3", FileCategory.AUDIO, ["audio/mpeg"])
    OGG = (".ogg", FileCategory.AUDIO, ["audio/ogg"])
    FLAC = (".flac", FileCategory.AUDIO, ["audio/flac"])
    
    # Video formats
    MP4 = (".mp4", FileCategory.VIDEO, ["video/mp4"])
    AVI = (".avi", FileCategory.VIDEO, ["video/x-msvideo"])
    MOV = (".mov", FileCategory.VIDEO, ["video/quicktime"])
    WMV = (".wmv", FileCategory.VIDEO, ["video/x-ms-wmv"])
    
    # Archive formats
    ZIP = (".zip", FileCategory.ARCHIVE, ["application/zip"])
    TAR = (".tar", FileCategory.ARCHIVE, ["application/x-tar"])
    GZ = (".gz", FileCategory.ARCHIVE, ["application/gzip"])
    RAR = (".rar", FileCategory.ARCHIVE, ["application/vnd.rar"])
    SEVEN_ZIP = (".7z", FileCategory.ARCHIVE, ["application/x-7z-compressed"])
    
    # Document formats
    PDF = (".pdf", FileCategory.DOCUMENT, ["application/pdf"])
    DOCX = (".docx", FileCategory.DOCUMENT, ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"])
    DOC = (".doc", FileCategory.DOCUMENT, ["application/msword"])
    PPTX = (".pptx", FileCategory.DOCUMENT, ["application/vnd.openxmlformats-officedocument.presentationml.presentation"])
    
    def __init__(self, extension, category, mimetypes):
        self.extension = extension
        self.category = category
        self.mimetypes = mimetypes


@dataclass
class FileMetadata:
    """Comprehensive metadata extracted from any file"""
    file_name: str
    file_path: str
    file_size: int
    file_extension: str
    file_category: FileCategory
    mime_type: Optional[str] = None
    
    # Basic file info
    created_timestamp: Optional[datetime] = None
    modified_timestamp: Optional[datetime] = None
    accessed_timestamp: Optional[datetime] = None
    
    # Content metadata
    content_type: Optional[str] = None
    content_encoding: Optional[str] = None
    content_language: Optional[str] = None
    
    # For tabular/spectral data
    num_rows: Optional[int] = None
    num_columns: Optional[int] = None
    column_names: Optional[List[str]] = None
    data_types: Optional[Dict[str, str]] = None
    
    # For text files
    num_lines: Optional[int] = None
    num_words: Optional[int] = None
    num_characters: Optional[int] = None
    
    # For images
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    image_channels: Optional[int] = None
    image_format: Optional[str] = None
    
    # For audio
    audio_duration: Optional[float] = None
    audio_sample_rate: Optional[int] = None
    audio_channels: Optional[int] = None
    audio_bit_rate: Optional[int] = None
    
    # For video
    video_duration: Optional[float] = None
    video_resolution: Optional[Tuple[int, int]] = None
    video_frame_rate: Optional[float] = None
    video_codec: Optional[str] = None
    
    # For archives
    archive_contents: Optional[List[str]] = None
    archive_num_files: Optional[int] = None
    
    # Hashes for integrity
    md5_hash: Optional[str] = None
    sha1_hash: Optional[str] = None
    sha256_hash: Optional[str] = None
    
    # Custom metadata from file content
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Quality assessment
    quality_score: Optional[float] = None
    quality_issues: Optional[List[str]] = None
    
    # Processing info
    processing_timestamp: datetime = field(default_factory=datetime.now)
    processed_by: str = "generic_file_handler_agent"


@dataclass
class FileProcessingResult:
    """Result of processing a single file"""
    file_path: str
    success: bool
    file_metadata: Optional[FileMetadata] = None
    extracted_data: Optional[Dict[str, Any]] = None
    processing_errors: Optional[List[str]] = None
    processing_warnings: Optional[List[str]] = None
    processing_time_ms: float = 0.0
    
    # Analysis results
    analysis_results: Optional[Dict[str, Any]] = None
    
    # Recommendations
    recommendations: Optional[List[Dict[str, Any]]] = None


@dataclass
class HandlerCapability:
    """Capabilities of a file handler"""
    handler_name: str
    supported_categories: List[FileCategory]
    supported_extensions: List[str]
    can_extract_metadata: bool = True
    can_analyze_content: bool = True
    can_generate_report: bool = True
    can_preprocess: bool = False
    priority: int = 0  # Higher priority handlers are tried first


class FileHandlerRegistry:
    """Registry for file type handlers"""
    
    def __init__(self):
        self.handlers: Dict[FileCategory, List[Callable]] = {}
        self.handler_capabilities: Dict[str, HandlerCapability] = {}
        self.default_handlers: Dict[FileCategory, Callable] = {}
    
    def register_handler(self, category: FileCategory, handler: Callable, 
                        capability: HandlerCapability = None, is_default: bool = False):
        """Register a handler for a specific file category"""
        if category not in self.handlers:
            self.handlers[category] = []
        
        # Sort by priority (higher first)
        self.handlers[category].append(handler)
        self.handlers[category].sort(key=lambda h: getattr(h, 'priority', 0), reverse=True)
        
        if capability:
            self.handler_capabilities[handler.__name__] = capability
        
        if is_default:
            self.default_handlers[category] = handler
    
    def get_handlers_for_category(self, category: FileCategory) -> List[Callable]:
        """Get all handlers for a specific category"""
        return self.handlers.get(category, [])
    
    def get_handler_for_file(self, file_info: FileTypeInfo) -> Optional[Callable]:
        """Get the best handler for a specific file type"""
        handlers = self.get_handlers_for_category(file_info.category)
        return handlers[0] if handlers else self.default_handlers.get(file_info.category)
    
    def get_handler_by_extension(self, extension: str) -> Optional[Callable]:
        """Get handler by file extension"""
        # Find the file type info for this extension
        file_type = self._get_file_type_by_extension(extension)
        if file_type:
            return self.get_handler_for_file(file_type)
        return None
    
    def _get_file_type_by_extension(self, extension: str) -> Optional[FileTypeInfo]:
        """Get file type info by extension"""
        extension = extension.lower()
        for file_type in FileTypeInfo:
            if file_type.extension == extension:
                return file_type
        return None


class GenericFileHandlerAgent(BaseAgent):
    """
    Generic File Handler Agent - Processes any uploaded file type for metadata extraction,
    analysis, and processing. This agent generalizes the spectral-specific workflow to handle
    arbitrary file types while maintaining specialized handling for known formats.
    """

    # Supported file extensions by category
    SUPPORTED_EXTENSIONS = {
        FileCategory.SPECTRAL: ['.csv', '.json', '.h5', '.jdx', '.spc', '.txt'],
        FileCategory.TABULAR: ['.csv', '.xlsx', '.xls', '.parquet', '.feather'],
        FileCategory.TEXT: ['.txt', '.json', '.xml', '.yaml', '.yml', '.md'],
        FileCategory.IMAGE: ['.png', '.jpg', '.jpeg', '.gif', '.tiff', '.webp', '.svg'],
        FileCategory.AUDIO: ['.wav', '.mp3', '.ogg', '.flac'],
        FileCategory.VIDEO: ['.mp4', '.avi', '.mov', '.wmv'],
        FileCategory.ARCHIVE: ['.zip', '.tar', '.gz', '.rar', '.7z'],
        FileCategory.DOCUMENT: ['.pdf', '.docx', '.doc', '.pptx'],
        FileCategory.BINARY: ['.bin', '.dat', '.exe', '.dll', '.so']
    }
    
    # MIME type to category mapping
    MIME_TYPE_MAPPING = {
        'text/csv': FileCategory.TABULAR,
        'application/json': FileCategory.TEXT,
        'application/x-hdf5': FileCategory.SPECTRAL,
        'chemical/x-jcamp-dx': FileCategory.SPECTRAL,
        'text/plain': FileCategory.TEXT,
        'application/xml': FileCategory.TEXT,
        'text/xml': FileCategory.TEXT,
        'application/x-yaml': FileCategory.TEXT,
        'text/yaml': FileCategory.TEXT,
        'image/png': FileCategory.IMAGE,
        'image/jpeg': FileCategory.IMAGE,
        'image/gif': FileCategory.IMAGE,
        'image/tiff': FileCategory.IMAGE,
        'image/webp': FileCategory.IMAGE,
        'image/svg+xml': FileCategory.IMAGE,
        'audio/wav': FileCategory.AUDIO,
        'audio/mpeg': FileCategory.AUDIO,
        'audio/ogg': FileCategory.AUDIO,
        'audio/flac': FileCategory.AUDIO,
        'video/mp4': FileCategory.VIDEO,
        'video/x-msvideo': FileCategory.VIDEO,
        'video/quicktime': FileCategory.VIDEO,
        'application/zip': FileCategory.ARCHIVE,
        'application/x-tar': FileCategory.ARCHIVE,
        'application/gzip': FileCategory.ARCHIVE,
        'application/pdf': FileCategory.DOCUMENT,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': FileCategory.TABULAR,
        'application/vnd.ms-excel': FileCategory.TABULAR
    }

    def __init__(self, **kwargs):
        super().__init__(name="GenericFileHandlerAgent", version="1.0.0", **kwargs)
        
        # Dependencies
        self.dependencies = ["pandas", "numpy"]
        if MAGIC_AVAILABLE:
            self.dependencies.append("python-magic")
        
        # Configuration
        self.input_directory = kwargs.get("input_directory", "data/uploads")
        self.output_directory = kwargs.get("output_directory", "data/processed")
        self.temp_directory = kwargs.get("temp_directory", "data/temp")
        self.max_file_size = kwargs.get("max_file_size", 500 * 1024 * 1024)  # 500MB default
        self.batch_size = kwargs.get("batch_size", 100)
        
        # Initialize handler registry
        self.handler_registry = FileHandlerRegistry()
        self._initialize_handlers()
        
        # Track statistics
        self.processing_stats = {
            "total_files_processed": 0,
            "successful_processing": 0,
            "failed_processing": 0,
            "files_by_category": {},
            "average_processing_time_ms": 0.0,
            "total_processing_time_ms": 0.0
        }
        
        # Initialize directories
        self._initialize_directories()

    def _initialize_directories(self) -> bool:
        """Initialize all required directories"""
        try:
            directories = [
                self.input_directory,
                self.output_directory,
                self.temp_directory,
                os.path.join(self.output_directory, "metadata"),
                os.path.join(self.output_directory, "processed"),
                os.path.join(self.output_directory, "reports"),
                os.path.join(self.temp_directory, "extracted"),
                os.path.join(self.temp_directory, "uploads")
            ]
            
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
            
            self.logger.info("Initialized directories")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to initialize directories: {str(e)}", ErrorSeverity.HIGH)
            return False

    def _initialize_handlers(self):
        """Initialize the handler registry with built-in handlers"""
        # Register built-in handlers for each category
        self.handler_registry.register_handler(
            FileCategory.SPECTRAL, 
            self._handle_spectral_file,
            HandlerCapability(
                handler_name="spectral_handler",
                supported_categories=[FileCategory.SPECTRAL],
                supported_extensions=['.csv', '.json', '.h5', '.jdx', '.spc'],
                can_extract_metadata=True,
                can_analyze_content=True,
                can_generate_report=True,
                can_preprocess=True,
                priority=10
            ),
            is_default=True
        )
        
        self.handler_registry.register_handler(
            FileCategory.TABULAR,
            self._handle_tabular_file,
            HandlerCapability(
                handler_name="tabular_handler",
                supported_categories=[FileCategory.TABULAR],
                supported_extensions=['.csv', '.xlsx', '.xls', '.parquet'],
                can_extract_metadata=True,
                can_analyze_content=True,
                can_generate_report=True,
                can_preprocess=True,
                priority=10
            ),
            is_default=True
        )
        
        self.handler_registry.register_handler(
            FileCategory.TEXT,
            self._handle_text_file,
            HandlerCapability(
                handler_name="text_handler",
                supported_categories=[FileCategory.TEXT],
                supported_extensions=['.txt', '.json', '.xml', '.yaml', '.yml', '.md'],
                can_extract_metadata=True,
                can_analyze_content=True,
                can_generate_report=True,
                priority=10
            ),
            is_default=True
        )
        
        self.handler_registry.register_handler(
            FileCategory.IMAGE,
            self._handle_image_file,
            HandlerCapability(
                handler_name="image_handler",
                supported_categories=[FileCategory.IMAGE],
                supported_extensions=['.png', '.jpg', '.jpeg', '.gif', '.tiff', '.webp', '.svg'],
                can_extract_metadata=True,
                can_analyze_content=True,
                can_generate_report=True,
                priority=10
            ),
            is_default=True
        )
        
        self.handler_registry.register_handler(
            FileCategory.AUDIO,
            self._handle_audio_file,
            HandlerCapability(
                handler_name="audio_handler",
                supported_categories=[FileCategory.AUDIO],
                supported_extensions=['.wav', '.mp3', '.ogg', '.flac'],
                can_extract_metadata=True,
                can_analyze_content=True,
                can_generate_report=True,
                priority=10
            ),
            is_default=True
        )
        
        self.handler_registry.register_handler(
            FileCategory.ARCHIVE,
            self._handle_archive_file,
            HandlerCapability(
                handler_name="archive_handler",
                supported_categories=[FileCategory.ARCHIVE],
                supported_extensions=['.zip', '.tar', '.gz', '.rar', '.7z'],
                can_extract_metadata=True,
                can_analyze_content=True,
                can_generate_report=True,
                priority=10
            ),
            is_default=True
        )
        
        # Generic fallback handler for unknown file types
        self.handler_registry.register_handler(
            FileCategory.UNKNOWN,
            self._handle_generic_file,
            HandlerCapability(
                handler_name="generic_handler",
                supported_categories=[FileCategory.UNKNOWN],
                supported_extensions=['*'],
                can_extract_metadata=True,
                can_analyze_content=False,
                can_generate_report=True,
                priority=1
            ),
            is_default=True
        )

    def _detect_file_category(self, file_path: str) -> FileCategory:
        """Detect the category of a file based on extension and content"""
        extension = os.path.splitext(file_path)[1].lower()
        
        # First, try to detect by extension
        for category, extensions in self.SUPPORTED_EXTENSIONS.items():
            if extension in extensions:
                return category
        
        # If extension not found, try MIME type detection
        if MAGIC_AVAILABLE:
            try:
                mime_type = magic.from_file(file_path, mime=True)
                if mime_type in self.MIME_TYPE_MAPPING:
                    return self.MIME_TYPE_MAPPING[mime_type]
            except:
                pass
        
        # Fallback to content-based detection
        try:
            mime_type = mimetypes.guess_type(file_path)[0]
            if mime_type and mime_type in self.MIME_TYPE_MAPPING:
                return self.MIME_TYPE_MAPPING[mime_type]
        except:
            pass
        
        # Default to unknown
        return FileCategory.UNKNOWN

    def _extract_basic_metadata(self, file_path: str) -> FileMetadata:
        """Extract basic metadata from any file"""
        try:
            file_stat = os.stat(file_path)
            
            file_name = os.path.basename(file_path)
            file_extension = os.path.splitext(file_path)[1].lower()
            file_size = file_stat.st_size
            file_category = self._detect_file_category(file_path)
            
            # Get file timestamps
            created_timestamp = datetime.fromtimestamp(file_stat.st_ctime) if hasattr(file_stat, 'st_ctime') else None
            modified_timestamp = datetime.fromtimestamp(file_stat.st_mtime) if hasattr(file_stat, 'st_mtime') else None
            accessed_timestamp = datetime.fromtimestamp(file_stat.st_atime) if hasattr(file_stat, 'st_atime') else None
            
            # Try to get MIME type
            mime_type = None
            if MAGIC_AVAILABLE:
                try:
                    mime_type = magic.from_file(file_path, mime=True)
                except:
                    pass
            
            if not mime_type:
                try:
                    mime_type = mimetypes.guess_type(file_path)[0]
                except:
                    pass
            
            # Calculate file hashes for integrity
            md5_hash = self._calculate_md5(file_path)
            sha1_hash = self._calculate_sha1(file_path)
            
            metadata = FileMetadata(
                file_name=file_name,
                file_path=file_path,
                file_size=file_size,
                file_extension=file_extension,
                file_category=file_category,
                mime_type=mime_type,
                created_timestamp=created_timestamp,
                modified_timestamp=modified_timestamp,
                accessed_timestamp=accessed_timestamp,
                md5_hash=md5_hash,
                sha1_hash=sha1_hash,
                processing_timestamp=datetime.now()
            )
            
            return metadata
            
        except Exception as e:
            self.log_error(f"Failed to extract basic metadata from {file_path}: {str(e)}", 
                         ErrorSeverity.MEDIUM)
            return None

    def _calculate_md5(self, file_path: str) -> Optional[str]:
        """Calculate MD5 hash of a file"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.warning(f"Failed to calculate MD5 hash: {str(e)}")
            return None

    def _calculate_sha1(self, file_path: str) -> Optional[str]:
        """Calculate SHA1 hash of a file"""
        try:
            hash_sha1 = hashlib.sha1()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha1.update(chunk)
            return hash_sha1.hexdigest()
        except Exception as e:
            self.logger.warning(f"Failed to calculate SHA1 hash: {str(e)}")
            return None

    def _handle_spectral_file(self, file_path: str, metadata: FileMetadata) -> FileProcessingResult:
        """Handle spectral data files"""
        import time
        start_time = time.time()
        
        try:
            # Use existing spectral data loading logic from data_preparation_agent
            from .data_preparation_agent import EnhancedDataPreparationAgent
            
            spectral_agent = EnhancedDataPreparationAgent(
                input_directory=os.path.dirname(file_path),
                output_directory=self.output_directory,
                temp_directory=self.temp_directory
            )
            
            # Load spectral data
            spectral_data = spectral_agent._load_spectral_data(file_path)
            if spectral_data is None:
                return FileProcessingResult(
                    file_path=file_path,
                    success=False,
                    file_metadata=metadata,
                    processing_errors=["Failed to load spectral data"],
                    processing_time_ms=(time.time() - start_time) * 1000
                )
            
            # Extract additional metadata from spectral data
            metadata.custom_metadata.update({
                "wavelength_column": spectral_data.get("wavelength_column"),
                "intensity_column": spectral_data.get("intensity_column"),
                "data_format": spectral_data.get("format"),
                "num_data_points": len(spectral_data.get("data", []))
            })
            
            # Validate data structure
            if hasattr(spectral_agent, '_validate_data_structure'):
                if not spectral_agent._validate_data_structure(spectral_data):
                    metadata.quality_issues = metadata.quality_issues or []
                    metadata.quality_issues.append("Invalid spectral data structure")
            
            # Assess metadata quality
            if hasattr(spectral_agent, '_assess_metadata_quality'):
                quality_result = spectral_agent._assess_metadata_quality(
                    spectral_data.get("metadata", {}), file_path
                )
                metadata.quality_score = quality_result.completeness_score
                metadata.custom_metadata["metadata_quality"] = {
                    "completeness_score": quality_result.completeness_score,
                    "standards_compliance": quality_result.standards_compliance,
                    "quality_grade": quality_result.quality_grade.value,
                    "missing_required_fields": quality_result.missing_required_fields,
                    "missing_optional_fields": quality_result.missing_optional_fields
                }
            
            processing_time = (time.time() - start_time) * 1000
            
            return FileProcessingResult(
                file_path=file_path,
                success=True,
                file_metadata=metadata,
                extracted_data=spectral_data,
                processing_time_ms=processing_time,
                analysis_results={
                    "file_type": "spectral",
                    "data_points": len(spectral_data.get("data", [])),
                    "columns": list(spectral_data.get("data", pd.DataFrame()).columns) if isinstance(spectral_data.get("data"), pd.DataFrame) else []
                },
                recommendations=[
                    {
                        "type": "data_quality",
                        "description": "Consider validating spectral data quality",
                        "priority": "medium"
                    }
                ]
            )
            
        except Exception as e:
            self.log_error(f"Failed to process spectral file {file_path}: {str(e)}", 
                         ErrorSeverity.MEDIUM)
            return FileProcessingResult(
                file_path=file_path,
                success=False,
                file_metadata=metadata,
                processing_errors=[str(e)],
                processing_time_ms=(time.time() - start_time) * 1000
            )

    def _handle_tabular_file(self, file_path: str, metadata: FileMetadata) -> FileProcessingResult:
        """Handle tabular data files (CSV, Excel, etc.)"""
        import time
        start_time = time.time()
        
        try:
            # Try to read the file based on extension
            extension = metadata.file_extension.lower()
            
            if extension in ['.csv']:
                df = pd.read_csv(file_path)
            elif extension in ['.xlsx', '.xls']:
                try:
                    df = pd.read_excel(file_path)
                except ImportError:
                    self.log_error("Excel support requires openpyxl or xlrd", ErrorSeverity.MEDIUM)
                    return FileProcessingResult(
                        file_path=file_path,
                        success=False,
                        file_metadata=metadata,
                        processing_errors=["Excel support requires openpyxl or xlrd"],
                        processing_time_ms=(time.time() - start_time) * 1000
                    )
            elif extension in ['.parquet']:
                try:
                    df = pd.read_parquet(file_path)
                except ImportError:
                    self.log_error("Parquet support requires pyarrow or fastparquet", ErrorSeverity.MEDIUM)
                    return FileProcessingResult(
                        file_path=file_path,
                        success=False,
                        file_metadata=metadata,
                        processing_errors=["Parquet support requires pyarrow or fastparquet"],
                        processing_time_ms=(time.time() - start_time) * 1000
                    )
            elif extension in ['.feather']:
                try:
                    df = pd.read_feather(file_path)
                except ImportError:
                    self.log_error("Feather support requires pyarrow", ErrorSeverity.MEDIUM)
                    return FileProcessingResult(
                        file_path=file_path,
                        success=False,
                        file_metadata=metadata,
                        processing_errors=["Feather support requires pyarrow"],
                        processing_time_ms=(time.time() - start_time) * 1000
                    )
            else:
                # Try CSV as fallback
                df = pd.read_csv(file_path)
            
            # Extract metadata from DataFrame
            metadata.num_rows = len(df)
            metadata.num_columns = len(df.columns)
            metadata.column_names = list(df.columns)
            metadata.data_types = {col: str(dtype) for col, dtype in df.dtypes.items()}
            
            # Check for potential spectral data
            wavelength_patterns = ['wavelength', 'wave', 'lambda', 'nm', 'wavenumber']
            intensity_patterns = ['intensity', 'absorbance', 'reflectance', 'transmittance', 'value']
            
            wavelength_col = None
            intensity_col = None
            
            for col in df.columns:
                col_lower = col.lower()
                if any(pattern in col_lower for pattern in wavelength_patterns):
                    wavelength_col = col
                elif any(pattern in col_lower for pattern in intensity_patterns):
                    intensity_col = col
            
            if wavelength_col and intensity_col:
                metadata.custom_metadata["potential_spectral_data"] = True
                metadata.custom_metadata["wavelength_column"] = wavelength_col
                metadata.custom_metadata["intensity_column"] = intensity_col
            
            processing_time = (time.time() - start_time) * 1000
            
            return FileProcessingResult(
                file_path=file_path,
                success=True,
                file_metadata=metadata,
                extracted_data={"dataframe": df.to_dict(orient='records')},
                processing_time_ms=processing_time,
                analysis_results={
                    "file_type": "tabular",
                    "num_rows": len(df),
                    "num_columns": len(df.columns),
                    "columns": list(df.columns),
                    "data_types": {col: str(dtype) for col, dtype in df.dtypes.items()}
                },
                recommendations=[
                    {
                        "type": "data_analysis",
                        "description": "Consider statistical analysis of tabular data",
                        "priority": "low"
                    }
                ]
            )
            
        except Exception as e:
            self.log_error(f"Failed to process tabular file {file_path}: {str(e)}", 
                         ErrorSeverity.MEDIUM)
            return FileProcessingResult(
                file_path=file_path,
                success=False,
                file_metadata=metadata,
                processing_errors=[str(e)],
                processing_time_ms=(time.time() - start_time) * 1000
            )

    def _handle_text_file(self, file_path: str, metadata: FileMetadata) -> FileProcessingResult:
        """Handle text-based files"""
        import time
        start_time = time.time()
        
        try:
            extension = metadata.file_extension.lower()
            
            # Read the file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract text metadata
            lines = content.split('\n')
            words = content.split()
            
            metadata.num_lines = len(lines)
            metadata.num_words = len(words)
            metadata.num_characters = len(content)
            
            # Try to parse structured text formats
            if extension in ['.json']:
                try:
                    import json
                    data = json.loads(content)
                    metadata.custom_metadata["json_structure"] = self._analyze_json_structure(data)
                    metadata.content_type = "application/json"
                except:
                    metadata.content_type = "text/plain"
            elif extension in ['.xml']:
                try:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(content)
                    metadata.custom_metadata["xml_root"] = root.tag
                    metadata.content_type = "application/xml"
                except:
                    metadata.content_type = "text/plain"
            elif extension in ['.yaml', '.yml']:
                try:
                    import yaml
                    data = yaml.safe_load(content)
                    metadata.custom_metadata["yaml_structure"] = self._analyze_yaml_structure(data)
                    metadata.content_type = "application/x-yaml"
                except:
                    metadata.content_type = "text/plain"
            else:
                metadata.content_type = "text/plain"
            
            processing_time = (time.time() - start_time) * 1000
            
            return FileProcessingResult(
                file_path=file_path,
                success=True,
                file_metadata=metadata,
                extracted_data={"content": content[:10000]} if len(content) > 10000 else {"content": content},
                processing_time_ms=processing_time,
                analysis_results={
                    "file_type": "text",
                    "num_lines": len(lines),
                    "num_words": len(words),
                    "num_characters": len(content),
                    "content_type": metadata.content_type
                },
                recommendations=[
                    {
                        "type": "text_analysis",
                        "description": "Consider natural language processing for text content",
                        "priority": "low"
                    }
                ]
            )
            
        except Exception as e:
            self.log_error(f"Failed to process text file {file_path}: {str(e)}", 
                         ErrorSeverity.MEDIUM)
            return FileProcessingResult(
                file_path=file_path,
                success=False,
                file_metadata=metadata,
                processing_errors=[str(e)],
                processing_time_ms=(time.time() - start_time) * 1000
            )

    def _handle_image_file(self, file_path: str, metadata: FileMetadata) -> FileProcessingResult:
        """Handle image files"""
        import time
        start_time = time.time()
        
        try:
            extension = metadata.file_extension.lower()
            
            # Try to extract image metadata
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    metadata.image_width = img.width
                    metadata.image_height = img.height
                    metadata.image_format = img.format
                    metadata.image_channels = len(img.getbands()) if img.mode != 'P' else 1
                    
                    # Get additional EXIF data if available
                    if hasattr(img, '_getexif'):
                        exif_data = img._getexif()
                        if exif_data:
                            metadata.custom_metadata["exif_data"] = { 
                                tag: value for tag, value in exif_data.items() 
                                if tag in [0x010F, 0x0110, 0x0112, 0x0132]  # Common EXIF tags
                            }
            except ImportError:
                self.logger.warning("PIL/Pillow not available for image metadata extraction")
            except Exception as e:
                self.logger.warning(f"Failed to extract image metadata: {str(e)}")
            
            processing_time = (time.time() - start_time) * 1000
            
            return FileProcessingResult(
                file_path=file_path,
                success=True,
                file_metadata=metadata,
                processing_time_ms=processing_time,
                analysis_results={
                    "file_type": "image",
                    "width": metadata.image_width,
                    "height": metadata.image_height,
                    "format": metadata.image_format,
                    "channels": metadata.image_channels
                },
                recommendations=[
                    {
                        "type": "image_analysis",
                        "description": "Consider computer vision analysis for images",
                        "priority": "low"
                    }
                ]
            )
            
        except Exception as e:
            self.log_error(f"Failed to process image file {file_path}: {str(e)}", 
                         ErrorSeverity.MEDIUM)
            return FileProcessingResult(
                file_path=file_path,
                success=False,
                file_metadata=metadata,
                processing_errors=[str(e)],
                processing_time_ms=(time.time() - start_time) * 1000
            )

    def _handle_audio_file(self, file_path: str, metadata: FileMetadata) -> FileProcessingResult:
        """Handle audio files"""
        import time
        start_time = time.time()
        
        try:
            extension = metadata.file_extension.lower()
            
            # Try to extract audio metadata
            try:
                import librosa
                y, sr = librosa.load(file_path, sr=None, duration=10)  # Load first 10 seconds
                metadata.audio_duration = librosa.get_duration(y=y, sr=sr)
                metadata.audio_sample_rate = sr
                metadata.audio_channels = 1 if len(y.shape) == 1 else y.shape[0]
                
                # Get additional audio features
                metadata.custom_metadata["audio_features"] = {
                    "duration": metadata.audio_duration,
                    "sample_rate": sr,
                    "num_samples": len(y)
                }
            except ImportError:
                self.logger.warning("librosa not available for audio metadata extraction")
            except Exception as e:
                self.logger.warning(f"Failed to extract audio metadata: {str(e)}")
            
            processing_time = (time.time() - start_time) * 1000
            
            return FileProcessingResult(
                file_path=file_path,
                success=True,
                file_metadata=metadata,
                processing_time_ms=processing_time,
                analysis_results={
                    "file_type": "audio",
                    "duration": metadata.audio_duration,
                    "sample_rate": metadata.audio_sample_rate,
                    "channels": metadata.audio_channels
                },
                recommendations=[
                    {
                        "type": "audio_analysis",
                        "description": "Consider audio signal processing and feature extraction",
                        "priority": "low"
                    }
                ]
            )
            
        except Exception as e:
            self.log_error(f"Failed to process audio file {file_path}: {str(e)}", 
                         ErrorSeverity.MEDIUM)
            return FileProcessingResult(
                file_path=file_path,
                success=False,
                file_metadata=metadata,
                processing_errors=[str(e)],
                processing_time_ms=(time.time() - start_time) * 1000
            )

    def _handle_archive_file(self, file_path: str, metadata: FileMetadata) -> FileProcessingResult:
        """Handle archive files (ZIP, TAR, etc.)"""
        import time
        import zipfile
        import tarfile
        start_time = time.time()
        
        try:
            extension = metadata.file_extension.lower()
            extracted_files = []
            
            if extension == '.zip':
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    metadata.archive_contents = file_list
                    metadata.archive_num_files = len(file_list)
                    
                    # Extract basic info about each file
                    for file_info in zip_ref.infolist():
                        extracted_files.append({
                            "name": file_info.filename,
                            "size": file_info.file_size,
                            "compressed_size": file_info.compress_size,
                            "is_directory": file_info.is_dir()
                        })
            elif extension in ['.tar', '.gz']:
                mode = 'r:gz' if extension == '.gz' else 'r'
                with tarfile.open(file_path, mode) as tar_ref:
                    file_list = tar_ref.getnames()
                    metadata.archive_contents = file_list
                    metadata.archive_num_files = len(file_list)
                    
                    for member in tar_ref.getmembers():
                        extracted_files.append({
                            "name": member.name,
                            "size": member.size,
                            "is_directory": member.isdir()
                        })
            
            metadata.custom_metadata["extracted_files_info"] = extracted_files
            
            processing_time = (time.time() - start_time) * 1000
            
            return FileProcessingResult(
                file_path=file_path,
                success=True,
                file_metadata=metadata,
                processing_time_ms=processing_time,
                analysis_results={
                    "file_type": "archive",
                    "num_files": metadata.archive_num_files,
                    "contents": metadata.archive_contents
                },
                recommendations=[
                    {
                        "type": "archive_processing",
                        "description": "Consider extracting and processing individual files from archive",
                        "priority": "medium"
                    }
                ]
            )
            
        except Exception as e:
            self.log_error(f"Failed to process archive file {file_path}: {str(e)}", 
                         ErrorSeverity.MEDIUM)
            return FileProcessingResult(
                file_path=file_path,
                success=False,
                file_metadata=metadata,
                processing_errors=[str(e)],
                processing_time_ms=(time.time() - start_time) * 1000
            )

    def _handle_generic_file(self, file_path: str, metadata: FileMetadata) -> FileProcessingResult:
        """Handle generic/unknown file types"""
        import time
        start_time = time.time()
        
        try:
            # For unknown file types, we can still extract basic metadata
            # and provide recommendations for handling
            
            # Try to read as text if it's not too large
            if metadata.file_size < 1024 * 1024:  # 1MB
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(1024)  # Read first 1KB
                    metadata.custom_metadata["file_preview"] = content
                except:
                    pass
            
            processing_time = (time.time() - start_time) * 1000
            
            return FileProcessingResult(
                file_path=file_path,
                success=True,
                file_metadata=metadata,
                processing_time_ms=processing_time,
                analysis_results={
                    "file_type": "unknown",
                    "file_size": metadata.file_size,
                    "file_extension": metadata.file_extension
                },
                recommendations=[
                    {
                        "type": "file_identification",
                        "description": "Unable to determine file type - consider manual inspection",
                        "priority": "high"
                    },
                    {
                        "type": "format_conversion",
                        "description": "Consider converting to a supported format",
                        "priority": "medium"
                    }
                ]
            )
            
        except Exception as e:
            self.log_error(f"Failed to process generic file {file_path}: {str(e)}", 
                         ErrorSeverity.MEDIUM)
            return FileProcessingResult(
                file_path=file_path,
                success=False,
                file_metadata=metadata,
                processing_errors=[str(e)],
                processing_time_ms=(time.time() - start_time) * 1000
            )

    def _analyze_json_structure(self, data: Any) -> Dict[str, Any]:
        """Analyze the structure of JSON data"""
        result = {"type": type(data).__name__}
        
        if isinstance(data, dict):
            result["num_keys"] = len(data)
            result["keys"] = list(data.keys())
            result["nested_structure"] = {}
            for key, value in data.items():
                result["nested_structure"][key] = type(value).__name__
        elif isinstance(data, list):
            result["num_items"] = len(data)
            if len(data) > 0:
                result["first_item_type"] = type(data[0]).__name__
        
        return result

    def _analyze_yaml_structure(self, data: Any) -> Dict[str, Any]:
        """Analyze the structure of YAML data"""
        return self._analyze_json_structure(data)  # Same as JSON for now

    def _process_single_file(self, file_path: str) -> FileProcessingResult:
        """Process a single file through the complete pipeline"""
        import time
        start_time = time.time()
        
        try:
            self.logger.info(f"Processing file: {file_path}")
            
            # Check file size limit
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                return FileProcessingResult(
                    file_path=file_path,
                    success=False,
                    processing_errors=[f"File too large: {file_size} bytes > {self.max_file_size} bytes limit"],
                    processing_time_ms=(time.time() - start_time) * 1000
                )
            
            # Extract basic metadata
            metadata = self._extract_basic_metadata(file_path)
            if metadata is None:
                return FileProcessingResult(
                    file_path=file_path,
                    success=False,
                    processing_errors=["Failed to extract basic metadata"],
                    processing_time_ms=(time.time() - start_time) * 1000
                )
            
            # Get the appropriate handler for this file type
            handler = None
            if metadata.file_category != FileCategory.UNKNOWN:
                handlers = self.handler_registry.get_handlers_for_category(metadata.file_category)
                if handlers:
                    handler = handlers[0]  # Use the highest priority handler
            
            if handler is None:
                # Fallback to generic handler
                handler = self._handle_generic_file
            
            # Process the file with the appropriate handler
            result = handler(file_path, metadata)
            
            # Update statistics
            self.processing_stats["total_files_processed"] += 1
            self.processing_stats["total_processing_time_ms"] += result.processing_time_ms
            
            if result.success:
                self.processing_stats["successful_processing"] += 1
                # Track files by category
                category_key = result.file_metadata.file_category.value
                self.processing_stats["files_by_category"][category_key] = \
                    self.processing_stats["files_by_category"].get(category_key, 0) + 1
            else:
                self.processing_stats["failed_processing"] += 1
            
            # Update average processing time
            if self.processing_stats["total_files_processed"] > 0:
                self.processing_stats["average_processing_time_ms"] = \
                    self.processing_stats["total_processing_time_ms"] / \
                    self.processing_stats["total_files_processed"]
            
            self.logger.info(f"Successfully processed file: {file_path}")
            return result
            
        except Exception as e:
            self.log_error(f"Failed to process file {file_path}: {str(e)}", ErrorSeverity.HIGH)
            return FileProcessingResult(
                file_path=file_path,
                success=False,
                processing_errors=[str(e)],
                processing_time_ms=(time.time() - start_time) * 1000
            )

    def _process_batch(self, file_paths: List[str]) -> List[FileProcessingResult]:
        """Process a batch of files"""
        results = []
        
        for file_path in file_paths:
            result = self._process_single_file(file_path)
            results.append(result)
            
            # Check if we should pause for batch processing
            if len(results) % self.batch_size == 0:
                self.logger.info(f"Processed {len(results)} files in current batch")
        
        return results

    def execute(self, context: Dict[str, Any] = None) -> AgentOutput:
        """
        Execute the Generic File Handler Agent's complete workflow.
        
        This method orchestrates the entire file processing pipeline including:
        1. Input validation
        2. File discovery and categorization
        3. Metadata extraction for all file types
        4. Content analysis based on file type
        5. Quality assessment
        6. Results saving and reporting
        
        Args:
            context: Dictionary containing execution context with optional parameters:
                - input_directory: Override default input directory
                - output_directory: Override default output directory
                - file_paths: Specific files to process (overrides directory scan)
                - max_file_size: Maximum file size to process
                - batch_size: Number of files to process in each batch
                
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
                if "max_file_size" in context:
                    self.max_file_size = context["max_file_size"]
                if "batch_size" in context:
                    self.batch_size = context["batch_size"]
            
            # Re-initialize directories with potentially updated paths
            self._initialize_directories()
            
            # Validate input directory
            if not os.path.exists(self.input_directory):
                self.log_error(
                    f"Input directory not found: {self.input_directory}",
                    ErrorSeverity.CRITICAL,
                    {"suggested_fix": f"Create directory: mkdir -p {self.input_directory}"}
                )
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
                # Discover all files in input directory
                all_extensions = []
                for extensions in self.SUPPORTED_EXTENSIONS.values():
                    all_extensions.extend(extensions)
                
                files_to_process = [
                    os.path.join(self.input_directory, f)
                    for f in os.listdir(self.input_directory)
                    if any(f.lower().endswith(ext) for ext in all_extensions)
                ]
            
            if not files_to_process:
                return self._create_success_output({
                    "status": "no_files_found",
                    "input_directory": self.input_directory,
                    "supported_extensions": all_extensions
                })
            
            self.logger.info(f"Starting processing of {len(files_to_process)} files")
            
            # Process files in batches
            results = self._process_batch(files_to_process)
            
            # Generate comprehensive report
            report_data = self._generate_comprehensive_report(results)
            
            # Save report to file
            report_path = os.path.join(
                self.output_directory, "reports",
                f"file_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
                "files_processed": len(results),
                "successful_files": len([r for r in results if r.success]),
                "failed_files": len([r for r in results if not r.success]),
                "processing_results": [
                    {
                        "file_path": r.file_path,
                        "success": r.success,
                        "file_category": r.file_metadata.file_category.value if r.file_metadata else "unknown",
                        "file_size": r.file_metadata.file_size if r.file_metadata else 0,
                        "processing_time_ms": r.processing_time_ms,
                        "errors": r.processing_errors,
                        "analysis_summary": r.analysis_results
                    }
                    for r in results
                ],
                "report": report_data,
                "processing_statistics": self.processing_stats,
                "configuration": {
                    "input_directory": self.input_directory,
                    "output_directory": self.output_directory,
                    "max_file_size": self.max_file_size,
                    "batch_size": self.batch_size
                }
            }
            
            self.status = AgentStatus.COMPLETED
            self.logger.info(f"File processing completed. Processed {len(results)} files.")
            
            return self._create_success_output(output_data)
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.log_error(f"Execution failed: {str(e)}", ErrorSeverity.CRITICAL)
            return self._handle_error(e)

    def _generate_comprehensive_report(self, results: List[FileProcessingResult]) -> Dict[str, Any]:
        """Generate a comprehensive report from processing results"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_files": len(results),
                "successful": len([r for r in results if r.success]),
                "failed": len([r for r in results if not r.success]),
                "success_rate": len([r for r in results if r.success]) / len(results) if results else 0
            },
            "files_by_category": {},
            "files_by_type": {},
            "quality_metrics": {
                "average_processing_time_ms": 0,
                "total_processing_time_ms": 0,
                "size_distribution": {"min": float('inf'), "max": 0, "total": 0}
            },
            "recommendations": [],
            "errors": []
        }
        
        # Categorize results
        for result in results:
            if result.file_metadata:
                category = result.file_metadata.file_category.value
                file_type = result.file_metadata.file_extension
                
                # Count by category
                report["files_by_category"][category] = report["files_by_category"].get(category, 0) + 1
                
                # Count by file type
                report["files_by_type"][file_type] = report["files_by_type"].get(file_type, 0) + 1
                
                # Update quality metrics
                report["quality_metrics"]["total_processing_time_ms"] += result.processing_time_ms
                
                # Update size distribution
                if result.file_metadata.file_size > 0:
                    report["quality_metrics"]["size_distribution"]["min"] = min(
                        report["quality_metrics"]["size_distribution"]["min"], 
                        result.file_metadata.file_size
                    )
                    report["quality_metrics"]["size_distribution"]["max"] = max(
                        report["quality_metrics"]["size_distribution"]["max"], 
                        result.file_metadata.file_size
                    )
                    report["quality_metrics"]["size_distribution"]["total"] += result.file_metadata.file_size
            
            # Collect errors
            if result.processing_errors:
                report["errors"].extend(result.processing_errors)
            
            # Collect recommendations
            if result.recommendations:
                report["recommendations"].extend(result.recommendations)
        
        # Calculate averages
        if len(results) > 0:
            report["quality_metrics"]["average_processing_time_ms"] = \
                report["quality_metrics"]["total_processing_time_ms"] / len(results)
        
        if report["quality_metrics"]["size_distribution"]["total"] > 0:
            report["quality_metrics"]["size_distribution"]["average"] = \
                report["quality_metrics"]["size_distribution"]["total"] / len(results)
        
        return report

    def register_custom_handler(self, category: FileCategory, handler: Callable, 
                               capability: HandlerCapability = None, is_default: bool = False):
        """Register a custom file handler for a specific category"""
        self.handler_registry.register_handler(category, handler, capability, is_default)
        self.logger.info(f"Registered custom handler for {category.value}")

    def get_supported_extensions(self) -> List[str]:
        """Get all supported file extensions"""
        extensions = []
        for category_extensions in self.SUPPORTED_EXTENSIONS.values():
            extensions.extend(category_extensions)
        return sorted(list(set(extensions)))

    def get_supported_categories(self) -> List[str]:
        """Get all supported file categories"""
        return [category.value for category in self.SUPPORTED_EXTENSIONS.keys()]

    def initialize(self) -> AgentOutput:
        """Initialize the agent"""
        self.status = AgentStatus.READY
        self.logger.info(f"{self.name} v{self.version} initialized")
        return AgentOutput(
            agent_name=self.name, 
            status=self.status, 
            version=self.version, 
            dependencies=self.dependencies
        )