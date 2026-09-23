"""URLs for the OP10 project workflow (upload -> project -> crew -> Quarto)."""
from django.urls import path
from .project_views import (
    ProjectListView,
    ProjectCreateView,
    ProjectDetailView,
    ProjectReingestView,
    ProjectMetadataView,
    ProjectReleaseView,
    ProjectFinalReportView,
    SpectrumDatabaseView,
    SpectrumDatabaseDetailView,
)

urlpatterns = [
    path('', ProjectListView.as_view(), name='project-list'),
    path('create/', ProjectCreateView.as_view(), name='project-create'),
    path('<uuid:project_id>/', ProjectDetailView.as_view(), name='project-detail'),
    path('<uuid:project_id>/reingest/', ProjectReingestView.as_view(), name='project-reingest'),
    path('<uuid:project_id>/metadata/', ProjectMetadataView.as_view(), name='project-metadata'),
    path('<uuid:project_id>/release/', ProjectReleaseView.as_view(), name='project-release'),
    path('<uuid:project_id>/final-report/', ProjectFinalReportView.as_view(), name='project-final-report'),
    path('database/', SpectrumDatabaseView.as_view(), name='spectrum-database'),
    path('database/<uuid:spectrum_id>/', SpectrumDatabaseDetailView.as_view(), name='spectrum-detail'),
]
