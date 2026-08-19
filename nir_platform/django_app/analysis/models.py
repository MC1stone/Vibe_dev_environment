"""
Models for the Analysis app in NIR Intelligence Platform.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class SpectralData(models.Model):
    """Model for storing spectral data."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # File information
    original_filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_type = models.CharField(max_length=50)
    upload_date = models.DateTimeField(default=timezone.now)
    
    # Spectral data
    wavelengths = models.JSONField(default=list)  # List of wavelengths
    intensities = models.JSONField(default=list)  # List of intensities
    
    # Metadata
    metadata = models.JSONField(default=dict)
    spectrometer_type = models.CharField(max_length=100, blank=True, null=True)
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    processing_date = models.DateTimeField(null=True, blank=True)
    
    # Quality scores
    data_quality_score = models.FloatField(null=True, blank=True)
    metadata_quality_score = models.FloatField(null=True, blank=True)
    calibration_quality_score = models.FloatField(null=True, blank=True)
    overall_quality_score = models.FloatField(null=True, blank=True)
    
    # Analysis results
    analysis_results = models.JSONField(default=dict)
    calibration_results = models.JSONField(default=dict)
    metadata_quality_results = models.JSONField(default=dict)
    
    # Federated learning
    federated_consent = models.BooleanField(default=False)
    is_federated = models.BooleanField(default=False)
    federation_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-upload_date']
        verbose_name = 'Spectral Data'
        verbose_name_plural = 'Spectral Data'
    
    def __str__(self):
        return f"{self.original_filename} ({self.upload_date})"
    
    def get_quality_grade(self):
        """Get quality grade based on overall score."""
        if self.overall_quality_score is None:
            return "N/A"
        if self.overall_quality_score >= 90:
            return "A"
        elif self.overall_quality_score >= 80:
            return "B"
        elif self.overall_quality_score >= 70:
            return "C"
        elif self.overall_quality_score >= 60:
            return "D"
        else:
            return "F"


class AnalysisProject(models.Model):
    """Model for analysis projects (collections of spectral data)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Project metadata
    project_type = models.CharField(max_length=100, blank=True, null=True)
    tags = models.JSONField(default=list)
    
    # Status
    status = models.CharField(max_length=50, default='draft')  # draft, processing, completed, error
    progress = models.FloatField(default=0.0)  # 0-100
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Related spectral data
    spectral_data = models.ManyToManyField(SpectralData, related_name='projects')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Analysis Project'
        verbose_name_plural = 'Analysis Projects'
    
    def __str__(self):
        return self.name


class Report(models.Model):
    """Model for storing generated reports."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    spectral_data = models.ForeignKey(SpectralData, on_delete=models.CASCADE, related_name='reports')
    
    # Report information
    report_type = models.CharField(max_length=100, default='spectral_analysis')
    title = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    
    # Content
    quarto_content = models.TextField()
    html_content = models.TextField(blank=True, null=True)
    python_source = models.TextField(blank=True, null=True)
    
    # Status
    is_generated = models.BooleanField(default=False)
    generation_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-generation_date']
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'
    
    def __str__(self):
        return f"{self.title} ({self.report_type})"


class ChatSession(models.Model):
    """Model for storing chat sessions with AI agents."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    spectral_data = models.ForeignKey(SpectralData, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Session information
    session_name = models.CharField(max_length=255, blank=True, null=True)
    agent_type = models.CharField(max_length=100, default='analysis')
    
    # Messages
    messages = models.JSONField(default=list)  # List of message dicts
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Chat Session'
        verbose_name_plural = 'Chat Sessions'
    
    def __str__(self):
        return f"Chat with {self.agent_type} ({self.created_at})"


class SystemLog(models.Model):
    """Model for storing system logs."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Log information
    level = models.CharField(max_length=20, default='INFO')  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message = models.TextField()
    module = models.CharField(max_length=100, blank=True, null=True)
    function = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional context
    context = models.JSONField(default=dict)
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'System Log'
        verbose_name_plural = 'System Logs'
    
    def __str__(self):
        return f"{self.level}: {self.message[:50]}..."


class CalibrationHistory(models.Model):
    """Model for storing calibration history."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    spectral_data = models.ForeignKey(SpectralData, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Calibration information
    calibration_type = models.CharField(max_length=100)  # wavelength, intensity, full
    calibration_data = models.JSONField(default=dict)
    
    # Quality metrics
    r_squared = models.FloatField(null=True, blank=True)
    rmse = models.FloatField(null=True, blank=True)
    quality_score = models.FloatField(null=True, blank=True)
    
    # Timestamps
    calibration_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-calibration_date']
        verbose_name = 'Calibration History'
        verbose_name_plural = 'Calibration Histories'
    
    def __str__(self):
        return f"{self.calibration_type} calibration ({self.calibration_date})"
