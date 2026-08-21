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
    MultipleFileAnalyzeView,
    FileCategoryView,
    FileStatisticsView
)

urlpatterns = [
    # File listing and details
    path('files/', FileListView.as_view(), name='file-list'),
    path('files/<uuid:file_id>/', FileDetailView.as_view(), name='file-detail'),
    
    # File upload
    path('files/upload/', FileUploadView.as_view(), name='file-upload'),
    
    # File deletion
    path('files/<uuid:file_id>/delete/', FileDeleteView.as_view(), name='file-delete'),
    path('files/delete-multiple/', MultipleFileDeleteView.as_view(), name='file-delete-multiple'),
    
    # File download
    path('files/<uuid:file_id>/download/', FileDownloadView.as_view(), name='file-download'),
    
    # File analysis
    path('files/<uuid:file_id>/analyze/', FileAnalyzeView.as_view(), name='file-analyze'),
    path('files/analyze-multiple/', MultipleFileAnalyzeView.as_view(), name='file-analyze-multiple'),
    
    # File categories and statistics
    path('files/categories/', FileCategoryView.as_view(), name='file-categories'),
    path('files/statistics/', FileStatisticsView.as_view(), name='file-statistics'),
]