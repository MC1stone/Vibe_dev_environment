"""
URL configuration for NIR_Mistral Web Application
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenRefreshView
from api.views import CustomTokenObtainPairView
from api.views import (
    AgentListView, AgentDetailView, AgentExecuteView,
    SpectrumListCreateView, SpectrumRetrieveView,
    AnalysisJobListCreateView, AnalysisJobRetrieveView,
    UserRegistrationView, UserProfileView,
    DashboardView, HealthCheckView,
    CustomLoginView, CustomRegisterView, CustomLogoutView,
    FlowerAIAuthView, ILIASAuthView, FederatedLearningView
)
from api.nir_test_views import (
    nir_test_info, nir_test_demo, nir_test_run,
    nir_test_files, nir_test_report, nir_test_setup, nir_test_clean
)
from api.quarto_views import (
    generate_spectral_report, generate_metadata_report,
    get_report_templates, check_quarto_status,
    serve_report, generate_report_from_analysis, render_custom_report
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Authentication
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API Endpoints
    path('api/agents/', AgentListView.as_view(), name='agent-list'),
    path('api/agents/<str:agent_name>/', AgentDetailView.as_view(), name='agent-detail'),
    path('api/agents/<str:agent_name>/execute/', AgentExecuteView.as_view(), name='agent-execute'),
    
    # Spectrum Management
    path('api/spectra/', SpectrumListCreateView.as_view(), name='spectrum-list'),
    path('api/spectra/<uuid:pk>/', SpectrumRetrieveView.as_view(), name='spectrum-detail'),
    
    # Analysis Jobs
    path('api/jobs/', AnalysisJobListCreateView.as_view(), name='job-list'),
    path('api/jobs/<uuid:pk>/', AnalysisJobRetrieveView.as_view(), name='job-detail'),
    
    # Generic File Management
    path('api/files/', include('api.file_urls')),
    
    # User Management
    path('api/users/register/', UserRegistrationView.as_view(), name='user-register'),
    path('api/users/profile/', UserProfileView.as_view(), name='user-profile'),
    
    # Authentication Views (Traditional Django)
    path('login/', CustomLoginView.as_view(), name='login'),
    path('register/', CustomRegisterView.as_view(), name='register'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    
    # FlowerAI and ILIAS Integration API
    path('api/auth/flowerai/', FlowerAIAuthView.as_view(), name='flowerai-auth'),
    path('api/auth/ilias/', ILIASAuthView.as_view(), name='ilias-auth'),
    path('api/auth/federated/', FederatedLearningView.as_view(), name='federated-learning-auth'),
    
    # System
    path('api/health/', HealthCheckView.as_view(), name='health-check'),
    path('health/', HealthCheckView.as_view(), name='health-check-root'),
    
    # NIR_TEST Environment Integration
    path('api/nir-test/info/', nir_test_info, name='nir-test-info'),
    path('api/nir-test/demo/', nir_test_demo, name='nir-test-demo'),
    path('api/nir-test/run/<str:test_name>/', nir_test_run, name='nir-test-run'),
    path('api/nir-test/files/', nir_test_files, name='nir-test-files'),
    path('api/nir-test/report/', nir_test_report, name='nir-test-report'),
    path('api/nir-test/setup/', nir_test_setup, name='nir-test-setup'),
    path('api/nir-test/clean/', nir_test_clean, name='nir-test-clean'),
    
    # Main Entry Point
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('dashboard/', TemplateView.as_view(template_name='dashboard_colorful.html'), name='dashboard'),
    path('agents/', TemplateView.as_view(template_name='agents.html'), name='agents-page'),
    path('spectra/', TemplateView.as_view(template_name='spectra.html'), name='spectra-page'),
    path('files/', TemplateView.as_view(template_name='files.html'), name='files-page'),
    path('analysis/', TemplateView.as_view(template_name='analysis.html'), name='analysis-page'),
    path('jobs/', TemplateView.as_view(template_name='jobs.html'), name='jobs-page'),
    path('settings/', TemplateView.as_view(template_name='settings.html'), name='settings-page'),
    path('documentation/', TemplateView.as_view(template_name='documentation.html'), name='documentation-page'),
    
    # Port Management API (must come before general api/ pattern)
    path('api/ports/', include('port_manager.urls')),
    
    # Crew AI API
    path('api/crewai/', include('api.crewai_urls')),
    
    # Quarto Report API
    path('api/reports/generate/spectral/', generate_spectral_report, name='generate-spectral-report'),
    path('api/reports/generate/metadata/', generate_metadata_report, name='generate-metadata-report'),
    path('api/reports/generate/analysis/<str:analysis_id>/', generate_report_from_analysis, name='generate-report-from-analysis'),
    path('api/reports/generate/custom/', render_custom_report, name='render-custom-report'),
    path('api/reports/templates/', get_report_templates, name='get-report-templates'),
    path('api/reports/status/', check_quarto_status, name='check-quarto-status'),
    path('api/reports/<str:report_name>/', serve_report, name='serve-report'),
    
    # API root
    path('api/', TemplateView.as_view(template_name='api_docs.html'), name='api-docs'),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Catch-all for React/Vue frontend (if used) - exclude API paths
# urlpatterns += [
#     re_path(r'^(?!api/|admin/|static/|media/).*', TemplateView.as_view(template_name='index.html')),
# ]