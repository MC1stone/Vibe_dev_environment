#!/usr/bin/env python3
"""
NIR Intelligence Platform - ImageProcessorAgent
Agent for processing image files containing spectral data (PNG, JPG, TIFF, etc.)
"""

import logging
import os
import json
import tempfile
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ExifTags
from io import BytesIO
from .base_agent import BaseAgent, AgentOutput, AgentStatus, ErrorSeverity, AgentError


@dataclass
class ImageFormat:
    """Supported image format information"""
    name: str
    extension: str
    mime_type: str
    lossless: bool = True
    supports_metadata: bool = True
    supports_transparency: bool = False
    color_depth: int = 24


@dataclass
class ImageMetadata:
    """Extracted image file metadata"""
    file_path: str
    file_name: str
    file_size: int
    file_format: str
    width: int = 0
    height: int = 0
    channels: int = 0
    mode: str = ""
    bits_per_sample: int = 0
    color_space: str = ""
    compression: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    exif_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImageProcessingResult:
    """Result of image processing"""
    success: bool
    file_path: str
    processed_data: Optional[np.ndarray] = None
    processed_image: Optional[Image.Image] = None
    width: int = 0
    height: int = 0
    channels: int = 0
    spectral_data: Optional[Dict[str, Any]] = None
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class SpectralImageAnalysis:
    """Spectral analysis results from image data"""
    wavelength_range: Tuple[float, float] = (0.0, 0.0)
    intensity_profile: Optional[np.ndarray] = None
    spectral_signature: Optional[Dict[str, float]] = None
    color_analysis: Optional[Dict[str, Any]] = None
    spatial_analysis: Optional[Dict[str, Any]] = None
    quality_score: float = 0.0
    confidence: float = 0.0


class ImageProcessorAgent(BaseAgent):
    """
    Agent for processing image files containing spectral data
    
    Features:
    - Support for PNG, JPG, TIFF, BMP, GIF, and other image formats
    - Image file validation and metadata extraction
    - Image preprocessing (resizing, enhancement, filtering)
    - Spectral data extraction from images
    - Quality assessment and issue detection
    - Format conversion and standardization
    - EXIF metadata handling
    """
    
    def __init__(self, **kwargs):
        super().__init__(name="ImageProcessorAgent", version="2.0.0", **kwargs)
        self.dependencies = ['numpy', 'pandas', 'Pillow', 'opencv-python', 'scikit-image']
        self.logger = logging.getLogger(f"Agent.ImageProcessorAgent")
        
        # Configuration
        self.supported_formats = {
            'png': ImageFormat(
                name="PNG",
                extension=".png",
                mime_type="image/png",
                lossless=True,
                supports_metadata=True,
                supports_transparency=True,
                color_depth=48
            ),
            'jpg': ImageFormat(
                name="JPG",
                extension=".jpg",
                mime_type="image/jpeg",
                lossless=False,
                supports_metadata=True,
                supports_transparency=False,
                color_depth=24
            ),
            'jpeg': ImageFormat(
                name="JPEG",
                extension=".jpeg",
                mime_type="image/jpeg",
                lossless=False,
                supports_metadata=True,
                supports_transparency=False,
                color_depth=24
            ),
            'tiff': ImageFormat(
                name="TIFF",
                extension=".tiff",
                mime_type="image/tiff",
                lossless=True,
                supports_metadata=True,
                supports_transparency=True,
                color_depth=48
            ),
            'bmp': ImageFormat(
                name="BMP",
                extension=".bmp",
                mime_type="image/bmp",
                lossless=True,
                supports_metadata=False,
                supports_transparency=True,
                color_depth=24
            ),
            'gif': ImageFormat(
                name="GIF",
                extension=".gif",
                mime_type="image/gif",
                lossless=True,
                supports_metadata=False,
                supports_transparency=True,
                color_depth=8
            ),
            'webp': ImageFormat(
                name="WebP",
                extension=".webp",
                mime_type="image/webp",
                lossless=True,
                supports_metadata=True,
                supports_transparency=True,
                color_depth=24
            )
        }
        
        self.output_dir = kwargs.get('output_dir', 'processed_images')
        self.temp_dir = kwargs.get('temp_dir', tempfile.gettempdir())
        
        # Processing parameters
        self.default_quality = kwargs.get('default_quality', 85)
        self.max_file_size = kwargs.get('max_file_size', 50 * 1024 * 1024)  # 50MB
        self.max_width = kwargs.get('max_width', 4096)
        self.max_height = kwargs.get('max_height', 4096)
        self.auto_orient = kwargs.get('auto_orient', True)
        self.color_correction = kwargs.get('color_correction', False)
        self.enhancement = kwargs.get('enhancement', True)
        self.metadata_extraction = kwargs.get('metadata_extraction', True)
        self.exif_preservation = kwargs.get('exif_preservation', True)
        
        # Initialize agent-specific attributes
        self._initialize_attributes()
    
    def _initialize_attributes(self):
        """Initialize agent-specific attributes"""
        self.processed_files: Dict[str, ImageProcessingResult] = {}
        self.stats = {
            'files_processed': 0,
            'files_successful': 0,
            'files_failed': 0,
            'formats_detected': {},
            'processing_time': 0.0,
            'errors': 0
        }
        
        # Create output directory
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def detect_image_format(self, file_path: str) -> Optional[str]:
        """Detect the image format from file extension or content"""
        try:
            file_path = str(file_path).lower()
            
            # Check by file extension first
            for fmt, info in self.supported_formats.items():
                if file_path.endswith(info.extension):
                    return fmt
            
            # If extension not recognized, try to detect from file signature
            with open(file_path, 'rb') as f:
                header = f.read(16)
                
                # PNG signature
                if header.startswith(b'\x89PNG\r\n\x1a\n'):
                    return 'png'
                
                # JPEG signature
                if header.startswith(b'\xFF\xD8\xFF'):
                    return 'jpg'
                
                # GIF signature
                if header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
                    return 'gif'
                
                # BMP signature
                if header.startswith(b'BM'):
                    return 'bmp'
                
                # TIFF signature (little-endian and big-endian)
                if header.startswith(b'II\x2A\x00') or header.startswith(b'MM\x00\x2A'):
                    return 'tiff'
                
                # WebP signature
                if header.startswith(b'RIFF') and header[8:12] == b'WEBP':
                    return 'webp'
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error detecting image format for {file_path}: {str(e)}")
            return None
    
    def validate_image_file(self, file_path: str) -> Tuple[bool, str, Optional[ImageMetadata]]:
        """Validate an image file and extract basic metadata"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return False, f"File not found: {file_path}", None
            
            if file_path.stat().st_size == 0:
                return False, "File is empty", None
            
            if file_path.stat().st_size > self.max_file_size:
                return False, f"File too large (>{self.max_file_size} bytes)", None
            
            # Detect format
            image_format = self.detect_image_format(file_path)
            if not image_format:
                return False, "Unsupported image format", None
            
            # Try to open the image
            try:
                with Image.open(file_path) as img:
                    # Extract basic metadata
                    metadata = ImageMetadata(
                        file_path=str(file_path),
                        file_name=file_path.name,
                        file_size=file_path.stat().st_size,
                        file_format=image_format,
                        width=img.width,
                        height=img.height,
                        mode=img.mode,
                        channels=len(img.mode) if img.mode in ['RGB', 'RGBA', 'CMYK'] else 1,
                        color_space=img.mode,
                        compression=img.info.get('compression', 'unknown')
                    )
                    
                    # Extract EXIF data if available
                    if self.metadata_extraction and image_format.supports_metadata:
                        exif_data = self._extract_exif_data(img)
                        metadata.exif_data = exif_data
                        
                        # Extract additional metadata from EXIF
                        if 'ImageDescription' in exif_data:
                            metadata.metadata['description'] = exif_data['ImageDescription']
                        if 'Artist' in exif_data:
                            metadata.metadata['artist'] = exif_data['Artist']
                        if 'Copyright' in exif_data:
                            metadata.metadata['copyright'] = exif_data['Copyright']
                        if 'DateTime' in exif_data:
                            metadata.metadata['date_time'] = exif_data['DateTime']
                        if 'Software' in exif_data:
                            metadata.metadata['software'] = exif_data['Software']
                    
                    return True, "Valid image file", metadata
                    
            except Exception as e:
                return False, f"Error opening image: {str(e)}", None
                
        except Exception as e:
            return False, f"Validation error: {str(e)}", None
    
    def _extract_exif_data(self, img: Image.Image) -> Dict[str, Any]:
        """Extract EXIF metadata from image"""
        exif_data = {}
        try:
            if hasattr(img, '_getexif'):
                exif_info = img._getexif()
                if exif_info:
                    for tag_id, value in exif_info.items():
                        tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                        exif_data[tag_name] = value
            
            # Also check for GPS info
            if hasattr(img, '_getexif') and 'GPSInfo' in exif_data:
                gps_info = exif_data['GPSInfo']
                if gps_info:
                    exif_data['GPS'] = self._parse_gps_info(gps_info)
                    
        except Exception as e:
            self.logger.debug(f"Error extracting EXIF data: {str(e)}")
        
        return exif_data
    
    def _parse_gps_info(self, gps_info: Dict) -> Dict[str, float]:
        """Parse GPS information from EXIF data"""
        gps_data = {}
        try:
            if 2 in gps_info:  # GPSLatitude
                lat = self._convert_gps_coordinate(gps_info[2])
                if 1 in gps_info:  # GPSLatitudeRef
                    lat_ref = gps_info[1].decode('utf-8', 'ignore') if isinstance(gps_info[1], bytes) else gps_info[1]
                    if lat_ref == 'S':
                        lat = -lat
                gps_data['latitude'] = lat
            
            if 4 in gps_info:  # GPSLongitude
                lon = self._convert_gps_coordinate(gps_info[4])
                if 3 in gps_info:  # GPSLongitudeRef
                    lon_ref = gps_info[3].decode('utf-8', 'ignore') if isinstance(gps_info[3], bytes) else gps_info[3]
                    if lon_ref == 'W':
                        lon = -lon
                gps_data['longitude'] = lon
            
            if 6 in gps_info:  # GPSAltitude
                altitude = float(gps_info[6][0]) / float(gps_info[6][1])
                if 5 in gps_info:  # GPSAltitudeRef
                    alt_ref = gps_info[5].decode('utf-8', 'ignore') if isinstance(gps_info[5], bytes) else gps_info[5]
                    if alt_ref == 1:  # Below sea level
                        altitude = -altitude
                gps_data['altitude'] = altitude
                
        except Exception as e:
            self.logger.debug(f"Error parsing GPS info: {str(e)}")
        
        return gps_data
    
    def _convert_gps_coordinate(self, coord: Tuple) -> float:
        """Convert GPS coordinate from EXIF format to decimal degrees"""
        try:
            degrees = float(coord[0][0]) / float(coord[0][1])
            minutes = float(coord[1][0]) / float(coord[1][1])
            seconds = float(coord[2][0]) / float(coord[2][1])
            return degrees + (minutes / 60.0) + (seconds / 3600.0)
        except Exception:
            return 0.0
    
    def load_image_file(self, file_path: str) -> Tuple[bool, str, Optional[Image.Image]]:
        """Load image file and return PIL Image object"""
        try:
            file_path = Path(file_path)
            image_format = self.detect_image_format(file_path)
            
            if not image_format:
                return False, "Unsupported image format", None
            
            # Open image
            img = Image.open(file_path)
            
            # Auto-orient based on EXIF orientation
            if self.auto_orient:
                img = self._auto_orient_image(img)
            
            # Convert to RGB/RGBA if needed
            if img.mode not in ['RGB', 'RGBA', 'L', 'LA']:
                if img.mode == 'P':
                    img = img.convert('RGBA')
                elif img.mode == 'CMYK':
                    img = img.convert('RGB')
                else:
                    img = img.convert('RGB')
            
            return True, "Image loaded successfully", img
            
        except Exception as e:
            return False, f"Error loading image: {str(e)}", None
    
    def _auto_orient_image(self, img: Image.Image) -> Image.Image:
        """Auto-orient image based on EXIF orientation tag"""
        try:
            if hasattr(img, '_getexif'):
                exif_info = img._getexif()
                if exif_info:
                    orientation = exif_info.get(ExifTags.Base.Orientation, 1)
                    
                    if orientation == 3:
                        img = img.rotate(180, expand=True)
                    elif orientation == 6:
                        img = img.rotate(270, expand=True)
                    elif orientation == 8:
                        img = img.rotate(90, expand=True)
                    elif orientation == 5:
                        img = img.transpose(Image.FLIP_LEFT_RIGHT)
                        img = img.rotate(270, expand=True)
                    elif orientation == 7:
                        img = img.transpose(Image.FLIP_LEFT_RIGHT)
                        img = img.rotate(90, expand=True)
                    elif orientation == 2:
                        img = img.transpose(Image.FLIP_LEFT_RIGHT)
                    elif orientation == 4:
                        img = img.transpose(Image.FLIP_TOP_BOTTOM)
                        
        except Exception as e:
            self.logger.debug(f"Error auto-orienting image: {str(e)}")
        
        return img
    
    def preprocess_image(self, img: Image.Image) -> Image.Image:
        """Apply preprocessing to image"""
        processed_img = img.copy()
        
        # Resize if too large
        if processed_img.width > self.max_width or processed_img.height > self.max_height:
            processed_img = self._resize_image(processed_img)
        
        # Apply color correction if enabled
        if self.color_correction:
            processed_img = self._apply_color_correction(processed_img)
        
        # Apply enhancement if enabled
        if self.enhancement:
            processed_img = self._apply_enhancement(processed_img)
        
        return processed_img
    
    def _resize_image(self, img: Image.Image) -> Image.Image:
        """Resize image while maintaining aspect ratio"""
        width, height = img.size
        
        # Calculate new dimensions
        if width > self.max_width:
            new_width = self.max_width
            new_height = int(height * (new_width / width))
        elif height > self.max_height:
            new_height = self.max_height
            new_width = int(width * (new_height / height))
        else:
            return img
        
        # Resize using high-quality resampling
        return img.resize((new_width, new_height), Image.LANCZOS)
    
    def _apply_color_correction(self, img: Image.Image) -> Image.Image:
        """Apply automatic color correction"""
        try:
            if img.mode in ['RGB', 'RGBA']:
                # Convert to RGB for processing
                rgb_img = img.convert('RGB') if img.mode == 'RGBA' else img
                
                # Apply auto contrast
                rgb_img = ImageOps.autocontrast(rgb_img, cutoff=0)
                
                # Convert back to original mode
                if img.mode == 'RGBA':
                    result = Image.new('RGBA', rgb_img.size)
                    result.paste(rgb_img, (0, 0))
                    if img.mode == 'RGBA':
                        # Preserve alpha channel
                        alpha = img.split()[3]
                        result.putalpha(alpha)
                    return result
                else:
                    return rgb_img
            else:
                # For grayscale images
                return ImageOps.autocontrast(img, cutoff=0)
                
        except Exception as e:
            self.logger.warning(f"Color correction failed: {str(e)}")
            return img
    
    def _apply_enhancement(self, img: Image.Image) -> Image.Image:
        """Apply image enhancement"""
        try:
            if img.mode in ['RGB', 'RGBA']:
                # Convert to RGB for processing
                rgb_img = img.convert('RGB') if img.mode == 'RGBA' else img
                
                # Create enhancer objects
                color_enhancer = ImageEnhance.Color(rgb_img)
                contrast_enhancer = ImageEnhance.Contrast(rgb_img)
                sharpness_enhancer = ImageEnhance.Sharpness(rgb_img)
                
                # Apply enhancements
                rgb_img = color_enhancer.enhance(1.2)  # 20% color enhancement
                rgb_img = contrast_enhancer.enhance(1.1)  # 10% contrast enhancement
                rgb_img = sharpness_enhancer.enhance(1.1)  # 10% sharpness enhancement
                
                # Convert back to original mode
                if img.mode == 'RGBA':
                    result = Image.new('RGBA', rgb_img.size)
                    result.paste(rgb_img, (0, 0))
                    # Preserve alpha channel
                    alpha = img.split()[3]
                    result.putalpha(alpha)
                    return result
                else:
                    return rgb_img
            else:
                # For grayscale images
                enhancer = ImageEnhance.Contrast(img)
                return enhancer.enhance(1.2)
                
        except Exception as e:
            self.logger.warning(f"Image enhancement failed: {str(e)}")
            return img
    
    def extract_spectral_data(self, img: Image.Image, metadata: ImageMetadata) -> Dict[str, Any]:
        """Extract spectral data from image"""
        spectral_data = {
            'image_info': {
                'width': img.width,
                'height': img.height,
                'mode': img.mode,
                'format': metadata.file_format
            },
            'color_analysis': {},
            'spatial_analysis': {},
            'intensity_analysis': {},
            'spectral_signature': {},
            'quality_metrics': {}
        }
        
        try:
            # Convert to numpy array for analysis
            np_img = np.array(img)
            
            # Color analysis
            spectral_data['color_analysis'] = self._analyze_colors(np_img, img.mode)
            
            # Spatial analysis
            spectral_data['spatial_analysis'] = self._analyze_spatial(np_img)
            
            # Intensity analysis
            spectral_data['intensity_analysis'] = self._analyze_intensity(np_img)
            
            # Extract spectral signature (for hyperspectral images)
            spectral_data['spectral_signature'] = self._extract_spectral_signature(np_img, img.mode)
            
            # Quality metrics
            spectral_data['quality_metrics'] = self.assess_image_quality(np_img, metadata)
            
        except Exception as e:
            self.logger.warning(f"Spectral data extraction failed: {str(e)}")
        
        return spectral_data
    
    def _analyze_colors(self, np_img: np.ndarray, mode: str) -> Dict[str, Any]:
        """Analyze color distribution in image"""
        color_analysis = {}
        
        try:
            if mode in ['RGB', 'RGBA']:
                # Extract RGB channels
                if np_img.ndim == 3:
                    r, g, b = np_img[:, :, 0], np_img[:, :, 1], np_img[:, :, 2]
                elif np_img.ndim == 4:  # RGBA
                    r, g, b = np_img[:, :, 0], np_img[:, :, 1], np_img[:, :, 2]
                else:
                    return color_analysis
                
                # Calculate color statistics
                color_analysis['red'] = {
                    'mean': float(np.mean(r)),
                    'std': float(np.std(r)),
                    'min': int(np.min(r)),
                    'max': int(np.max(r)),
                    'median': float(np.median(r))
                }
                
                color_analysis['green'] = {
                    'mean': float(np.mean(g)),
                    'std': float(np.std(g)),
                    'min': int(np.min(g)),
                    'max': int(np.max(g)),
                    'median': float(np.median(g))
                }
                
                color_analysis['blue'] = {
                    'mean': float(np.mean(b)),
                    'std': float(np.std(b)),
                    'min': int(np.min(b)),
                    'max': int(np.max(b)),
                    'median': float(np.median(b))
                }
                
                # Calculate color ratios
                total_pixels = r.size
                color_analysis['color_ratios'] = {
                    'red_percentage': float(np.sum(r > 200) / total_pixels * 100),
                    'green_percentage': float(np.sum(g > 200) / total_pixels * 100),
                    'blue_percentage': float(np.sum(b > 200) / total_pixels * 100),
                    'dark_percentage': float(np.sum((r < 50) & (g < 50) & (b < 50)) / total_pixels * 100),
                    'light_percentage': float(np.sum((r > 200) & (g > 200) & (b > 200)) / total_pixels * 100)
                }
                
                # Calculate color temperature (approximate)
                color_analysis['color_temperature'] = self._calculate_color_temperature(r, g, b)
                
                # Calculate color histogram
                color_analysis['histogram'] = self._calculate_color_histogram(np_img)
                
            elif mode == 'L':  # Grayscale
                color_analysis['grayscale'] = {
                    'mean': float(np.mean(np_img)),
                    'std': float(np.std(np_img)),
                    'min': int(np.min(np_img)),
                    'max': int(np.max(np_img)),
                    'median': float(np.median(np_img))
                }
                
                # Calculate grayscale histogram
                color_analysis['histogram'] = self._calculate_grayscale_histogram(np_img)
                
        except Exception as e:
            self.logger.warning(f"Color analysis failed: {str(e)}")
        
        return color_analysis
    
    def _calculate_color_temperature(self, r: np.ndarray, g: np.ndarray, b: np.ndarray) -> float:
        """Calculate approximate color temperature from RGB values"""
        try:
            # Simple approximation based on red/blue ratio
            r_mean = np.mean(r[r > 0]) if np.any(r > 0) else 1
            b_mean = np.mean(b[b > 0]) if np.any(b > 0) else 1
            
            # Avoid division by zero
            if b_mean == 0:
                b_mean = 1
            
            # Color temperature approximation (in Kelvin)
            # This is a very rough estimate - real color temperature requires proper calibration
            ratio = r_mean / b_mean
            
            # Simple mapping from ratio to temperature
            if ratio < 0.5:
                temp = 2000 + (ratio * 15000)
            elif ratio < 1.0:
                temp = 5000 + ((ratio - 0.5) * 10000)
            elif ratio < 2.0:
                temp = 10000 + ((ratio - 1.0) * 5000)
            else:
                temp = 15000 + ((ratio - 2.0) * 2500)
            
            return round(temp, 0)
            
        except Exception:
            return 0.0
    
    def _calculate_color_histogram(self, np_img: np.ndarray) -> Dict[str, List[int]]:
        """Calculate color histogram for RGB image"""
        try:
            if np_img.ndim == 4:  # RGBA
                np_img = np_img[:, :, :3]  # Remove alpha channel
            
            # Calculate histograms for each channel
            hist_r = np.histogram(np_img[:, :, 0], bins=256, range=(0, 256))[0].tolist()
            hist_g = np.histogram(np_img[:, :, 1], bins=256, range=(0, 256))[0].tolist()
            hist_b = np.histogram(np_img[:, :, 2], bins=256, range=(0, 256))[0].tolist()
            
            return {
                'red': hist_r,
                'green': hist_g,
                'blue': hist_b,
                'bins': 256,
                'range': [0, 256]
            }
            
        except Exception:
            return {}
    
    def _calculate_grayscale_histogram(self, np_img: np.ndarray) -> Dict[str, List[int]]:
        """Calculate histogram for grayscale image"""
        try:
            hist = np.histogram(np_img, bins=256, range=(0, 256))[0].tolist()
            
            return {
                'intensity': hist,
                'bins': 256,
                'range': [0, 256]
            }
            
        except Exception:
            return {}
    
    def _analyze_spatial(self, np_img: np.ndarray) -> Dict[str, Any]:
        """Analyze spatial characteristics of image"""
        spatial_analysis = {}
        
        try:
            if np_img.ndim == 3:
                # Convert to grayscale for spatial analysis
                if np_img.shape[2] == 4:  # RGBA
                    gray = np.mean(np_img[:, :, :3], axis=2)
                else:  # RGB
                    gray = np.mean(np_img, axis=2)
            elif np_img.ndim == 2:
                gray = np_img
            else:
                return spatial_analysis
            
            # Calculate spatial statistics
            spatial_analysis['dimensions'] = {
                'width': gray.shape[1],
                'height': gray.shape[0],
                'aspect_ratio': float(gray.shape[1] / gray.shape[0])
            }
            
            # Calculate texture features
            spatial_analysis['texture'] = self._calculate_texture_features(gray)
            
            # Calculate edge detection
            spatial_analysis['edges'] = self._detect_edges(gray)
            
            # Calculate spatial frequency
            spatial_analysis['spatial_frequency'] = self._calculate_spatial_frequency(gray)
            
        except Exception as e:
            self.logger.warning(f"Spatial analysis failed: {str(e)}")
        
        return spatial_analysis
    
    def _calculate_texture_features(self, gray: np.ndarray) -> Dict[str, float]:
        """Calculate texture features using simple statistics"""
        features = {}
        
        try:
            # Calculate local variance (texture energy)
            from scipy import ndimage
            local_mean = ndimage.uniform_filter(gray, size=3)
            local_var = ndimage.uniform_filter(gray**2, size=3) - local_mean**2
            features['energy'] = float(np.mean(local_var))
            
            # Calculate entropy
            hist = np.histogram(gray, bins=256, range=(0, 256))[0]
            hist = hist[hist > 0]  # Remove zero bins
            prob = hist / hist.sum()
            features['entropy'] = float(-np.sum(prob * np.log2(prob)))
            
            # Calculate contrast
            features['contrast'] = float(np.std(gray))
            
            # Calculate homogeneity
            features['homogeneity'] = float(1.0 / (1.0 + np.var(gray)))
            
        except Exception:
            pass
        
        return features
    
    def _detect_edges(self, gray: np.ndarray) -> Dict[str, Any]:
        """Detect edges in image using Sobel operator"""
        edge_data = {}
        
        try:
            from scipy import ndimage
            
            # Apply Sobel operator
            sobel_x = ndimage.sobel(gray, axis=0)
            sobel_y = ndimage.sobel(gray, axis=1)
            sobel_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
            
            # Calculate edge statistics
            edge_data['total_edges'] = int(np.sum(sobel_magnitude > 50))
            edge_data['edge_density'] = float(edge_data['total_edges'] / gray.size)
            edge_data['mean_edge_strength'] = float(np.mean(sobel_magnitude))
            edge_data['max_edge_strength'] = float(np.max(sobel_magnitude))
            
            # Edge direction histogram
            edge_angles = np.arctan2(sobel_y, sobel_x)
            edge_angles = np.degrees(edge_angles) + 180
            hist, bins = np.histogram(edge_angles, bins=36, range=(0, 360))
            edge_data['direction_histogram'] = {
                'counts': hist.tolist(),
                'bins': bins.tolist()
            }
            
        except Exception:
            pass
        
        return edge_data
    
    def _calculate_spatial_frequency(self, gray: np.ndarray) -> Dict[str, float]:
        """Calculate spatial frequency content using FFT"""
        freq_data = {}
        
        try:
            # Apply FFT
            fft_result = np.fft.fft2(gray)
            fft_shift = np.fft.fftshift(fft_result)
            magnitude_spectrum = np.abs(fft_shift)
            
            # Calculate radial frequency distribution
            center = np.array(magnitude_spectrum.shape) // 2
            y, x = np.indices(magnitude_spectrum.shape)
            r = np.sqrt((x - center[1])**2 + (y - center[0])**2)
            
            # Create radial bins
            max_r = r.max()
            bins = np.linspace(0, max_r, 10)
            radial_profile = np.histogram(r, bins=bins, weights=magnitude_spectrum)[0]
            
            freq_data['radial_profile'] = radial_profile.tolist()
            freq_data['total_energy'] = float(np.sum(magnitude_spectrum))
            freq_data['high_frequency_energy'] = float(np.sum(magnitude_spectrum[r > max_r/2]))
            freq_data['low_frequency_energy'] = float(np.sum(magnitude_spectrum[r <= max_r/2]))
            freq_data['frequency_ratio'] = float(freq_data['high_frequency_energy'] / freq_data['total_energy']) if freq_data['total_energy'] > 0 else 0.0
            
        except Exception:
            pass
        
        return freq_data
    
    def _analyze_intensity(self, np_img: np.ndarray) -> Dict[str, Any]:
        """Analyze intensity distribution in image"""
        intensity_analysis = {}
        
        try:
            if np_img.ndim == 3:
                # Convert to grayscale
                if np_img.shape[2] == 4:  # RGBA
                    gray = np.mean(np_img[:, :, :3], axis=2)
                else:  # RGB
                    gray = np.mean(np_img, axis=2)
            elif np_img.ndim == 2:
                gray = np_img
            else:
                return intensity_analysis
            
            # Calculate intensity statistics
            intensity_analysis['statistics'] = {
                'mean': float(np.mean(gray)),
                'std': float(np.std(gray)),
                'min': int(np.min(gray)),
                'max': int(np.max(gray)),
                'median': float(np.median(gray)),
                'range': int(np.max(gray) - np.min(gray))
            }
            
            # Calculate intensity histogram
            hist, bins = np.histogram(gray, bins=256, range=(0, 256))
            intensity_analysis['histogram'] = {
                'counts': hist.tolist(),
                'bins': bins.tolist()
            }
            
            # Calculate cumulative distribution function
            cdf = np.cumsum(hist)
            cdf = cdf / cdf[-1] if cdf[-1] > 0 else cdf
            intensity_analysis['cdf'] = cdf.tolist()
            
            # Calculate intensity percentiles
            percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
            percentile_values = np.percentile(gray, percentiles)
            intensity_analysis['percentiles'] = {
                str(p): float(v) for p, v in zip(percentiles, percentile_values)
            }
            
            # Calculate contrast metrics
            intensity_analysis['contrast'] = self._calculate_contrast_metrics(gray)
            
        except Exception as e:
            self.logger.warning(f"Intensity analysis failed: {str(e)}")
        
        return intensity_analysis
    
    def _calculate_contrast_metrics(self, gray: np.ndarray) -> Dict[str, float]:
        """Calculate various contrast metrics"""
        metrics = {}
        
        try:
            # Standard deviation as contrast measure
            metrics['std_contrast'] = float(np.std(gray))
            
            # Range as contrast measure
            metrics['range_contrast'] = float(np.max(gray) - np.min(gray))
            
            # Michelson contrast (for images with mean > 0)
            mean_val = np.mean(gray)
            if mean_val > 0:
                max_val = np.max(gray)
                min_val = np.min(gray)
                metrics['michelson_contrast'] = float((max_val - min_val) / (max_val + min_val))
            else:
                metrics['michelson_contrast'] = 0.0
            
            # RMS contrast
            metrics['rms_contrast'] = float(np.sqrt(np.mean((gray - mean_val)**2)))
            
            # Local contrast (using 3x3 windows)
            from scipy import ndimage
            local_mean = ndimage.uniform_filter(gray, size=3)
            local_std = ndimage.uniform_filter((gray - local_mean)**2, size=3)
            local_std = np.sqrt(local_std)
            metrics['local_contrast'] = float(np.mean(local_std))
            
        except Exception:
            pass
        
        return metrics
    
    def _extract_spectral_signature(self, np_img: np.ndarray, mode: str) -> Dict[str, Any]:
        """Extract spectral signature from image (for hyperspectral images)"""
        signature = {}
        
        try:
            # For now, we'll extract basic spectral information
            # In a real hyperspectral image, this would be more sophisticated
            
            if np_img.ndim == 3:
                # Assume RGB or RGBA image
                if np_img.shape[2] == 4:  # RGBA
                    r, g, b = np_img[:, :, 0], np_img[:, :, 1], np_img[:, :, 2]
                else:  # RGB
                    r, g, b = np_img[:, :, 0], np_img[:, :, 1], np_img[:, :, 2]
                
                # Calculate average spectral response
                signature['average_spectrum'] = {
                    'red': float(np.mean(r)),
                    'green': float(np.mean(g)),
                    'blue': float(np.mean(b))
                }
                
                # Calculate spectral ratios
                signature['spectral_ratios'] = {
                    'red_green': float(np.mean(r) / (np.mean(g) + 1e-10)),
                    'green_blue': float(np.mean(g) / (np.mean(b) + 1e-10)),
                    'red_blue': float(np.mean(r) / (np.mean(b) + 1e-10))
                }
                
                # Calculate spectral centroid (weighted average wavelength)
                # Approximate wavelengths: Red ~700nm, Green ~550nm, Blue ~450nm
                wavelengths = np.array([700.0, 550.0, 450.0])
                intensities = np.array([np.mean(r), np.mean(g), np.mean(b)])
                total_intensity = np.sum(intensities)
                if total_intensity > 0:
                    signature['spectral_centroid'] = float(np.sum(wavelengths * intensities) / total_intensity)
                else:
                    signature['spectral_centroid'] = 0.0
                
                # Calculate spectral purity
                signature['spectral_purity'] = float(np.max(intensities) / total_intensity) if total_intensity > 0 else 0.0
                
            elif np_img.ndim == 2:
                # Grayscale image - treat as single band
                signature['average_intensity'] = float(np.mean(np_img))
                signature['spectral_centroid'] = 550.0  # Approximate visible light center
                signature['spectral_purity'] = 1.0
                
        except Exception as e:
            self.logger.warning(f"Spectral signature extraction failed: {str(e)}")
        
        return signature
    
    def assess_image_quality(self, np_img: np.ndarray, metadata: ImageMetadata) -> Dict[str, float]:
        """Assess the quality of image data for spectral analysis"""
        quality_metrics = {}
        
        try:
            if np_img.ndim == 3:
                # Convert to grayscale for some metrics
                if np_img.shape[2] == 4:  # RGBA
                    gray = np.mean(np_img[:, :, :3], axis=2)
                else:  # RGB
                    gray = np.mean(np_img, axis=2)
            elif np_img.ndim == 2:
                gray = np_img
            else:
                gray = np_img
            
            # Signal-to-noise ratio estimate
            signal_power = np.mean(gray ** 2)
            noise_power = np.mean((gray - np.mean(gray)) ** 2)
            quality_metrics['snr_estimate'] = float(10 * np.log10(signal_power / (noise_power + 1e-10)))
            
            # Dynamic range
            max_val = np.max(gray)
            min_val = np.min(gray[gray > 0]) if np.any(gray > 0) else 1e-10
            quality_metrics['dynamic_range'] = float(20 * np.log10(max_val / min_val))
            
            # Contrast assessment
            quality_metrics['contrast'] = float(np.std(gray))
            
            # Sharpness assessment (using Laplacian variance)
            from scipy import ndimage
            laplacian = ndimage.laplace(gray)
            quality_metrics['sharpness'] = float(np.var(laplacian))
            
            # Noise level (using median absolute deviation)
            median_val = np.median(gray)
            mad = np.median(np.abs(gray - median_val))
            quality_metrics['noise_level'] = float(mad)
            
            # Resolution quality (based on image dimensions)
            width, height = gray.shape[1] if len(gray.shape) > 1 else 1, gray.shape[0]
            quality_metrics['resolution_quality'] = min(min(width, height) / 1024.0, 1.0)
            
            # Format quality (lossless formats get higher score)
            format_quality = 1.0 if self.supported_formats.get(metadata.file_format, ImageFormat("", "", "")).lossless else 0.7
            quality_metrics['format_quality'] = format_quality
            
            # Bit depth quality
            quality_metrics['bit_depth_quality'] = min(metadata.bits_per_sample / 16.0, 1.0)
            
            # Overall quality score (0-100)
            weights = {
                'snr_estimate': 0.25,
                'dynamic_range': 0.15,
                'contrast': 0.15,
                'sharpness': 0.15,
                'noise_level': -0.10,  # Negative weight (lower is better)
                'resolution_quality': 0.10,
                'format_quality': 0.05,
                'bit_depth_quality': 0.05
            }
            
            # Normalize metrics to 0-1 range where appropriate
            normalized_metrics = {}
            for metric, weight in weights.items():
                if metric in quality_metrics:
                    if metric == 'noise_level':
                        # For negative weights, invert the metric
                        normalized_metrics[metric] = 1.0 - min(quality_metrics[metric] / 255.0, 1.0)
                    elif metric == 'snr_estimate':
                        normalized_metrics[metric] = min(quality_metrics[metric] / 100.0, 1.0)
                    elif metric == 'dynamic_range':
                        normalized_metrics[metric] = min(quality_metrics[metric] / 120.0, 1.0)
                    elif metric == 'contrast':
                        normalized_metrics[metric] = min(quality_metrics[metric] / 255.0, 1.0)
                    elif metric == 'sharpness':
                        normalized_metrics[metric] = min(quality_metrics[metric] / 10000.0, 1.0)
                    else:
                        normalized_metrics[metric] = quality_metrics[metric]
            
            # Calculate weighted sum
            total_weight = sum(abs(w) for w in weights.values())
            overall_quality = sum(
                normalized_metrics.get(metric, 0) * abs(weight) for metric, weight in weights.items()
            ) / total_weight * 100
            
            quality_metrics['overall_quality'] = round(overall_quality, 2)
            
        except Exception as e:
            self.logger.warning(f"Image quality assessment failed: {str(e)}")
        
        return quality_metrics
    
    def detect_spectral_content(self, spectral_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect and analyze spectral content in image data"""
        content_analysis = {
            'has_spectral_content': False,
            'content_type': 'unknown',
            'spectral_features': {},
            'potential_issues': [],
            'recommendations': []
        }
        
        try:
            color_analysis = spectral_data.get('color_analysis', {})
            spectral_signature = spectral_data.get('spectral_signature', {})
            
            # Check if we have meaningful spectral content
            if color_analysis and spectral_signature:
                content_analysis['has_spectral_content'] = True
            
            # Determine content type
            if color_analysis:
                # Check for grayscale content
                if 'grayscale' in color_analysis:
                    content_analysis['content_type'] = 'grayscale'
                    content_analysis['spectral_features']['intensity_range'] = {
                        'min': color_analysis['grayscale']['min'],
                        'max': color_analysis['grayscale']['max'],
                        'mean': color_analysis['grayscale']['mean']
                    }
                elif 'color_ratios' in color_analysis:
                    content_analysis['content_type'] = 'color'
                    content_analysis['spectral_features']['color_distribution'] = color_analysis['color_ratios']
                    content_analysis['spectral_features']['color_temperature'] = color_analysis.get('color_temperature', 0)
                
                # Check for spectral signature
                if spectral_signature:
                    content_analysis['spectral_features']['spectral_centroid'] = spectral_signature.get('spectral_centroid', 0)
                    content_analysis['spectral_features']['spectral_purity'] = spectral_signature.get('spectral_purity', 0)
                    content_analysis['spectral_features']['spectral_ratios'] = spectral_signature.get('spectral_ratios', {})
            
            # Detect potential issues
            if content_analysis['content_type'] == 'unknown':
                content_analysis['potential_issues'].append("Could not determine image content type")
            
            if spectral_signature.get('spectral_purity', 0) < 0.1:
                content_analysis['potential_issues'].append("Low spectral purity may indicate noise or mixed content")
            
            if color_analysis.get('color_temperature', 0) < 2000 or color_analysis.get('color_temperature', 0) > 15000:
                content_analysis['potential_issues'].append("Unusual color temperature may indicate calibration issues")
            
            # Generate recommendations
            if content_analysis['content_type'] == 'grayscale':
                content_analysis['recommendations'].append("Grayscale image detected - ensure proper calibration for spectral analysis")
            elif content_analysis['content_type'] == 'color':
                content_analysis['recommendations'].append("Color image detected - consider converting to spectral data for analysis")
            
            if spectral_signature.get('spectral_purity', 0) < 0.5:
                content_analysis['recommendations'].append("Low spectral purity - consider using a spectrometer with better wavelength separation")
            
            # Add general recommendations
            content_analysis['recommendations'].extend([
                "Ensure proper lighting conditions during image capture",
                "Use consistent camera settings for comparable results",
                "Consider using lossless image formats for archival purposes"
            ])
            
        except Exception as e:
            self.logger.warning(f"Spectral content analysis failed: {str(e)}")
        
        return content_analysis
    
    def convert_image_format(self, input_path: str, output_format: str, output_path: Optional[str] = None, quality: Optional[int] = None) -> Tuple[bool, str, Optional[str]]:
        """Convert image file to different format"""
        try:
            input_path = Path(input_path)
            if not input_path.exists():
                return False, f"Input file not found: {input_path}", None
            
            # Determine output path
            if output_path is None:
                output_path = Path(self.output_dir) / f"{input_path.stem}.{output_format}"
            else:
                output_path = Path(output_path)
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if format is supported
            if output_format not in self.supported_formats:
                return False, f"Unsupported output format: {output_format}", None
            
            # Load image
            success, message, img = self.load_image_file(input_path)
            if not success:
                return False, message, None
            
            # Preprocess image
            processed_img = self.preprocess_image(img)
            
            # Save in new format
            save_kwargs = {}
            if output_format in ['jpg', 'jpeg']:
                save_kwargs['quality'] = quality or self.default_quality
                save_kwargs['optimize'] = True
            elif output_format == 'png':
                save_kwargs['compress_level'] = 6  # 0-9, 6 is default
            elif output_format == 'tiff':
                save_kwargs['compression'] = 'tiff_lzw' if processed_img.mode == 'RGB' else None
            
            # Preserve EXIF data if requested
            if self.exif_preservation and self.metadata_extraction:
                exif_data = self._extract_exif_data(img)
                if exif_data:
                    # For PNG, we can save some metadata as text
                    if output_format == 'png':
                        info = processed_img.info.copy() if hasattr(processed_img, 'info') else {}
                        info['exif'] = json.dumps(exif_data)
                        save_kwargs['pnginfo'] = info
            
            processed_img.save(output_path, format=output_format.upper(), **save_kwargs)
            
            if not output_path.exists():
                return False, "Output file was not created", None
            
            return True, f"Successfully converted to {output_format}", str(output_path)
            
        except Exception as e:
            return False, f"Conversion error: {str(e)}", None
    
    def extract_spectral_data_from_file(self, file_path: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Extract spectral data from image file"""
        try:
            # Validate file
            is_valid, message, metadata = self.validate_image_file(file_path)
            if not is_valid:
                return False, message, None
            
            # Load image
            success, message, img = self.load_image_file(file_path)
            if not success:
                return False, message, None
            
            # Preprocess image
            processed_img = self.preprocess_image(img)
            
            # Extract spectral data
            spectral_data = self.extract_spectral_data(processed_img, metadata)
            
            # Detect spectral content
            content_analysis = self.detect_spectral_content(spectral_data)
            
            # Assess image quality
            np_img = np.array(processed_img)
            quality_metrics = self.assess_image_quality(np_img, metadata)
            
            # Create result
            result = {
                'file_info': {
                    'file_path': str(file_path),
                    'file_name': Path(file_path).name,
                    'file_format': metadata.file_format,
                    'width': processed_img.width,
                    'height': processed_img.height,
                    'mode': processed_img.mode,
                    'channels': len(processed_img.mode) if processed_img.mode in ['RGB', 'RGBA', 'CMYK'] else 1,
                    'file_size': metadata.file_size
                },
                'spectral_data': spectral_data,
                'content_analysis': content_analysis,
                'quality_metrics': quality_metrics,
                'metadata': {
                    'image_metadata': metadata.metadata,
                    'exif_data': metadata.exif_data
                }
            }
            
            return True, "Spectral data extraction completed", result
            
        except Exception as e:
            return False, f"Spectral data extraction failed: {str(e)}", None
    
    def process_batch(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process multiple image files in batch"""
        results = {
            'total_files': len(file_paths),
            'successful': 0,
            'failed': 0,
            'results': {},
            'summary': {}
        }
        
        for file_path in file_paths:
            try:
                success, message, spectral_data = self.extract_spectral_data_from_file(file_path)
                
                if success:
                    results['successful'] += 1
                    results['results'][file_path] = spectral_data
                else:
                    results['failed'] += 1
                    results['results'][file_path] = {'error': message}
                    
            except Exception as e:
                results['failed'] += 1
                results['results'][file_path] = {'error': str(e)}
        
        # Generate summary statistics
        if results['successful'] > 0:
            successful_results = [
                r for r in results['results'].values() 
                if isinstance(r, dict) and 'spectral_data' in r
            ]
            
            if successful_results:
                avg_quality = np.mean([
                    r['quality_metrics'].get('overall_quality', 0) 
                    for r in successful_results
                ])
                results['summary']['average_quality'] = float(avg_quality)
                
                # Most common format
                formats = [r['file_info']['file_format'] for r in successful_results]
                format_counts = {fmt: formats.count(fmt) for fmt in set(formats)}
                most_common_format = max(format_counts, key=format_counts.get)
                results['summary']['most_common_format'] = most_common_format
                
                # Most common content type
                content_types = [r['content_analysis']['content_type'] for r in successful_results]
                content_counts = {ct: content_types.count(ct) for ct in set(content_types)}
                most_common_content = max(content_counts, key=content_counts.get)
                results['summary']['most_common_content_type'] = most_common_content
        
        return results
    
    def create_image_report(self, spectral_data: Dict[str, Any], output_path: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Create a detailed report of image analysis"""
        try:
            if output_path is None:
                output_path = Path(self.output_dir) / f"report_{Path(spectral_data['file_info']['file_name']).stem}.json"
            else:
                output_path = Path(output_path)
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create comprehensive report
            report = {
                'analysis_timestamp': datetime.now().isoformat(),
                'file_information': spectral_data['file_info'],
                'spectral_data': spectral_data['spectral_data'],
                'content_analysis': spectral_data['content_analysis'],
                'quality_assessment': spectral_data['quality_metrics'],
                'metadata': spectral_data.get('metadata', {}),
                'recommendations': self._generate_recommendations(spectral_data)
            }
            
            # Save report
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            return True, f"Report saved to {output_path}", str(output_path)
            
        except Exception as e:
            return False, f"Failed to create report: {str(e)}", None
    
    def _generate_recommendations(self, spectral_data: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on image analysis"""
        recommendations = []
        quality_metrics = spectral_data.get('quality_metrics', {})
        content_analysis = spectral_data.get('content_analysis', {})
        spectral_data_info = spectral_data.get('spectral_data', {})
        
        # Quality-based recommendations
        if quality_metrics.get('overall_quality', 100) < 70:
            recommendations.append(
                "Overall image quality is low. Consider re-capturing with better equipment or settings."
            )
        
        if quality_metrics.get('snr_estimate', 100) < 20:
            recommendations.append(
                "Low signal-to-noise ratio. Try to reduce noise during image capture."
            )
        
        if quality_metrics.get('sharpness', 0) < 100:
            recommendations.append(
                "Low image sharpness. Ensure proper focus and avoid motion blur."
            )
        
        if quality_metrics.get('contrast', 0) < 50:
            recommendations.append(
                "Low contrast. Consider adjusting lighting or camera settings for better contrast."
            )
        
        if quality_metrics.get('resolution_quality', 1.0) < 0.5:
            recommendations.append(
                f"Low resolution ({spectral_data['file_info']['width']}x{spectral_data['file_info']['height']}). Consider using higher resolution images."
            )
        
        # Content-based recommendations
        if not content_analysis.get('has_spectral_content', True):
            recommendations.append(
                "No clear spectral content detected. Verify that the image contains valid spectral data."
            )
        
        if content_analysis.get('content_type') == 'grayscale':
            recommendations.append(
                "Grayscale image detected. For spectral analysis, consider using color images or direct spectral data."
            )
        
        if content_analysis.get('spectral_features', {}).get('spectral_purity', 0) < 0.3:
            recommendations.append(
                "Low spectral purity. The image may contain mixed spectral information or noise."
            )
        
        # Format-based recommendations
        file_format = spectral_data['file_info']['file_format']
        if not self.supported_formats.get(file_format, ImageFormat("", "", "")).lossless:
            recommendations.append(
                f"Lossy format ({file_format}) detected. Consider using lossless formats (PNG, TIFF) for archival purposes."
            )
        
        # Add general recommendations
        recommendations.extend([
            "Ensure proper calibration of your imaging device before capture.",
            "Use consistent lighting conditions for comparable results.",
            "Consider using raw image formats for maximum data preservation.",
            "Document camera settings and conditions for each image."
        ])
        
        return recommendations
    
    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute the agent's primary function"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting ImageProcessorAgent execution")
            
            action = context.get('action', 'extract_spectral_data')
            
            if action == 'extract_spectral_data':
                file_path = context.get('file_path')
                if not file_path:
                    return self._create_error_output("file_path is required")
                
                success, message, spectral_data = self.extract_spectral_data_from_file(file_path)
                
                if success:
                    output = {
                        "status": "completed",
                        "message": message,
                        "file_path": file_path,
                        "spectral_data": spectral_data
                    }
                else:
                    output = {
                        "status": "failed",
                        "message": message,
                        "file_path": file_path
                    }
                
            elif action == 'process_batch':
                file_paths = context.get('file_paths', [])
                if not file_paths:
                    return self._create_error_output("file_paths is required")
                
                results = self.process_batch(file_paths)
                output = {
                    "status": "completed",
                    "message": f"Processed {results['total_files']} files",
                    "results": results
                }
                
            elif action == 'validate_image':
                file_path = context.get('file_path')
                if not file_path:
                    return self._create_error_output("file_path is required")
                
                is_valid, message, metadata = self.validate_image_file(file_path)
                output = {
                    "status": "completed",
                    "valid": is_valid,
                    "message": message,
                    "metadata": metadata.dict() if metadata else None
                }
                
            elif action == 'convert_format':
                input_path = context.get('input_path')
                output_format = context.get('output_format')
                output_path = context.get('output_path')
                quality = context.get('quality')
                
                if not input_path or not output_format:
                    return self._create_error_output("input_path and output_format are required")
                
                success, message, converted_path = self.convert_image_format(
                    input_path, output_format, output_path, quality
                )
                output = {
                    "status": "completed" if success else "failed",
                    "message": message,
                    "output_path": converted_path
                }
                
            elif action == 'create_report':
                spectral_data = context.get('spectral_data')
                output_path = context.get('output_path')
                
                if not spectral_data:
                    return self._create_error_output("spectral_data is required")
                
                success, message, report_path = self.create_image_report(spectral_data, output_path)
                output = {
                    "status": "completed" if success else "failed",
                    "message": message,
                    "report_path": report_path
                }
                
            elif action == 'analyze_quality':
                file_path = context.get('file_path')
                if not file_path:
                    return self._create_error_output("file_path is required")
                
                # Load and preprocess
                success, message, img = self.load_image_file(file_path)
                if not success:
                    return self._create_error_output(message)
                
                metadata = self.validate_image_file(file_path)[2]
                np_img = np.array(img)
                
                quality_metrics = self.assess_image_quality(np_img, metadata)
                output = {
                    "status": "completed",
                    "file_path": file_path,
                    "quality_metrics": quality_metrics
                }
                
            elif action == 'detect_spectral_content':
                file_path = context.get('file_path')
                if not file_path:
                    return self._create_error_output("file_path is required")
                
                # Extract spectral data
                success, message, spectral_data = self.extract_spectral_data_from_file(file_path)
                if not success:
                    return self._create_error_output(message)
                
                # Perform content analysis
                content_analysis = self.detect_spectral_content(spectral_data['spectral_data'])
                output = {
                    "status": "completed",
                    "file_path": file_path,
                    "content_analysis": content_analysis
                }
                
            elif action == 'get_supported_formats':
                output = {
                    "status": "completed",
                    "supported_formats": {
                        fmt: {
                            "name": info.name,
                            "extension": info.extension,
                            "mime_type": info.mime_type,
                            "lossless": info.lossless,
                            "supports_metadata": info.supports_metadata,
                            "supports_transparency": info.supports_transparency,
                            "color_depth": info.color_depth
                        }
                        for fmt, info in self.supported_formats.items()
                    }
                }
                
            else:
                output = {"status": "error", "message": f"Unknown action: {action}"}
            
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(output)
            
        except Exception as e:
            return self._handle_error(e)
    
    def validate(self) -> List[AgentError]:
        """Validate agent configuration and state"""
        errors = super().validate()
        
        # Check required dependencies
        required_deps = ['numpy', 'pandas']
        for dep in required_deps:
            try:
                __import__(dep)
            except ImportError:
                errors.append(AgentError(
                    agent_name=self.name,
                    error_type="dependency_error",
                    message=f"Missing required dependency: {dep}",
                    severity=ErrorSeverity.HIGH,
                    context={"dependency": dep},
                    solution=f"Install with: pip install {dep}"
                ))
        
        # Check optional dependencies
        optional_deps = ['Pillow', 'opencv-python', 'scikit-image']
        for dep in optional_deps:
            try:
                __import__(dep)
            except ImportError:
                errors.append(AgentError(
                    agent_name=self.name,
                    error_type="dependency_warning",
                    message=f"Missing optional dependency: {dep} (reduced functionality)",
                    severity=ErrorSeverity.MEDIUM,
                    context={"dependency": dep},
                    solution=f"Install with: pip install {dep} for full functionality"
                ))
        
        # Check output directory
        try:
            output_dir = Path(self.output_dir)
            if not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)
            elif not os.access(output_dir, os.W_OK):
                errors.append(AgentError(
                    agent_name=self.name,
                    error_type="permission_error",
                    message=f"Output directory is not writable: {self.output_dir}",
                    severity=ErrorSeverity.MEDIUM,
                    context={"output_dir": self.output_dir},
                    solution=f"Ensure directory {self.output_dir} exists and is writable"
                ))
        except Exception as e:
            errors.append(AgentError(
                agent_name=self.name,
                error_type="permission_error",
                message=f"Error accessing output directory: {str(e)}",
                severity=ErrorSeverity.MEDIUM,
                context={"output_dir": self.output_dir},
                solution=f"Ensure directory {self.output_dir} exists and is writable"
            ))
        
        return errors


if __name__ == "__main__":
    # Allow direct execution for testing
    agent = ImageProcessorAgent()
    output = agent.initialize()
    print(f"ImageProcessorAgent initialized: {output.status.name}")
