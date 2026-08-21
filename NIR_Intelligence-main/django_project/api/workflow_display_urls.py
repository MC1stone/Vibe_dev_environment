# NIR Intelligence Platform - Workflow Display URLs
# URL routing for workflow display views

from django.urls import path
from . import workflow_display_views

urlpatterns = [
    # Dashboard and overview
    path('dashboard/', workflow_display_views.dashboard_view, name='dashboard'),
    path('', workflow_display_views.dashboard_view, name='home'),
    
    # Workflow display views
    path('workflows/', workflow_display_views.workflow_list_view, name='workflow_list'),
    path('workflows/<str:workflow_id>/', workflow_display_views.workflow_results_view, name='workflow_results'),
    path('workflows/<str:workflow_id>/details/', workflow_display_views.workflow_detail_view, name='workflow_details'),
    
    # File upload
    path('upload/', workflow_display_views.upload_view, name='upload_files'),
    
    # Report viewing
    path('reports/<str:report_filename>/', workflow_display_views.workflow_results_view, name='view_report'),
]