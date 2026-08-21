"""
Serializers for NIR_Mistral API
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from core.models import User, NIRSpectrum, AnalysisJob, Agent, SystemLog, UserPreference, GenericFile
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'password', 'password2']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'institution', 'department', 'position', 'phone',
            'preferred_language', 'theme_preference',
            'is_active', 'is_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_active', 'is_verified', 'created_at', 'updated_at']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer that accepts both username and email"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The parent class sets up the username_field (which is 'email' for our User model)
        # Make the email field not required since we'll handle validation
        self.fields[self.username_field].required = False
        # Add username field to accept username as an alternative
        self.fields['username'] = serializers.CharField(write_only=True, required=False)
    
    def validate(self, attrs):
        # Handle the case where username is provided instead of email
        if 'username' in attrs and self.username_field not in attrs:
            # Look up the user by username to get their email
            User = get_user_model()
            try:
                user = User.objects.get(username=attrs['username'])
                # Use the user's actual email for authentication
                attrs[self.username_field] = user.email
            except User.DoesNotExist:
                # If user doesn't exist, pass through the username as email
                # This will fail authentication but with a proper error message
                attrs[self.username_field] = attrs['username']
        elif self.username_field not in attrs and 'username' not in attrs:
            # If neither is provided, raise error
            raise serializers.ValidationError({self.username_field: 'This field is required.'})
        
        return super().validate(attrs)
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['email'] = user.email
        token['username'] = user.username
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        
        return token


class NIRSpectrumSerializer(serializers.ModelSerializer):
    """Serializer for NIR Spectrum"""
    
    user = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = NIRSpectrum
        fields = [
            'id', 'user', 'name', 'description',
            'sample_id', 'sample_type', 'sample_source',
            'spectral_type', 'data_format',
            'original_file', 'processed_file',
            'wavelength_range_start', 'wavelength_range_end',
            'resolution', 'data_points',
            'instrument', 'collection_date', 'collection_conditions',
            'mean_absorbance', 'max_absorbance', 'min_absorbance',
            'peaks_detected', 'signal_to_noise_ratio',
            'baseline_corrected', 'quality_score',
            'status', 'tags', 'categories',
            'created_at', 'updated_at', 'processed_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'processed_at']
    
    def validate(self, attrs):
        # Validate wavelength range
        if 'wavelength_range_start' in attrs and 'wavelength_range_end' in attrs:
            if attrs['wavelength_range_start'] >= attrs['wavelength_range_end']:
                raise serializers.ValidationError(
                    "wavelength_range_start must be less than wavelength_range_end"
                )
        
        # Validate resolution
        if 'resolution' in attrs and attrs['resolution'] <= 0:
            raise serializers.ValidationError("Resolution must be positive")
        
        return attrs


class NIRSpectrumUploadSerializer(serializers.ModelSerializer):
    """Serializer for NIR Spectrum upload (simplified)"""
    
    class Meta:
        model = NIRSpectrum
        fields = [
            'id', 'name', 'description',
            'sample_id', 'sample_type', 'sample_source',
            'spectral_type', 'data_format',
            'original_file',
            'wavelength_range_start', 'wavelength_range_end',
            'resolution', 'data_points',
            'instrument', 'tags', 'categories'
        ]
        read_only_fields = ['id']
    
    def validate_data_format(self, value):
        """Validate that the data format is one of the allowed values"""
        allowed_formats = [choice[0] for choice in NIRSpectrum.DATA_FORMATS]
        if value not in allowed_formats:
            raise serializers.ValidationError(
                f'Invalid data format. Allowed formats are: {", ".join(allowed_formats)}'
            )
        return value
    
    def validate_spectral_type(self, value):
        """Validate that the spectral type is one of the allowed values"""
        allowed_types = [choice[0] for choice in NIRSpectrum.SPECTRAL_TYPES]
        if value not in allowed_types:
            raise serializers.ValidationError(
                f'Invalid spectral type. Allowed types are: {", ".join(allowed_types)}'
            )
        return value


class AnalysisJobSerializer(serializers.ModelSerializer):
    """Serializer for Analysis Job"""
    
    user = UserProfileSerializer(read_only=True)
    spectra = NIRSpectrumSerializer(many=True, read_only=True)
    spectra_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        default=[]
    )
    
    class Meta:
        model = AnalysisJob
        fields = [
            'id', 'user', 'name', 'job_type', 'description',
            'spectra', 'spectra_ids',
            'agent_name', 'agent_version',
            'parameters', 'results',
            'status', 'progress', 'error_message',
            'execution_time', 'memory_usage',
            'created_at', 'started_at', 'completed_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'spectra', 'results',
            'status', 'progress', 'error_message',
            'execution_time', 'memory_usage',
            'created_at', 'started_at', 'completed_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        spectra_ids = validated_data.pop('spectra_ids', [])
        job = AnalysisJob.objects.create(**validated_data)
        
        # Add spectra to the job
        if spectra_ids:
            spectra = NIRSpectrum.objects.filter(id__in=spectra_ids)
            job.spectra.set(spectra)
        
        return job


class AnalysisJobUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating Analysis Job (limited fields)"""
    
    class Meta:
        model = AnalysisJob
        fields = ['status', 'progress', 'error_message', 'results']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class AgentSerializer(serializers.ModelSerializer):
    """Serializer for Agent"""
    
    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'display_name', 'description', 'version',
            'agent_file', 'capabilities', 'supported_formats',
            'parameters_schema', 'dependencies',
            'status', 'last_error',
            'average_execution_time', 'success_rate',
            'total_executions', 'successful_executions',
            'author', 'license', 'documentation',
            'created_at', 'updated_at', 'last_executed'
        ]
        read_only_fields = [
            'id', 'average_execution_time', 'success_rate',
            'total_executions', 'successful_executions',
            'created_at', 'updated_at', 'last_executed'
        ]


class AgentStatusSerializer(serializers.ModelSerializer):
    """Serializer for updating Agent status"""
    
    class Meta:
        model = Agent
        fields = ['status', 'last_error']


class SystemLogSerializer(serializers.ModelSerializer):
    """Serializer for System Log"""
    
    user = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = SystemLog
        fields = [
            'id', 'user', 'level', 'message',
            'module', 'function', 'context', 'stack_trace',
            'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class UserPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for User Preferences"""
    
    user = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = UserPreference
        fields = [
            'id', 'user', 'theme', 'language', 'timezone',
            'email_notifications', 'job_completion_notifications', 'error_notifications',
            'default_agent', 'auto_process_uploads',
            'max_storage_usage', 'auto_cleanup_old_files', 'retention_days',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class HealthCheckSerializer(serializers.Serializer):
    """Serializer for health check response"""
    
    status = serializers.CharField()
    version = serializers.CharField()
    timestamp = serializers.DateTimeField()
    agents_loaded = serializers.IntegerField()
    database_status = serializers.CharField()
    storage_status = serializers.CharField()
    system_info = serializers.DictField()


class SpectrumAnalysisSerializer(serializers.Serializer):
    """Serializer for spectrum analysis results"""
    
    spectrum_id = serializers.UUIDField()
    analysis_type = serializers.CharField()
    results = serializers.DictField()
    peaks = serializers.ListField(child=serializers.DictField())
    statistics = serializers.DictField()
    quality_metrics = serializers.DictField()
    execution_time = serializers.FloatField()
    timestamp = serializers.DateTimeField()


class JobExecutionSerializer(serializers.Serializer):
    """Serializer for job execution requests"""
    
    job_id = serializers.UUIDField(required=False)
    agent_name = serializers.CharField()
    spectrum_ids = serializers.ListField(child=serializers.UUIDField())
    parameters = serializers.DictField(default=dict)
    priority = serializers.IntegerField(default=0)


class GenericFileSerializer(serializers.ModelSerializer):
    """Serializer for GenericFile model"""
    
    class Meta:
        model = GenericFile
        fields = [
            'id', 'user', 'name', 'original_filename', 'description',
            'file', 'thumbnail', 'preview_file',
            'file_size', 'file_extension', 'mime_type', 'file_category',
            'content_metadata',
            'num_rows', 'num_columns', 'column_names', 'data_types',
            'num_lines', 'num_words', 'num_characters',
            'image_width', 'image_height', 'image_channels', 'image_format',
            'audio_duration', 'audio_sample_rate', 'audio_channels', 'audio_bit_rate',
            'video_duration', 'video_resolution', 'video_frame_rate', 'video_codec',
            'archive_contents', 'archive_num_files',
            'md5_hash', 'sha1_hash', 'sha256_hash',
            'quality_score', 'quality_grade', 'quality_issues',
            'processing_status', 'processing_results', 'analysis_results', 'recommendations',
            'processed_by_agent', 'agent_version', 'processing_parameters',
            'tags', 'custom_metadata',
            'spectral_data',
            'is_valid', 'is_processed', 'is_analyzed',
            'created_at', 'updated_at', 'processed_at', 'analyzed_at'
        ]
        read_only_fields = [
            'id', 'user', 'file_size', 'file_extension', 'mime_type',
            'content_metadata', 'md5_hash', 'sha1_hash', 'sha256_hash',
            'quality_score', 'quality_grade', 'quality_issues',
            'processing_status', 'processing_results', 'analysis_results', 'recommendations',
            'processed_by_agent', 'agent_version', 'processing_parameters',
            'is_valid', 'is_processed', 'is_analyzed',
            'created_at', 'updated_at', 'processed_at', 'analyzed_at'
        ]
    
    def get_file_url(self, obj):
        """Get the URL for the file"""
        if obj.file:
            return self.context['request'].build_absolute_uri(obj.file.url)
        return None
    
    def get_thumbnail_url(self, obj):
        """Get the URL for the thumbnail"""
        if obj.thumbnail:
            return self.context['request'].build_absolute_uri(obj.thumbnail.url)
        return None
    
    def get_preview_url(self, obj):
        """Get the URL for the preview file"""
        if obj.preview_file:
            return self.context['request'].build_absolute_uri(obj.preview_file.url)
        return None


class GenericFileUploadSerializer(serializers.Serializer):
    """Serializer for file upload requests"""
    
    files = serializers.ListField(
        child=serializers.FileField(),  # File size validation handled in view
        required=True
    )
    file_name = serializers.CharField(required=False, allow_blank=True)
    file_category = serializers.CharField(required=False, default='auto')
    description = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.CharField(required=False, allow_blank=True)
    metadata_author = serializers.CharField(required=False, allow_blank=True)
    metadata_date = serializers.DateField(required=False)
    metadata_source = serializers.CharField(required=False, allow_blank=True)
    auto_analyze = serializers.BooleanField(required=False, default=True)


class GenericFileListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for file lists"""
    
    file_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    
    class Meta:
        model = GenericFile
        fields = [
            'id', 'name', 'original_filename', 'description',
            'file_size', 'file_extension', 'mime_type', 'file_category',
            'quality_score', 'quality_grade',
            'processing_status', 'is_valid', 'is_processed', 'is_analyzed',
            'tags', 'created_at', 'updated_at',
            'file_url', 'thumbnail_url', 'preview_url'
        ]
        read_only_fields = fields
    
    def get_file_url(self, obj):
        if obj.file and hasattr(self, 'context') and 'request' in self.context:
            return self.context['request'].build_absolute_uri(obj.file.url)
        return None
    
    def get_thumbnail_url(self, obj):
        if obj.thumbnail and hasattr(self, 'context') and 'request' in self.context:
            return self.context['request'].build_absolute_uri(obj.thumbnail.url)
        return None
    
    def get_preview_url(self, obj):
        if obj.preview_file and hasattr(self, 'context') and 'request' in self.context:
            return self.context['request'].build_absolute_uri(obj.preview_file.url)
        return None