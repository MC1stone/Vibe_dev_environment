"""
Core models for NIR_Mistral Framework
"""

import uuid
import json
import os
from pathlib import Path
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinLengthValidator
from django.utils import timezone
from django.conf import settings


class User(AbstractUser):
    """Custom user model for NIR_Mistral"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, verbose_name='Email Address')
    username = models.CharField(
        max_length=50, 
        unique=True, 
        validators=[MinLengthValidator(3)],
        verbose_name='Username'
    )
    first_name = models.CharField(max_length=100, blank=True, verbose_name='First Name')
    last_name = models.CharField(max_length=100, blank=True, verbose_name='Last Name')
    
    # Profile fields
    institution = models.CharField(max_length=200, blank=True, verbose_name='Institution')
    department = models.CharField(max_length=200, blank=True, verbose_name='Department')
    position = models.CharField(max_length=100, blank=True, verbose_name='Position')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Phone Number')
    
    # Preferences
    preferred_language = models.CharField(max_length=10, default='en', verbose_name='Language')
    theme_preference = models.CharField(max_length=10, default='light', verbose_name='Theme')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    last_login = models.DateTimeField(null=True, blank=True, verbose_name='Last Login')
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name='Active')
    is_verified = models.BooleanField(default=False, verbose_name='Email Verified')
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        return self.first_name if self.first_name else self.username


class NIRSpectrum(models.Model):
    """Model for NIR Spectroscopy Data"""
    
    SPECTRAL_TYPES = [
        ('absorbance', 'Absorbance'),
        ('reflectance', 'Reflectance'),
        ('transmittance', 'Transmittance'),
    ]
    
    DATA_FORMATS = [
        ('txt', 'Text File'),
        ('csv', 'CSV File'),
        ('json', 'JSON File'),
        ('h5', 'HDF5 File'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='spectra',
        verbose_name='User'
    )
    
    # Basic information
    name = models.CharField(max_length=200, verbose_name='Spectrum Name')
    description = models.TextField(blank=True, verbose_name='Description')
    
    # Sample information
    sample_id = models.CharField(max_length=100, blank=True, verbose_name='Sample ID')
    sample_type = models.CharField(max_length=100, blank=True, verbose_name='Sample Type')
    sample_source = models.CharField(max_length=200, blank=True, verbose_name='Sample Source')
    
    # Spectral data
    spectral_type = models.CharField(
        max_length=20, 
        choices=SPECTRAL_TYPES, 
        default='absorbance',
        verbose_name='Spectral Type'
    )
    data_format = models.CharField(
        max_length=10, 
        choices=DATA_FORMATS, 
        default='txt',
        verbose_name='Data Format'
    )
    
    # File storage
    original_file = models.FileField(
        upload_to='spectra/original/', 
        verbose_name='Original File'
    )
    processed_file = models.FileField(
        upload_to='spectra/processed/', 
        blank=True, 
        null=True,
        verbose_name='Processed File'
    )
    
    # Metadata
    wavelength_range_start = models.FloatField(verbose_name='Wavelength Start (nm)')
    wavelength_range_end = models.FloatField(verbose_name='Wavelength End (nm)')
    resolution = models.FloatField(verbose_name='Resolution (nm)')
    data_points = models.IntegerField(verbose_name='Number of Data Points')
    
    # Collection information
    instrument = models.CharField(max_length=200, blank=True, verbose_name='Instrument')
    collection_date = models.DateTimeField(
        default=timezone.now, 
        verbose_name='Collection Date'
    )
    collection_conditions = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='Collection Conditions'
    )
    
    # Analysis metadata
    mean_absorbance = models.FloatField(blank=True, null=True, verbose_name='Mean Absorbance')
    max_absorbance = models.FloatField(blank=True, null=True, verbose_name='Max Absorbance')
    min_absorbance = models.FloatField(blank=True, null=True, verbose_name='Min Absorbance')
    peaks_detected = models.IntegerField(default=0, verbose_name='Peaks Detected')
    
    # Quality metrics
    signal_to_noise_ratio = models.FloatField(blank=True, null=True, verbose_name='S/N Ratio')
    baseline_corrected = models.BooleanField(default=False, verbose_name='Baseline Corrected')
    quality_score = models.FloatField(default=0.0, verbose_name='Quality Score')
    
    # Status and timestamps
    status = models.CharField(
        max_length=20, 
        default='uploaded',
        verbose_name='Status'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='Processed At')
    
    # Tags and categories
    tags = models.JSONField(default=list, blank=True, verbose_name='Tags')
    categories = models.JSONField(default=list, blank=True, verbose_name='Categories')
    
    class Meta:
        verbose_name = 'NIR Spectrum'
        verbose_name_plural = 'NIR Spectra'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['sample_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.sample_id or self.id})"
    
    def get_file_path(self):
        """Get the absolute path to the original file"""
        if self.original_file:
            return os.path.join(settings.MEDIA_ROOT, str(self.original_file))
        return None
    
    def get_data_summary(self):
        """Get a summary of the spectral data"""
        return {
            'id': str(self.id),
            'name': self.name,
            'sample_id': self.sample_id,
            'spectral_type': self.spectral_type,
            'wavelength_range': f"{self.wavelength_range_start}-{self.wavelength_range_end} nm",
            'resolution': f"{self.resolution} nm",
            'data_points': self.data_points,
            'mean_absorbance': self.mean_absorbance,
            'peaks_detected': self.peaks_detected,
            'quality_score': self.quality_score,
        }


class AnalysisJob(models.Model):
    """Model for Analysis Jobs"""
    
    JOB_TYPES = [
        ('spectral_analysis', 'Spectral Analysis'),
        ('quality_control', 'Quality Control'),
        ('peak_detection', 'Peak Detection'),
        ('baseline_correction', 'Baseline Correction'),
        ('noise_reduction', 'Noise Reduction'),
        ('classification', 'Classification'),
        ('regression', 'Regression'),
        ('custom', 'Custom Analysis'),
    ]
    
    JOB_STATUSES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='analysis_jobs',
        verbose_name='User'
    )
    
    # Job information
    name = models.CharField(max_length=200, verbose_name='Job Name')
    job_type = models.CharField(
        max_length=50, 
        choices=JOB_TYPES, 
        default='spectral_analysis',
        verbose_name='Job Type'
    )
    description = models.TextField(blank=True, verbose_name='Description')
    
    # Related spectra
    spectra = models.ManyToManyField(
        NIRSpectrum, 
        related_name='analysis_jobs',
        verbose_name='Spectra'
    )
    
    # Agent information
    agent_name = models.CharField(max_length=100, verbose_name='Agent Name')
    agent_version = models.CharField(max_length=20, blank=True, verbose_name='Agent Version')
    
    # Parameters
    parameters = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='Parameters'
    )
    
    # Results
    results = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='Results'
    )
    
    # Status and progress
    status = models.CharField(
        max_length=20, 
        choices=JOB_STATUSES, 
        default='pending',
        verbose_name='Status'
    )
    progress = models.FloatField(default=0.0, verbose_name='Progress (%)')
    error_message = models.TextField(blank=True, verbose_name='Error Message')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Started At')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Completed At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    # Performance metrics
    execution_time = models.FloatField(blank=True, null=True, verbose_name='Execution Time (s)')
    memory_usage = models.FloatField(blank=True, null=True, verbose_name='Memory Usage (MB)')
    
    class Meta:
        verbose_name = 'Analysis Job'
        verbose_name_plural = 'Analysis Jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['job_type']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.job_type}) - {self.status}"
    
    def get_duration(self):
        """Get the duration of the job in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


class Agent(models.Model):
    """Model for NIR Analysis Agents"""
    
    AGENT_STATUSES = [
        ('available', 'Available'),
        ('running', 'Running'),
        ('disabled', 'Disabled'),
        ('error', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Agent information
    name = models.CharField(max_length=100, unique=True, verbose_name='Agent Name')
    display_name = models.CharField(max_length=200, verbose_name='Display Name')
    description = models.TextField(blank=True, verbose_name='Description')
    version = models.CharField(max_length=20, default='1.0.0', verbose_name='Version')
    
    # Agent file
    agent_file = models.CharField(max_length=200, verbose_name='Agent File')
    
    # Capabilities
    capabilities = models.JSONField(default=list, blank=True, verbose_name='Capabilities')
    supported_formats = models.JSONField(default=list, blank=True, verbose_name='Supported Formats')
    parameters_schema = models.JSONField(default=dict, blank=True, verbose_name='Parameters Schema')
    
    # Dependencies
    dependencies = models.JSONField(default=list, blank=True, verbose_name='Dependencies')
    
    # Status
    status = models.CharField(
        max_length=20, 
        choices=AGENT_STATUSES, 
        default='available',
        verbose_name='Status'
    )
    last_error = models.TextField(blank=True, verbose_name='Last Error')
    
    # Performance
    average_execution_time = models.FloatField(blank=True, null=True, verbose_name='Avg Execution Time (s)')
    success_rate = models.FloatField(default=0.0, verbose_name='Success Rate (%)')
    total_executions = models.IntegerField(default=0, verbose_name='Total Executions')
    successful_executions = models.IntegerField(default=0, verbose_name='Successful Executions')
    
    # Metadata
    author = models.CharField(max_length=100, blank=True, verbose_name='Author')
    license = models.CharField(max_length=50, blank=True, verbose_name='License')
    documentation = models.URLField(blank=True, verbose_name='Documentation URL')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    last_executed = models.DateTimeField(null=True, blank=True, verbose_name='Last Executed')
    
    class Meta:
        verbose_name = 'Agent'
        verbose_name_plural = 'Agents'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.display_name} ({self.version})"
    
    def get_success_rate(self):
        """Calculate success rate"""
        if self.total_executions > 0:
            return (self.successful_executions / self.total_executions) * 100
        return 0.0


class SystemLog(models.Model):
    """Model for System Logs"""
    
    LOG_LEVELS = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='system_logs',
        verbose_name='User'
    )
    
    # Log information
    level = models.CharField(
        max_length=10, 
        choices=LOG_LEVELS, 
        default='INFO',
        verbose_name='Log Level'
    )
    message = models.TextField(verbose_name='Message')
    module = models.CharField(max_length=100, blank=True, verbose_name='Module')
    function = models.CharField(max_length=100, blank=True, verbose_name='Function')
    
    # Additional context
    context = models.JSONField(default=dict, blank=True, verbose_name='Context')
    stack_trace = models.TextField(blank=True, verbose_name='Stack Trace')
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Timestamp')
    
    class Meta:
        verbose_name = 'System Log'
        verbose_name_plural = 'System Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['level']),
            models.Index(fields=['module']),
        ]
    
    def __str__(self):
        return f"[{self.level}] {self.message[:50]}..."


class UserPreference(models.Model):
    """Model for User Preferences"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='preferences',
        verbose_name='User'
    )
    
    # Display preferences
    theme = models.CharField(max_length=20, default='light', verbose_name='Theme')
    language = models.CharField(max_length=10, default='en', verbose_name='Language')
    timezone = models.CharField(max_length=50, default='UTC', verbose_name='Timezone')
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True, verbose_name='Email Notifications')
    job_completion_notifications = models.BooleanField(default=True, verbose_name='Job Completion Notifications')
    error_notifications = models.BooleanField(default=True, verbose_name='Error Notifications')
    
    # Analysis preferences
    default_agent = models.ForeignKey(
        Agent, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='default_for_users',
        verbose_name='Default Agent'
    )
    auto_process_uploads = models.BooleanField(default=False, verbose_name='Auto Process Uploads')
    
    # Storage preferences
    max_storage_usage = models.IntegerField(default=1000, verbose_name='Max Storage (MB)')
    auto_cleanup_old_files = models.BooleanField(default=False, verbose_name='Auto Cleanup Old Files')
    retention_days = models.IntegerField(default=30, verbose_name='Retention Days')
    
    # FlowerAI and Federated Learning preferences
    flowerai_enabled = models.BooleanField(default=True, verbose_name='FlowerAI Enabled')
    federated_learning_enabled = models.BooleanField(default=True, verbose_name='Federated Learning Enabled')
    share_spectra_data = models.BooleanField(default=True, verbose_name='Share Spectra Data')
    share_metadata = models.BooleanField(default=True, verbose_name='Share Metadata')
    share_analysis_results = models.BooleanField(default=True, verbose_name='Share Analysis Results')
    
    # Data visibility options: 'private', 'public', 'federated'
    DATA_VISIBILITY_CHOICES = [
        ('private', 'Private (Local Only)'),
        ('public', 'Public (Shared with all users)'),
        ('federated', 'Federated (Shared with FlowerAI network)'),
    ]
    data_visibility = models.CharField(
        max_length=20, 
        choices=DATA_VISIBILITY_CHOICES, 
        default='private', 
        verbose_name='Data Visibility'
    )
    
    # ILIAS Integration preferences
    ilias_enabled = models.BooleanField(default=True, verbose_name='ILIAS Integration Enabled')
    ilias_sync_enabled = models.BooleanField(default=True, verbose_name='ILIAS Synchronization Enabled')
    ilias_user_id = models.CharField(max_length=100, blank=True, verbose_name='ILIAS User ID')
    ilias_session_token = models.CharField(max_length=200, blank=True, verbose_name='ILIAS Session Token')
    
    # FlowerAI client configuration
    flowerai_client_id = models.CharField(max_length=100, blank=True, verbose_name='FlowerAI Client ID')
    flowerai_server_url = models.URLField(blank=True, verbose_name='FlowerAI Server URL')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'User Preference'
        verbose_name_plural = 'User Preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.email}"


class GenericFile(models.Model):
    """Model for Generic File Storage - Handles any file type for analysis and processing"""
    
    # File categories
    FILE_CATEGORIES = [
        ('spectral', 'Spectral Data'),
        ('tabular', 'Tabular Data'),
        ('text', 'Text'),
        ('image', 'Image'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('archive', 'Archive'),
        ('document', 'Document'),
        ('binary', 'Binary'),
        ('unknown', 'Unknown'),
    ]
    
    # Quality grades
    QUALITY_GRADES = [
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('unacceptable', 'Unacceptable'),
        ('unknown', 'Unknown'),
    ]
    
    # Processing statuses
    PROCESSING_STATUSES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('analyzing', 'Analyzing'),
        ('analyzed', 'Analyzed'),
        ('error', 'Error'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='generic_files',
        verbose_name='User'
    )
    
    # Basic file information
    name = models.CharField(max_length=255, verbose_name='File Name')
    original_filename = models.CharField(max_length=255, verbose_name='Original Filename')
    description = models.TextField(blank=True, verbose_name='Description')
    
    # File storage
    file = models.FileField(upload_to='files/', verbose_name='File')
    thumbnail = models.ImageField(upload_to='files/thumbnails/', blank=True, null=True, verbose_name='Thumbnail')
    preview_file = models.FileField(upload_to='files/previews/', blank=True, null=True, verbose_name='Preview File')
    
    # File metadata
    file_size = models.PositiveBigIntegerField(verbose_name='File Size (bytes)')
    file_extension = models.CharField(max_length=20, verbose_name='File Extension')
    mime_type = models.CharField(max_length=100, blank=True, verbose_name='MIME Type')
    file_category = models.CharField(
        max_length=20, 
        choices=FILE_CATEGORIES, 
        default='unknown',
        verbose_name='File Category'
    )
    
    # Content metadata (will be extracted based on file type)
    content_metadata = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='Content Metadata'
    )
    
    # For tabular/spectral data
    num_rows = models.IntegerField(null=True, blank=True, verbose_name='Number of Rows')
    num_columns = models.IntegerField(null=True, blank=True, verbose_name='Number of Columns')
    column_names = models.JSONField(default=list, blank=True, verbose_name='Column Names')
    data_types = models.JSONField(default=dict, blank=True, verbose_name='Data Types')
    
    # For text files
    num_lines = models.IntegerField(null=True, blank=True, verbose_name='Number of Lines')
    num_words = models.IntegerField(null=True, blank=True, verbose_name='Number of Words')
    num_characters = models.IntegerField(null=True, blank=True, verbose_name='Number of Characters')
    
    # For images
    image_width = models.IntegerField(null=True, blank=True, verbose_name='Image Width')
    image_height = models.IntegerField(null=True, blank=True, verbose_name='Image Height')
    image_channels = models.IntegerField(null=True, blank=True, verbose_name='Image Channels')
    image_format = models.CharField(max_length=20, blank=True, verbose_name='Image Format')
    
    # For audio
    audio_duration = models.FloatField(null=True, blank=True, verbose_name='Audio Duration (seconds)')
    audio_sample_rate = models.IntegerField(null=True, blank=True, verbose_name='Audio Sample Rate')
    audio_channels = models.IntegerField(null=True, blank=True, verbose_name='Audio Channels')
    audio_bit_rate = models.IntegerField(null=True, blank=True, verbose_name='Audio Bit Rate')
    
    # For video
    video_duration = models.FloatField(null=True, blank=True, verbose_name='Video Duration (seconds)')
    video_resolution = models.CharField(max_length=20, blank=True, verbose_name='Video Resolution')
    video_frame_rate = models.FloatField(null=True, blank=True, verbose_name='Video Frame Rate')
    video_codec = models.CharField(max_length=50, blank=True, verbose_name='Video Codec')
    
    # For archives
    archive_contents = models.JSONField(default=list, blank=True, verbose_name='Archive Contents')
    archive_num_files = models.IntegerField(null=True, blank=True, verbose_name='Number of Files in Archive')
    
    # Hashes for integrity
    md5_hash = models.CharField(max_length=64, blank=True, verbose_name='MD5 Hash')
    sha1_hash = models.CharField(max_length=64, blank=True, verbose_name='SHA1 Hash')
    sha256_hash = models.CharField(max_length=128, blank=True, verbose_name='SHA256 Hash')
    
    # Quality assessment
    quality_score = models.FloatField(default=0.0, verbose_name='Quality Score')
    quality_grade = models.CharField(
        max_length=20, 
        choices=QUALITY_GRADES, 
        default='unknown',
        verbose_name='Quality Grade'
    )
    quality_issues = models.JSONField(default=list, blank=True, verbose_name='Quality Issues')
    
    # Processing information
    processing_status = models.CharField(
        max_length=20, 
        choices=PROCESSING_STATUSES, 
        default='uploaded',
        verbose_name='Processing Status'
    )
    processing_results = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='Processing Results'
    )
    analysis_results = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='Analysis Results'
    )
    recommendations = models.JSONField(
        default=list, 
        blank=True,
        verbose_name='Recommendations'
    )
    
    # Agent processing
    processed_by_agent = models.CharField(max_length=100, blank=True, verbose_name='Processed By Agent')
    agent_version = models.CharField(max_length=20, blank=True, verbose_name='Agent Version')
    processing_parameters = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='Processing Parameters'
    )
    
    # Tags and categories
    tags = models.JSONField(default=list, blank=True, verbose_name='Tags')
    custom_metadata = models.JSONField(default=dict, blank=True, verbose_name='Custom Metadata')
    
    # Relationship to spectral data (if this file is spectral)
    spectral_data = models.OneToOneField(
        NIRSpectrum, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='generic_file',
        verbose_name='Related Spectral Data'
    )
    
    # Status and timestamps
    is_valid = models.BooleanField(default=True, verbose_name='Is Valid')
    is_processed = models.BooleanField(default=False, verbose_name='Is Processed')
    is_analyzed = models.BooleanField(default=False, verbose_name='Is Analyzed')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='Processed At')
    analyzed_at = models.DateTimeField(null=True, blank=True, verbose_name='Analyzed At')
    
    class Meta:
        verbose_name = 'Generic File'
        verbose_name_plural = 'Generic Files'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['file_category']),
            models.Index(fields=['processing_status']),
            models.Index(fields=['quality_grade']),
            models.Index(fields=['is_valid']),
            models.Index(fields=['is_processed']),
            models.Index(fields=['is_analyzed']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.file_category})"
    
    def get_file_path(self):
        """Get the absolute path to the file"""
        if self.file:
            return os.path.join(settings.MEDIA_ROOT, str(self.file))
        return None
    
    def get_file_url(self):
        """Get the URL to the file"""
        if self.file:
            return self.file.url
        return None
    
    def get_file_summary(self):
        """Get a summary of the file"""
        return {
            'id': str(self.id),
            'name': self.name,
            'original_filename': self.original_filename,
            'file_category': self.file_category,
            'file_extension': self.file_extension,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'quality_score': self.quality_score,
            'quality_grade': self.quality_grade,
            'processing_status': self.processing_status,
            'is_valid': self.is_valid,
            'is_processed': self.is_processed,
            'is_analyzed': self.is_analyzed,
            'created_at': self.created_at.isoformat(),
            'tags': self.tags,
            'description': self.description
        }
    
    def get_metadata_summary(self):
        """Get a summary of the file metadata"""
        metadata = {
            'basic': {
                'name': self.name,
                'original_filename': self.original_filename,
                'file_size': self.file_size,
                'file_extension': self.file_extension,
                'mime_type': self.mime_type,
                'file_category': self.file_category
            },
            'content': self.content_metadata,
            'quality': {
                'score': self.quality_score,
                'grade': self.quality_grade,
                'issues': self.quality_issues
            }
        }
        
        # Add type-specific metadata
        if self.file_category == 'tabular' or self.file_category == 'spectral':
            metadata['tabular'] = {
                'num_rows': self.num_rows,
                'num_columns': self.num_columns,
                'column_names': self.column_names,
                'data_types': self.data_types
            }
        elif self.file_category == 'text':
            metadata['text'] = {
                'num_lines': self.num_lines,
                'num_words': self.num_words,
                'num_characters': self.num_characters
            }
        elif self.file_category == 'image':
            metadata['image'] = {
                'width': self.image_width,
                'height': self.image_height,
                'channels': self.image_channels,
                'format': self.image_format
            }
        elif self.file_category == 'audio':
            metadata['audio'] = {
                'duration': self.audio_duration,
                'sample_rate': self.audio_sample_rate,
                'channels': self.audio_channels,
                'bit_rate': self.audio_bit_rate
            }
        elif self.file_category == 'video':
            metadata['video'] = {
                'duration': self.video_duration,
                'resolution': self.video_resolution,
                'frame_rate': self.video_frame_rate,
                'codec': self.video_codec
            }
        elif self.file_category == 'archive':
            metadata['archive'] = {
                'num_files': self.archive_num_files,
                'contents': self.archive_contents
            }
        
        return metadata
    
    def get_processing_info(self):
        """Get processing information"""
        return {
            'status': self.processing_status,
            'results': self.processing_results,
            'analysis': self.analysis_results,
            'recommendations': self.recommendations,
            'processed_by': self.processed_by_agent,
            'agent_version': self.agent_version,
            'parameters': self.processing_parameters,
            'is_processed': self.is_processed,
            'is_analyzed': self.is_analyzed,
            'processed_at': self.processed_at,
            'analyzed_at': self.analyzed_at
        }
    
    def save_with_metadata(self, metadata_dict):
        """Save the file with extracted metadata"""
        # Update fields from metadata
        if 'file_category' in metadata_dict:
            self.file_category = metadata_dict['file_category']
        if 'mime_type' in metadata_dict:
            self.mime_type = metadata_dict['mime_type']
        if 'quality_score' in metadata_dict:
            self.quality_score = metadata_dict['quality_score']
        if 'quality_grade' in metadata_dict:
            self.quality_grade = metadata_dict['quality_grade']
        if 'quality_issues' in metadata_dict:
            self.quality_issues = metadata_dict['quality_issues']
        if 'content_metadata' in metadata_dict:
            self.content_metadata = metadata_dict['content_metadata']
        
        # Save type-specific metadata
        if self.file_category in ['tabular', 'spectral']:
            if 'num_rows' in metadata_dict:
                self.num_rows = metadata_dict['num_rows']
            if 'num_columns' in metadata_dict:
                self.num_columns = metadata_dict['num_columns']
            if 'column_names' in metadata_dict:
                self.column_names = metadata_dict['column_names']
            if 'data_types' in metadata_dict:
                self.data_types = metadata_dict['data_types']
        
        elif self.file_category == 'text':
            if 'num_lines' in metadata_dict:
                self.num_lines = metadata_dict['num_lines']
            if 'num_words' in metadata_dict:
                self.num_words = metadata_dict['num_words']
            if 'num_characters' in metadata_dict:
                self.num_characters = metadata_dict['num_characters']
        
        elif self.file_category == 'image':
            if 'image_width' in metadata_dict:
                self.image_width = metadata_dict['image_width']
            if 'image_height' in metadata_dict:
                self.image_height = metadata_dict['image_height']
            if 'image_channels' in metadata_dict:
                self.image_channels = metadata_dict['image_channels']
            if 'image_format' in metadata_dict:
                self.image_format = metadata_dict['image_format']
        
        elif self.file_category == 'audio':
            if 'audio_duration' in metadata_dict:
                self.audio_duration = metadata_dict['audio_duration']
            if 'audio_sample_rate' in metadata_dict:
                self.audio_sample_rate = metadata_dict['audio_sample_rate']
            if 'audio_channels' in metadata_dict:
                self.audio_channels = metadata_dict['audio_channels']
            if 'audio_bit_rate' in metadata_dict:
                self.audio_bit_rate = metadata_dict['audio_bit_rate']
        
        elif self.file_category == 'video':
            if 'video_duration' in metadata_dict:
                self.video_duration = metadata_dict['video_duration']
            if 'video_resolution' in metadata_dict:
                self.video_resolution = metadata_dict['video_resolution']
            if 'video_frame_rate' in metadata_dict:
                self.video_frame_rate = metadata_dict['video_frame_rate']
            if 'video_codec' in metadata_dict:
                self.video_codec = metadata_dict['video_codec']
        
        elif self.file_category == 'archive':
            if 'archive_contents' in metadata_dict:
                self.archive_contents = metadata_dict['archive_contents']
            if 'archive_num_files' in metadata_dict:
                self.archive_num_files = metadata_dict['archive_num_files']
        
        # Mark as processed
        self.is_processed = True
        self.processing_status = 'processed'
        self.processed_at = timezone.now()
        
        self.save()