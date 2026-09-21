"""
URLs for Generic File Management API
"""

from django.urls import path
from .file_views import (
    FileListView,
    FileDetailView,
    FileUploadView,
    FileDeleteView,
    MultipleFileDeleteView,
    FileDownloadView,
    FileAnalyzeView,
    FileCrewAnalysisView,
    MultipleFileAnalyzeView,
    FileCategoryView,
    FileStatisticsView
)

urlpatterns = [
    # File listing and details
    path('', FileListView.as_view(), name='file-list'),
    path('<uuid:file_id>/', FileDetailView.as_view(), name='file-detail'),
    
    # File upload
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    
    # File deletion
    path('<uuid:file_id>/delete/', FileDeleteView.as_view(), name='file-delete'),
    path('delete-multiple/', MultipleFileDeleteView.as_view(), name='file-delete-multiple'),
    
    # File download
    path('<uuid:file_id>/download/', FileDownloadView.as_view(), name='file-download'),
    
    # File analysis
    path('<uuid:file_id>/analyze/', FileAnalyzeView.as_view(), name='file-analyze'),
    path('<uuid:file_id>/crew-analysis/', FileCrewAnalysisView.as_view(), name='file-crew-analysis'),
    path('analyze-multiple/', MultipleFileAnalyzeView.as_view(), name='file-analyze-multiple'),
    
    # File categories and statistics
    path('categories/', FileCategoryView.as_view(), name='file-categories'),
    path('statistics/', FileStatisticsView.as_view(), name='file-statistics'),
]