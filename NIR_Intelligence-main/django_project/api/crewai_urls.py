# NIR Intelligence Platform - Crew AI API URLs
# URL routing for Crew AI endpoints

from django.urls import path
from .crewai_views import (
    start_analysis,
    get_analysis_status,
    get_analysis_history,
    get_report_preview,
    batch_analysis,
    get_crew_status,
    cleanup_resources,
    get_report_list,
    federated_learning_contribution,
    # Legacy endpoints
    crewai_analysis,
    crewai_status,
    crewai_history
)

urlpatterns = [
    # Main Crew AI endpoints
    path('analysis/start/', start_analysis, name='crewai_start_analysis'),
    path('analysis/status/', get_analysis_status, name='crewai_analysis_status'),
    path('analysis/history/', get_analysis_history, name='crewai_analysis_history'),
    path('analysis/batch/', batch_analysis, name='crewai_batch_analysis'),
    
    # Report endpoints
    path('reports/preview/', get_report_preview, name='crewai_report_preview'),
    path('reports/list/', get_report_list, name='crewai_report_list'),
    
    # System endpoints
    path('status/', get_crew_status, name='crewai_status'),
    path('cleanup/', cleanup_resources, name='crewai_cleanup'),
    
    # Federated learning endpoints
    path('federated/contribute/', federated_learning_contribution, name='crewai_federated_contribute'),
    
    # Legacy endpoints (for backward compatibility)
    path('analysis/', crewai_analysis, name='crewai_analysis_legacy'),
    path('history/', crewai_history, name='crewai_history_legacy'),
]

# URL patterns for including in main urls.py
from django.urls import include

crewai_api_urls = [
    path('api/crewai/', include(urlpatterns)),
]

# For direct inclusion
crewai_urls = urlpatterns