# NIR Intelligence Platform - Workflow URLs
# URL routing for workflow API endpoints

from django.urls import path
from . import workflow_views

urlpatterns = [
    # Workflow execution endpoints
    path('workflows/start/', workflow_views.start_workflow, name='start_workflow'),
    path('workflows/upload-and-analyze/', workflow_views.upload_and_analyze, name='upload_and_analyze'),
    
    # Workflow status and management
    path('workflows/status/<str:workflow_id>/', workflow_views.get_workflow_status, name='get_workflow_status'),
    path('workflows/summary/<str:workflow_id>/', workflow_views.get_workflow_summary, name='get_workflow_summary'),
    path('workflows/all/', workflow_views.get_all_workflows, name='get_all_workflows'),
    path('workflows/cleanup/<str:workflow_id>/', workflow_views.cleanup_workflow, name='cleanup_workflow'),
    
    # Report management
    path('reports/list/', workflow_views.list_reports, name='list_reports'),
    path('reports/<str:report_filename>/', workflow_views.get_report, name='get_report'),
    
    # Convenience endpoints
    path('workflows/standard/', lambda request: workflow_views.start_workflow(request), {
        'workflow_type': 'standard_analysis'
    }, name='start_standard_workflow'),
    
    path('workflows/comprehensive/', lambda request: workflow_views.start_workflow(request), {
        'workflow_type': 'comprehensive_analysis'
    }, name='start_comprehensive_workflow'),
    
    path('workflows/quick/', lambda request: workflow_views.start_workflow(request), {
        'workflow_type': 'quick_analysis'
    }, name='start_quick_workflow'),
]