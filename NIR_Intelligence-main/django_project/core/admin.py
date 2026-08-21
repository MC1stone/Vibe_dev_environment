"""
Admin configuration for Core app
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, NIRSpectrum, AnalysisJob, Agent, SystemLog, UserPreference


class UserAdmin(BaseUserAdmin):
    """Custom admin for User model"""
    
    list_display = ['email', 'username', 'first_name', 'last_name', 'institution', 'is_active', 'is_verified']
    list_filter = ['is_active', 'is_verified', 'institution']
    search_fields = ['email', 'username', 'first_name', 'last_name', 'institution']
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'institution', 'department', 'position', 'phone')}),
        (_('Preferences'), {'fields': ('preferred_language', 'theme_preference')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'created_at', 'updated_at')}),
        (_('Status'), {'fields': ('is_verified',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )
    
    ordering = ['-created_at']


class NIRSpectrumAdmin(admin.ModelAdmin):
    """Admin for NIR Spectrum model"""
    
    list_display = ['name', 'user', 'sample_id', 'sample_type', 'spectral_type', 'data_format', 'status', 'created_at']
    list_filter = ['user', 'sample_type', 'spectral_type', 'data_format', 'status']
    search_fields = ['name', 'sample_id', 'sample_type', 'description']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('user', 'name', 'description')
        }),
        (_('Sample Information'), {
            'fields': ('sample_id', 'sample_type', 'sample_source')
        }),
        (_('Spectral Data'), {
            'fields': ('spectral_type', 'data_format', 'original_file', 'processed_file')
        }),
        (_('Metadata'), {
            'fields': ('wavelength_range_start', 'wavelength_range_end', 'resolution', 'data_points')
        }),
        (_('Collection Information'), {
            'fields': ('instrument', 'collection_date', 'collection_conditions')
        }),
        (_('Analysis Results'), {
            'fields': ('mean_absorbance', 'max_absorbance', 'min_absorbance', 'peaks_detected',
                     'signal_to_noise_ratio', 'baseline_corrected', 'quality_score')
        }),
        (_('Status'), {
            'fields': ('status', 'tags', 'categories')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'processed_at')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'processed_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


class AnalysisJobAdmin(admin.ModelAdmin):
    """Admin for Analysis Job model"""
    
    list_display = ['name', 'user', 'job_type', 'agent_name', 'status', 'progress', 'created_at']
    list_filter = ['user', 'job_type', 'status', 'agent_name']
    search_fields = ['name', 'description', 'agent_name']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('user', 'name', 'description', 'job_type')
        }),
        (_('Spectra'), {
            'fields': ('spectra',)
        }),
        (_('Agent Information'), {
            'fields': ('agent_name', 'agent_version')
        }),
        (_('Parameters'), {
            'fields': ('parameters',)
        }),
        (_('Results'), {
            'fields': ('results',)
        }),
        (_('Status'), {
            'fields': ('status', 'progress', 'error_message')
        }),
        (_('Performance'), {
            'fields': ('execution_time', 'memory_usage')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'started_at', 'completed_at', 'updated_at')
        }),
    )
    
    readonly_fields = ['created_at', 'started_at', 'completed_at', 'updated_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


class AgentAdmin(admin.ModelAdmin):
    """Admin for Agent model"""
    
    list_display = ['display_name', 'name', 'version', 'status', 'success_rate', 'total_executions']
    list_filter = ['status', 'capabilities']
    search_fields = ['name', 'display_name', 'description', 'author']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'display_name', 'description', 'version')
        }),
        (_('Agent File'), {
            'fields': ('agent_file',)
        }),
        (_('Capabilities'), {
            'fields': ('capabilities', 'supported_formats', 'parameters_schema')
        }),
        (_('Dependencies'), {
            'fields': ('dependencies',)
        }),
        (_('Status'), {
            'fields': ('status', 'last_error')
        }),
        (_('Performance'), {
            'fields': ('average_execution_time', 'success_rate', 'total_executions', 'successful_executions')
        }),
        (_('Metadata'), {
            'fields': ('author', 'license', 'documentation')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'last_executed')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_executed']


class SystemLogAdmin(admin.ModelAdmin):
    """Admin for System Log model"""
    
    list_display = ['timestamp', 'level', 'module', 'function', 'user', 'message']
    list_filter = ['level', 'module', 'function', 'timestamp']
    search_fields = ['message', 'module', 'function']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('level', 'message')
        }),
        (_('Context'), {
            'fields': ('user', 'module', 'function')
        }),
        (_('Additional Information'), {
            'fields': ('context', 'stack_trace')
        }),
        (_('Timestamps'), {
            'fields': ('timestamp',)
        }),
    )
    
    readonly_fields = ['timestamp']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


class UserPreferenceAdmin(admin.ModelAdmin):
    """Admin for User Preference model"""
    
    list_display = ['user', 'theme', 'language', 'timezone']
    list_filter = ['theme', 'language']
    search_fields = ['user__email', 'user__username']
    
    fieldsets = (
        (_('User'), {
            'fields': ('user',)
        }),
        (_('Display Preferences'), {
            'fields': ('theme', 'language', 'timezone')
        }),
        (_('Notification Preferences'), {
            'fields': ('email_notifications', 'job_completion_notifications', 'error_notifications')
        }),
        (_('Analysis Preferences'), {
            'fields': ('default_agent', 'auto_process_uploads')
        }),
        (_('Storage Preferences'), {
            'fields': ('max_storage_usage', 'auto_cleanup_old_files', 'retention_days')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


# Register models
admin.site.register(User, UserAdmin)
admin.site.register(NIRSpectrum, NIRSpectrumAdmin)
admin.site.register(AnalysisJob, AnalysisJobAdmin)
admin.site.register(Agent, AgentAdmin)
admin.site.register(SystemLog, SystemLogAdmin)
admin.site.register(UserPreference, UserPreferenceAdmin)