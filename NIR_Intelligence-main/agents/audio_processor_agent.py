#!/usr/bin/env python3
"""
NIR Intelligence Platform - AudioProcessorAgent
Agent for processing audio files containing spectral data (WAV, MP3, FLAC, etc.)
"""

import logging
import os
import wave
import struct
import json
import tempfile
import subprocess
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
from scipy import signal, fft
from scipy.io import wavfile
from .base_agent import BaseAgent, AgentOutput, AgentStatus, ErrorSeverity, AgentError


@dataclass
class AudioFormat:
    """Supported audio format information"""
    name: str
    extension: str
    mime_type: str
    sample_rate_range: Tuple[int, int] = (8000, 192000)
    bits_per_sample_range: Tuple[int, int] = (8, 32)
    channels_range: Tuple[int, int] = (1, 8)
    lossless: bool = True
    supports_metadata: bool = True


@dataclass
class AudioMetadata:
    """Extracted audio file metadata"""
    file_path: str
    file_name: str
    file_size: int
    file_format: str
    duration: float = 0.0
    sample_rate: int = 0
    bits_per_sample: int = 0
    channels: int = 0
    bitrate: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioProcessingResult:
    """Result of audio processing"""
    success: bool
    file_path: str
    processed_data: Optional[np.ndarray] = None
    sample_rate: int = 0
    duration: float = 0.0
    spectral_data: Optional[Dict[str, Any]] = None
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class SpectralAnalysis:
    """Spectral analysis results from audio data"""
    frequencies: np.ndarray
    magnitudes: np.ndarray
    phases: np.ndarray
    dominant_frequencies: List[float] = field(default_factory=list)
    spectral_centroid: float = 0.0
    spectral_bandwidth: float = 0.0
    spectral_rolloff: float = 0.0
    spectral_flatness: float = 0.0
    zero_crossing_rate: float = 0.0
    rms_amplitude: float = 0.0
    peak_amplitude: float = 0.0


class AudioProcessorAgent(BaseAgent):
    """
    Agent for processing audio files containing spectral data
    
    Features:
    - Support for WAV, MP3, FLAC, and other audio formats
    - Audio file validation and metadata extraction
    - Audio preprocessing (normalization, filtering, noise reduction)
    - Spectral analysis using FFT
    - Quality assessment and issue detection
    - Format conversion and standardization
    """
    
    def __init__(self, **kwargs):
        super().__init__(name="AudioProcessorAgent", version="2.0.0", **kwargs)
        self.dependencies = ['numpy', 'scipy', 'pandas', 'librosa', 'pydub']
        self.logger = logging.getLogger(f"Agent.AudioProcessorAgent")
        
        # Configuration
        self.supported_formats = {
            'wav': AudioFormat(
                name="WAV",
                extension=".wav",
                mime_type="audio/wav",
                lossless=True,
                supports_metadata=True
            ),
            'mp3': AudioFormat(
                name="MP3",
                extension=".mp3",
                mime_type="audio/mpeg",
                lossless=False,
                supports_metadata=True
            ),
            'flac': AudioFormat(
                name="FLAC",
                extension=".flac",
                mime_type="audio/flac",
                lossless=True,
                supports_metadata=True
            ),
            'ogg': AudioFormat(
                name="OGG",
                extension=".ogg",
                mime_type="audio/ogg",
                lossless=True,
                supports_metadata=True
            ),
            'aiff': AudioFormat(
                name="AIFF",
                extension=".aiff",
                mime_type="audio/aiff",
                lossless=True,
                supports_metadata=True
            ),
            'wma': AudioFormat(
                name="WMA",
                extension=".wma",
                mime_type="audio/x-ms-wma",
                lossless=False,
                supports_metadata=True
            )
        }
        
        self.output_dir = kwargs.get('output_dir', 'processed_audio')
        self.temp_dir = kwargs.get('temp_dir', tempfile.gettempdir())
        self.ffmpeg_path = kwargs.get('ffmpeg_path', 'ffmpeg')
        self.ffprobe_path = kwargs.get('ffprobe_path', 'ffprobe')
        
        # Processing parameters
        self.default_sample_rate = kwargs.get('default_sample_rate', 44100)
        self.default_bits_per_sample = kwargs.get('default_bits_per_sample', 16)
        self.default_channels = kwargs.get('default_channels', 1)
        self.normalize_audio = kwargs.get('normalize_audio', True)
        self.apply_bandpass = kwargs.get('apply_bandpass', False)
        self.bandpass_range = kwargs.get('bandpass_range', (20, 20000))  # Hz
        self.noise_reduction = kwargs.get('noise_reduction', False)
        
        # Initialize agent-specific attributes
        self._initialize_attributes()
    
    def _initialize_attributes(self):
        """Initialize agent-specific attributes"""
        self.processed_files: Dict[str, AudioProcessingResult] = {}
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
    
    def detect_audio_format(self, file_path: str) -> Optional[str]:
        """Detect the audio format from file extension or content"""
        try:
            file_path = str(file_path).lower()
            
            # Check by file extension first
            for fmt, info in self.supported_formats.items():
                if file_path.endswith(info.extension):
                    return fmt
            
            # If extension not recognized, try to detect from file signature
            with open(file_path, 'rb') as f:
                header = f.read(12)
                
                # WAV signature: "RIFF" followed by "WAVE"
                if header.startswith(b'RIFF') and header[8:12] == b'WAVE':
                    return 'wav'
                
                # MP3 signature: starts with "ID3" or has MP3 frame sync
                if header.startswith(b'ID3') or (header[0] == 0xFF and header[1] >= 0xE0):
                    return 'mp3'
                
                # FLAC signature: "fLaC"
                if header.startswith(b'fLaC'):
                    return 'flac'
                
                # OGG signature: "OggS"
                if header.startswith(b'OggS'):
                    return 'ogg'
                
                # AIFF signature: "FORM" followed by "AIFF"
                if header.startswith(b'FORM') and header[8:12] == b'AIFF':
                    return 'aiff'
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error detecting audio format for {file_path}: {str(e)}")
            return None
    
    def validate_audio_file(self, file_path: str) -> Tuple[bool, str, Optional[AudioMetadata]]:
        """Validate an audio file and extract basic metadata"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return False, f"File not found: {file_path}", None
            
            if file_path.stat().st_size == 0:
                return False, "File is empty", None
            
            # Detect format
            audio_format = self.detect_audio_format(file_path)
            if not audio_format:
                return False, "Unsupported audio format", None
            
            # Extract metadata using ffprobe if available
            metadata = self._extract_metadata_with_ffprobe(file_path)
            if metadata:
                return True, "Valid audio file", metadata
            
            # Fallback to format-specific validation
            if audio_format == 'wav':
                metadata = self._validate_wav_file(file_path)
                if metadata:
                    return True, "Valid WAV file", metadata
            
            # For other formats, try basic validation
            metadata = AudioMetadata(
                file_path=str(file_path),
                file_name=file_path.name,
                file_size=file_path.stat().st_size,
                file_format=audio_format
            )
            
            return True, "Valid audio file (basic validation)", metadata
            
        except Exception as e:
            return False, f"Validation error: {str(e)}", None
    
    def _extract_metadata_with_ffprobe(self, file_path: str) -> Optional[AudioMetadata]:
        """Extract metadata using ffprobe"""
        try:
            import json
            
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return None
            
            data = json.loads(result.stdout)
            
            # Extract stream information
            stream = data.get('streams', [{}])[0]
            format_info = data.get('format', {})
            
            metadata = AudioMetadata(
                file_path=str(file_path),
                file_name=Path(file_path).name,
                file_size=format_info.get('size', 0),
                file_format=format_info.get('format_name', 'unknown'),
                duration=float(format_info.get('duration', 0)),
                sample_rate=int(stream.get('sample_rate', 0)),
                bits_per_sample=int(stream.get('bits_per_sample', 0)),
                channels=int(stream.get('channels', 0)),
                bitrate=int(stream.get('bit_rate', 0)),
                metadata={k: v for k, v in format_info.get('tags', {}).items()}
            )
            
            return metadata
            
        except Exception as e:
            self.logger.debug(f"ffprobe metadata extraction failed: {str(e)}")
            return None
    
    def _validate_wav_file(self, file_path: str) -> Optional[AudioMetadata]:
        """Validate WAV file and extract metadata"""
        try:
            with wave.open(file_path, 'rb') as wav_file:
                n_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                n_frames = wav_file.getnframes()
                
                metadata = AudioMetadata(
                    file_path=str(file_path),
                    file_name=Path(file_path).name,
                    file_size=Path(file_path).stat().st_size,
                    file_format='wav',
                    duration=n_frames / frame_rate,
                    sample_rate=frame_rate,
                    bits_per_sample=sample_width * 8,
                    channels=n_channels,
                    bitrate=frame_rate * n_channels * sample_width * 8
                )
                
                return metadata
                
        except Exception as e:
            self.logger.warning(f"WAV validation failed for {file_path}: {str(e)}")
            return None
    
    def load_audio_file(self, file_path: str, target_sample_rate: Optional[int] = None) -> Tuple[bool, str, Optional[Tuple[np.ndarray, int]]]:
        """Load audio file and return samples and sample rate"""
        try:
            file_path = Path(file_path)
            audio_format = self.detect_audio_format(file_path)
            
            if not audio_format:
                return False, "Unsupported audio format", None
            
            # Use librosa for most formats (handles resampling, etc.)
            try:
                import librosa
                
                target_sr = target_sample_rate or self.default_sample_rate
                
                # Load audio file
                y, sr = librosa.load(file_path, sr=target_sr, mono=True)
                
                # Normalize if requested
                if self.normalize_audio:
                    y = librosa.util.normalize(y)
                
                return True, "Audio loaded successfully", (y, sr)
                
            except ImportError:
                # Fallback to scipy for WAV files
                if audio_format == 'wav':
                    try:
                        sample_rate, data = wavfile.read(file_path)
                        
                        # Convert to mono if stereo
                        if len(data.shape) > 1 and data.shape[1] > 1:
                            data = data.mean(axis=1)
                        
                        # Convert to float32 and normalize
                        if data.dtype != np.float32:
                            data = data.astype(np.float32)
                            if data.dtype in [np.int16, np.int32]:
                                data = data / (2 ** (data.dtype.itemsize * 8 - 1))
                        
                        if self.normalize_audio:
                            max_val = np.max(np.abs(data))
                            if max_val > 0:
                                data = data / max_val
                        
                        # Resample if needed
                        if target_sample_rate and sample_rate != target_sample_rate:
                            data = signal.resample(data, int(len(data) * target_sample_rate / sample_rate))
                            sample_rate = target_sample_rate
                        
                        return True, "Audio loaded successfully", (data, sample_rate)
                        
                    except Exception as e:
                        return False, f"Error loading WAV file: {str(e)}", None
                
                return False, f"Unsupported format without librosa: {audio_format}", None
                
        except Exception as e:
            return False, f"Error loading audio file: {str(e)}", None
    
    def preprocess_audio(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply preprocessing to audio data"""
        processed_data = audio_data.copy()
        
        # Apply bandpass filter if enabled
        if self.apply_bandpass and len(self.bandpass_range) == 2:
            low, high = self.bandpass_range
            nyquist = 0.5 * sample_rate
            low = low / nyquist
            high = high / nyquist
            
            # Design bandpass filter
            b, a = signal.butter(4, [low, high], btype='band')
            processed_data = signal.filtfilt(b, a, processed_data)
        
        # Apply noise reduction if enabled
        if self.noise_reduction:
            processed_data = self._apply_noise_reduction(processed_data, sample_rate)
        
        return processed_data
    
    def _apply_noise_reduction(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply noise reduction using spectral gating"""
        try:
            # Apply simple noise reduction using FFT
            fft_data = np.fft.rfft(audio_data)
            magnitudes = np.abs(fft_data)
            
            # Calculate noise profile (assuming noise is in the lower magnitudes)
            sorted_magnitudes = np.sort(magnitudes)
            noise_threshold = sorted_magnitudes[int(len(sorted_magnitudes) * 0.1)]  # 10th percentile
            
            # Apply spectral gating
            clean_fft = fft_data.copy()
            clean_fft[magnitudes < noise_threshold] = 0
            
            # Reconstruct signal
            clean_audio = np.fft.irfft(clean_fft, n=len(audio_data))
            
            return np.real(clean_audio)
            
        except Exception as e:
            self.logger.warning(f"Noise reduction failed: {str(e)}")
            return audio_data
    
    def perform_fft_analysis(self, audio_data: np.ndarray, sample_rate: int) -> SpectralAnalysis:
        """Perform FFT analysis on audio data to extract spectral information"""
        try:
            # Ensure audio data is mono
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)
            
            # Number of samples
            n = len(audio_data)
            
            # Perform FFT
            fft_result = np.fft.fft(audio_data)
            fft_magnitude = np.abs(fft_result)
            fft_phase = np.angle(fft_result)
            
            # Only use first half (positive frequencies)
            half_n = n // 2
            frequencies = np.fft.fftfreq(n, 1.0 / sample_rate)[:half_n]
            magnitudes = fft_magnitude[:half_n]
            phases = fft_phase[:half_n]
            
            # Calculate spectral features
            spectral_centroid = self._calculate_spectral_centroid(frequencies, magnitudes)
            spectral_bandwidth = self._calculate_spectral_bandwidth(frequencies, magnitudes, spectral_centroid)
            spectral_rolloff = self._calculate_spectral_rolloff(frequencies, magnitudes, 0.85)
            spectral_flatness = self._calculate_spectral_flatness(magnitudes)
            zero_crossing_rate = self._calculate_zero_crossing_rate(audio_data)
            rms_amplitude = self._calculate_rms(audio_data)
            peak_amplitude = np.max(np.abs(audio_data))
            
            # Find dominant frequencies (peaks in magnitude spectrum)
            dominant_frequencies = self._find_dominant_frequencies(frequencies, magnitudes)
            
            analysis = SpectralAnalysis(
                frequencies=frequencies,
                magnitudes=magnitudes,
                phases=phases,
                dominant_frequencies=dominant_frequencies,
                spectral_centroid=spectral_centroid,
                spectral_bandwidth=spectral_bandwidth,
                spectral_rolloff=spectral_rolloff,
                spectral_flatness=spectral_flatness,
                zero_crossing_rate=zero_crossing_rate,
                rms_amplitude=rms_amplitude,
                peak_amplitude=peak_amplitude
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"FFT analysis failed: {str(e)}")
            # Return empty analysis
            return SpectralAnalysis(
                frequencies=np.array([]),
                magnitudes=np.array([]),
                phases=np.array([])
            )
    
    def _calculate_spectral_centroid(self, frequencies: np.ndarray, magnitudes: np.ndarray) -> float:
        """Calculate spectral centroid (center of mass of the spectrum)"""
        if len(frequencies) == 0 or len(magnitudes) == 0:
            return 0.0
        
        # Normalize magnitudes
        normalized_magnitudes = magnitudes / np.sum(magnitudes)
        
        # Calculate centroid
        centroid = np.sum(frequencies * normalized_magnitudes)
        return float(centroid)
    
    def _calculate_spectral_bandwidth(self, frequencies: np.ndarray, magnitudes: np.ndarray, centroid: float) -> float:
        """Calculate spectral bandwidth (spread of the spectrum around the centroid)"""
        if len(frequencies) == 0 or len(magnitudes) == 0:
            return 0.0
        
        # Normalize magnitudes
        normalized_magnitudes = magnitudes / np.sum(magnitudes)
        
        # Calculate second moment
        second_moment = np.sum(((frequencies - centroid) ** 2) * normalized_magnitudes)
        
        return float(np.sqrt(second_moment))
    
    def _calculate_spectral_rolloff(self, frequencies: np.ndarray, magnitudes: np.ndarray, rolloff_percent: float = 0.85) -> float:
        """Calculate spectral rolloff (frequency below which rolloff_percent of the total energy is contained)"""
        if len(frequencies) == 0 or len(magnitudes) == 0:
            return 0.0
        
        # Sort frequencies and magnitudes by frequency
        sorted_indices = np.argsort(frequencies)
        sorted_frequencies = frequencies[sorted_indices]
        sorted_magnitudes = magnitudes[sorted_indices]
        
        # Calculate cumulative sum
        cumulative_sum = np.cumsum(sorted_magnitudes)
        total_energy = cumulative_sum[-1]
        
        # Find rolloff frequency
        rolloff_index = np.where(cumulative_sum >= rolloff_percent * total_energy)[0]
        if len(rolloff_index) > 0:
            return float(sorted_frequencies[rolloff_index[0]])
        
        return float(sorted_frequencies[-1])
    
    def _calculate_spectral_flatness(self, magnitudes: np.ndarray) -> float:
        """Calculate spectral flatness (measure of how flat or spiky the spectrum is)"""
        if len(magnitudes) == 0:
            return 0.0
        
        # Avoid division by zero
        magnitudes = magnitudes + 1e-10
        
        # Calculate geometric mean and arithmetic mean
        log_magnitudes = np.log(magnitudes)
        geometric_mean = np.exp(np.mean(log_magnitudes))
        arithmetic_mean = np.mean(magnitudes)
        
        # Calculate flatness
        flatness = geometric_mean / arithmetic_mean
        
        return float(flatness)
    
    def _calculate_zero_crossing_rate(self, audio_data: np.ndarray) -> float:
        """Calculate zero crossing rate (rate at which the signal changes sign)"""
        if len(audio_data) < 2:
            return 0.0
        
        # Count zero crossings
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_data)))) / 2
        
        # Normalize by length
        zcr = zero_crossings / len(audio_data)
        
        return float(zcr)
    
    def _calculate_rms(self, audio_data: np.ndarray) -> float:
        """Calculate root mean square amplitude"""
        if len(audio_data) == 0:
            return 0.0
        
        return float(np.sqrt(np.mean(audio_data ** 2)))
    
    def _find_dominant_frequencies(self, frequencies: np.ndarray, magnitudes: np.ndarray, n_peaks: int = 5) -> List[float]:
        """Find dominant frequencies (peaks in the magnitude spectrum)"""
        if len(frequencies) == 0 or len(magnitudes) == 0:
            return []
        
        # Find peaks in magnitude spectrum
        peaks, _ = signal.find_peaks(magnitudes, height=np.max(magnitudes) * 0.1)
        
        # Sort peaks by magnitude (descending)
        peak_indices = peaks[np.argsort(-magnitudes[peaks])]
        
        # Get top n peaks
        dominant_indices = peak_indices[:min(n_peaks, len(peak_indices))]
        
        # Return corresponding frequencies
        return [float(frequencies[i]) for i in dominant_indices]
    
    def assess_audio_quality(self, audio_data: np.ndarray, sample_rate: int, metadata: AudioMetadata) -> Dict[str, float]:
        """Assess the quality of audio data for spectral analysis"""
        quality_metrics = {}
        
        try:
            # Signal-to-noise ratio estimate
            signal_power = np.mean(audio_data ** 2)
            noise_power = np.mean((audio_data - np.mean(audio_data)) ** 2)
            quality_metrics['snr_estimate'] = float(10 * np.log10(signal_power / (noise_power + 1e-10)))
            
            # Dynamic range
            max_val = np.max(np.abs(audio_data))
            min_val = np.min(np.abs(audio_data[audio_data != 0])) if np.any(audio_data != 0) else 1e-10
            quality_metrics['dynamic_range'] = float(20 * np.log10(max_val / min_val))
            
            # Clipping detection
            clipped_samples = np.sum(np.abs(audio_data) >= 0.99)  # Assuming normalized audio
            quality_metrics['clipping_percentage'] = float(clipped_samples / len(audio_data) * 100)
            
            # DC offset
            dc_offset = np.mean(audio_data)
            quality_metrics['dc_offset'] = float(np.abs(dc_offset))
            
            # Sample rate quality (higher is better for spectral analysis)
            quality_metrics['sample_rate_quality'] = min(sample_rate / 44100.0, 1.0)  # Normalized to 44.1kHz
            
            # Duration quality (longer recordings may be better for analysis)
            quality_metrics['duration_quality'] = min(metadata.duration / 10.0, 1.0)  # Normalized to 10 seconds
            
            # Bit depth quality
            quality_metrics['bit_depth_quality'] = min(metadata.bits_per_sample / 24.0, 1.0)  # Normalized to 24 bits
            
            # Overall quality score (0-100)
            weights = {
                'snr_estimate': 0.25,
                'dynamic_range': 0.15,
                'clipping_percentage': -0.20,  # Negative weight (lower is better)
                'dc_offset': -0.10,  # Negative weight
                'sample_rate_quality': 0.15,
                'duration_quality': 0.10,
                'bit_depth_quality': 0.10
            }
            
            # Normalize metrics to 0-1 range where appropriate
            normalized_metrics = {}
            for metric, weight in weights.items():
                if metric in quality_metrics:
                    if metric in ['clipping_percentage', 'dc_offset']:
                        # For negative weights, invert the metric
                        normalized_metrics[metric] = 1.0 - min(quality_metrics[metric] / 100.0, 1.0) if metric == 'clipping_percentage' else 1.0 - min(quality_metrics[metric], 1.0)
                    else:
                        # For positive weights, normalize to 0-1
                        if metric == 'snr_estimate':
                            normalized_metrics[metric] = min(quality_metrics[metric] / 100.0, 1.0)  # Assuming max 100dB SNR
                        elif metric == 'dynamic_range':
                            normalized_metrics[metric] = min(quality_metrics[metric] / 120.0, 1.0)  # Assuming max 120dB
                        else:
                            normalized_metrics[metric] = quality_metrics[metric]
            
            # Calculate weighted sum
            total_weight = sum(abs(w) for w in weights.values())
            overall_quality = sum(
                normalized_metrics.get(metric, 0) * abs(weight) for metric, weight in weights.items()
            ) / total_weight * 100
            
            quality_metrics['overall_quality'] = round(overall_quality, 2)
            
        except Exception as e:
            self.logger.warning(f"Audio quality assessment failed: {str(e)}")
        
        return quality_metrics
    
    def detect_spectral_content(self, spectral_analysis: SpectralAnalysis) -> Dict[str, Any]:
        """Detect and analyze spectral content in audio data"""
        content_analysis = {
            'has_spectral_content': False,
            'spectral_range': {'min': 0.0, 'max': 0.0, 'center': 0.0},
            'frequency_bands': {},
            'potential_issues': [],
            'recommendations': []
        }
        
        try:
            if len(spectral_analysis.frequencies) == 0 or len(spectral_analysis.magnitudes) == 0:
                return content_analysis
            
            # Check if we have meaningful spectral content
            max_magnitude = np.max(spectral_analysis.magnitudes)
            if max_magnitude > 0:
                content_analysis['has_spectral_content'] = True
            
            # Analyze spectral range
            content_analysis['spectral_range'] = {
                'min': float(np.min(spectral_analysis.frequencies)),
                'max': float(np.max(spectral_analysis.frequencies)),
                'center': spectral_analysis.spectral_centroid
            }
            
            # Analyze frequency bands
            bands = {
                'sub_bass': (20, 60),
                'bass': (60, 250),
                'low_mid': (250, 500),
                'mid': (500, 2000),
                'upper_mid': (2000, 4000),
                'presence': (4000, 6000),
                'brilliance': (6000, 20000)
            }
            
            for band_name, (low, high) in bands.items():
                mask = (spectral_analysis.frequencies >= low) & (spectral_analysis.frequencies <= high)
                if np.any(mask):
                    band_energy = np.sum(spectral_analysis.magnitudes[mask])
                    content_analysis['frequency_bands'][band_name] = {
                        'energy': float(band_energy),
                        'percentage': float(band_energy / np.sum(spectral_analysis.magnitudes) * 100)
                    }
            
            # Detect potential issues
            if spectral_analysis.spectral_flatness > 0.8:
                content_analysis['potential_issues'].append(
                    "High spectral flatness may indicate noise-dominated signal"
                )
            
            if spectral_analysis.zero_crossing_rate > 0.1:
                content_analysis['potential_issues'].append(
                    "High zero-crossing rate may indicate noisy or high-frequency dominated signal"
                )
            
            if len(spectral_analysis.dominant_frequencies) == 0:
                content_analysis['potential_issues'].append(
                    "No clear dominant frequencies detected"
                )
            elif len(spectral_analysis.dominant_frequencies) > 10:
                content_analysis['potential_issues'].append(
                    "Too many dominant frequencies may indicate noise or complex signal"
                )
            
            # Generate recommendations
            if not content_analysis['has_spectral_content']:
                content_analysis['recommendations'].append(
                    "Check if the audio file contains valid spectral data"
                )
            
            if spectral_analysis.spectral_centroid < 1000:
                content_analysis['recommendations'].append(
                    "Consider using a higher sample rate for better low-frequency resolution"
                )
            
            if spectral_analysis.spectral_bandwidth > 5000:
                content_analysis['recommendations'].append(
                    "The signal has a wide bandwidth; consider focusing on specific frequency ranges"
                )
            
        except Exception as e:
            self.logger.warning(f"Spectral content analysis failed: {str(e)}")
        
        return content_analysis
    
    def convert_audio_format(self, input_path: str, output_format: str, output_path: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Convert audio file to different format"""
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
            
            # Use ffmpeg for conversion
            cmd = [
                self.ffmpeg_path,
                '-i', str(input_path),
                '-acodec', 'pcm_s16le' if output_format == 'wav' else 'libmp3lame' if output_format == 'mp3' else 'flac',
                '-ar', str(self.default_sample_rate),
                '-ac', str(self.default_channels),
                '-y',  # Overwrite output file
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                return False, f"Conversion failed: {result.stderr}", None
            
            if not output_path.exists():
                return False, "Output file was not created", None
            
            return True, f"Successfully converted to {output_format}", str(output_path)
            
        except Exception as e:
            return False, f"Conversion error: {str(e)}", None
    
    def extract_spectral_data(self, file_path: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Extract spectral data from audio file"""
        try:
            # Validate file
            is_valid, message, metadata = self.validate_audio_file(file_path)
            if not is_valid:
                return False, message, None
            
            # Load audio
            success, message, audio_data = self.load_audio_file(file_path)
            if not success:
                return False, message, None
            
            audio_samples, sample_rate = audio_data
            
            # Preprocess audio
            processed_audio = self.preprocess_audio(audio_samples, sample_rate)
            
            # Perform FFT analysis
            spectral_analysis = self.perform_fft_analysis(processed_audio, sample_rate)
            
            # Assess audio quality
            quality_metrics = self.assess_audio_quality(processed_audio, sample_rate, metadata)
            
            # Detect spectral content
            content_analysis = self.detect_spectral_content(spectral_analysis)
            
            # Create result
            result = {
                'file_info': {
                    'file_path': str(file_path),
                    'file_name': Path(file_path).name,
                    'file_format': metadata.file_format,
                    'duration': metadata.duration,
                    'sample_rate': sample_rate,
                    'channels': metadata.channels,
                    'bits_per_sample': metadata.bits_per_sample
                },
                'spectral_analysis': {
                    'frequencies': spectral_analysis.frequencies.tolist(),
                    'magnitudes': spectral_analysis.magnitudes.tolist(),
                    'phases': spectral_analysis.phases.tolist(),
                    'dominant_frequencies': spectral_analysis.dominant_frequencies,
                    'spectral_centroid': spectral_analysis.spectral_centroid,
                    'spectral_bandwidth': spectral_analysis.spectral_bandwidth,
                    'spectral_rolloff': spectral_analysis.spectral_rolloff,
                    'spectral_flatness': spectral_analysis.spectral_flatness,
                    'zero_crossing_rate': spectral_analysis.zero_crossing_rate,
                    'rms_amplitude': spectral_analysis.rms_amplitude,
                    'peak_amplitude': spectral_analysis.peak_amplitude
                },
                'quality_metrics': quality_metrics,
                'content_analysis': content_analysis,
                'metadata': metadata.metadata
            }
            
            return True, "Spectral data extraction completed", result
            
        except Exception as e:
            return False, f"Spectral data extraction failed: {str(e)}", None
    
    def process_batch(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process multiple audio files in batch"""
        results = {
            'total_files': len(file_paths),
            'successful': 0,
            'failed': 0,
            'results': {},
            'summary': {}
        }
        
        for file_path in file_paths:
            try:
                success, message, spectral_data = self.extract_spectral_data(file_path)
                
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
                if isinstance(r, dict) and 'spectral_analysis' in r
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
        
        return results
    
    def create_audio_report(self, spectral_data: Dict[str, Any], output_path: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Create a detailed report of audio analysis"""
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
                'spectral_analysis': spectral_data['spectral_analysis'],
                'quality_assessment': spectral_data['quality_metrics'],
                'content_analysis': spectral_data['content_analysis'],
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
        """Generate recommendations based on spectral analysis"""
        recommendations = []
        quality_metrics = spectral_data.get('quality_metrics', {})
        content_analysis = spectral_data.get('content_analysis', {})
        
        # Quality-based recommendations
        if quality_metrics.get('overall_quality', 100) < 70:
            recommendations.append(
                "Overall audio quality is low. Consider re-recording with better equipment or settings."
            )
        
        if quality_metrics.get('clipping_percentage', 0) > 1:
            recommendations.append(
                "Audio clipping detected. Reduce input gain to prevent distortion."
            )
        
        if quality_metrics.get('snr_estimate', 100) < 20:
            recommendations.append(
                "Low signal-to-noise ratio. Try to reduce background noise during recording."
            )
        
        if quality_metrics.get('sample_rate_quality', 1.0) < 0.5:
            recommendations.append(
                f"Low sample rate ({spectral_data['file_info']['sample_rate']} Hz). Consider using at least 44.1kHz for better spectral resolution."
            )
        
        # Content-based recommendations
        if not content_analysis.get('has_spectral_content', True):
            recommendations.append(
                "No clear spectral content detected. Verify that the audio file contains valid spectral data."
            )
        
        if content_analysis.get('spectral_range', {}).get('max', 0) < 1000:
            recommendations.append(
                "Spectral content is limited to low frequencies. Consider extending the frequency range of your measurements."
            )
        
        # Add general recommendations
        recommendations.extend([
            "Ensure proper calibration of your spectrometer before recording.",
            "Use consistent recording conditions for comparable results.",
            "Consider using lossless audio formats (WAV, FLAC) for archival purposes."
        ])
        
        return recommendations
    
    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute the agent's primary function"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting AudioProcessorAgent execution")
            
            action = context.get('action', 'extract_spectral_data')
            
            if action == 'extract_spectral_data':
                file_path = context.get('file_path')
                if not file_path:
                    return self._create_error_output("file_path is required")
                
                success, message, spectral_data = self.extract_spectral_data(file_path)
                
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
                
            elif action == 'validate_audio':
                file_path = context.get('file_path')
                if not file_path:
                    return self._create_error_output("file_path is required")
                
                is_valid, message, metadata = self.validate_audio_file(file_path)
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
                
                if not input_path or not output_format:
                    return self._create_error_output("input_path and output_format are required")
                
                success, message, converted_path = self.convert_audio_format(input_path, output_format, output_path)
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
                
                success, message, report_path = self.create_audio_report(spectral_data, output_path)
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
                success, message, audio_data = self.load_audio_file(file_path)
                if not success:
                    return self._create_error_output(message)
                
                audio_samples, sample_rate = audio_data
                metadata = self.validate_audio_file(file_path)[2]
                
                quality_metrics = self.assess_audio_quality(audio_samples, sample_rate, metadata)
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
                success, message, spectral_data = self.extract_spectral_data(file_path)
                if not success:
                    return self._create_error_output(message)
                
                # Perform content analysis
                spectral_analysis = SpectralAnalysis(
                    frequencies=np.array(spectral_data['spectral_analysis']['frequencies']),
                    magnitudes=np.array(spectral_data['spectral_analysis']['magnitudes']),
                    phases=np.array(spectral_data['spectral_analysis']['phases']),
                    dominant_frequencies=spectral_data['spectral_analysis']['dominant_frequencies'],
                    spectral_centroid=spectral_data['spectral_analysis']['spectral_centroid'],
                    spectral_bandwidth=spectral_data['spectral_analysis']['spectral_bandwidth'],
                    spectral_rolloff=spectral_data['spectral_analysis']['spectral_rolloff'],
                    spectral_flatness=spectral_data['spectral_analysis']['spectral_flatness'],
                    zero_crossing_rate=spectral_data['spectral_analysis']['zero_crossing_rate'],
                    rms_amplitude=spectral_data['spectral_analysis']['rms_amplitude'],
                    peak_amplitude=spectral_data['spectral_analysis']['peak_amplitude']
                )
                
                content_analysis = self.detect_spectral_content(spectral_analysis)
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
                            "supports_metadata": info.supports_metadata
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
        required_deps = ['numpy', 'scipy']
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
        
        # Check if ffmpeg is available if we want to use it
        try:
            subprocess.run([self.ffmpeg_path, '-version'], 
                         capture_output=True, timeout=5)
        except (subprocess.SubprocessError, FileNotFoundError):
            errors.append(AgentError(
                agent_name=self.name,
                error_type="dependency_error",
                message=f"ffmpeg not found at {self.ffmpeg_path}",
                severity=ErrorSeverity.MEDIUM,
                context={"ffmpeg_path": self.ffmpeg_path},
                solution="Install ffmpeg or set correct ffmpeg_path in configuration"
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
    agent = AudioProcessorAgent()
    output = agent.initialize()
    print(f"AudioProcessorAgent initialized: {output.status.name}")
