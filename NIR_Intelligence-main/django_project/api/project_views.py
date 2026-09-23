# NIR Intelligence Platform - Project workflow views (OP10)
# Project workflow: uploaded files open a new project (phase 1 'drafted');
# the ingest service turns them into usable datasets and shows a preparation
# report with quality assessment and improvement recommendations. The user
# adapts the data (re-upload / re-ingest) and releases the project; phase 2
# runs the full NIRAnalysisCrew with per-agent reports and generates the
# final comprehensive Quarto project report plus the overview page.
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

logger = logging.getLogger("API.ProjectViews")

try:
    from rest_framework import status
    from rest_framework.response import Response
    from rest_framework.views import APIView
    DRF_AVAILABLE = True
except ImportError:  # offline test mode without djangorestframework
    DRF_AVAILABLE = False

from core.models import AnalysisProject, GenericFile


def _get_project(project_id, user):
    try:
        return AnalysisProject.objects.get(id=project_id, user=user)
    except (AnalysisProject.DoesNotExist, ValueError):
        raise Http404('Project not found')


class ProjectListView(TemplateView):
    """List the user's analysis projects with phase and quality summary."""

    template_name = 'projects.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())
        projects = AnalysisProject.objects.filter(user=request.user)
        context = {
            'page_title': 'Analysis Projects',
            'projects': [p.get_summary() for p in projects],
        }
        return render(request, self.template_name, context)


class ProjectCreateView(APIView if DRF_AVAILABLE else object):
    """Create a new project for one or more uploaded files (upload = project)."""

    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': 'Authentication required'},
                            status=status.HTTP_401_UNAUTHORIZED)
        file_ids = request.data.get('file_ids', [])
        name = (request.data.get('name') or '').strip()
        if not file_ids:
            return Response({'success': False, 'error': 'file_ids required'},
                            status=status.HTTP_400_BAD_REQUEST)
        files = GenericFile.objects.filter(id__in=file_ids, user=request.user)
        if not files.exists():
            return Response({'success': False, 'error': 'No matching files'},
                            status=status.HTTP_404_NOT_FOUND)
        if not name:
            name = f"Projekt {files.first().name}"
        project = AnalysisProject.objects.create(user=request.user, name=name,
                                                 description=request.data.get('description', ''))
        project.files.set(files)
        from services.project_ingest import build_preparation_report
        build_preparation_report(project)
        return Response({
            'success': True,
            'project_id': str(project.id),
            'summary': project.get_summary(),
            'report_url': f'/projects/{project.id}/',
        })


class ProjectDetailView(TemplateView):
    """Phase 1 report (drafted) or phase 2 overview (released/completed).

    Drafted: datasets, metadata assessment, improvement recommendations,
    release button. Released/completed: per-agent crew reports, overall
    results, final Quarto report download.
    """

    template_name = 'project_report.html'

    def get(self, request, project_id):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())
        project = _get_project(project_id, request.user)
        preparation = project.preparation_report or {}
        crew_results = project.crew_results or {}
        context = {
            'page_title': f'Projekt: {project.name}',
            'project': project,
            'project_summary': project.get_summary(),
            'preparation': preparation,
            'datasets': preparation.get('datasets', []),
            'metadata_quality': preparation.get('metadata_quality', {}),
            'recommendations': preparation.get('recommendations', []),
            'crew_results': crew_results,
            'per_agent_reports': crew_results.get('per_agent_reports', []),
            'crew_analysis': crew_results.get('crew_analysis', {}),
            'final_report_path': project.final_report_path,
            'final_report_url': f'/projects/{project.id}/final-report/' if project.final_report_path else None,
        }
        return render(request, self.template_name, context)


class ProjectReingestView(APIView if DRF_AVAILABLE else object):
    """Re-run the phase 1 preparation after the user adapted the files."""

    def post(self, request, project_id):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': 'Authentication required'},
                            status=status.HTTP_401_UNAUTHORIZED)
        project = _get_project(project_id, request.user)
        from services.project_ingest import build_preparation_report
        report = build_preparation_report(project)
        return Response({
            'success': True,
            'usable_dataset_count': report.get('usable_dataset_count'),
            'total_dataset_count': report.get('total_dataset_count'),
            'recommendations': report.get('recommendations', []),
            'report_url': f'/projects/{project.id}/',
        })


class ProjectReleaseView(APIView if DRF_AVAILABLE else object):
    """Release the project for analysis: run the full crew with per-agent
    reports and generate the final comprehensive Quarto report."""

    def post(self, request, project_id):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': 'Authentication required'},
                            status=status.HTTP_401_UNAUTHORIZED)
        project = _get_project(project_id, request.user)
        if project.phase == 'drafted':
            preparation = project.preparation_report or {}
            if not preparation.get('usable_dataset_count'):
                return Response({
                    'success': False,
                    'error': 'No usable datasets',
                    'message': 'Mindestens ein verwertbarer Datensatz ist erforderlich, '
                               ' bevor die Analyse freigegeben werden kann.',
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            project.phase = 'released'
            project.released_at = datetime.now()
            project.save(update_fields=['phase', 'released_at', 'updated_at'])
        try:
            from services.project_crew import run_project_crew
            crew_results = run_project_crew(project)
        except Exception as e:
            logger.error(f'Error running project crew: {e}', exc_info=True)
            return Response({'success': False, 'error': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({
            'success': True,
            'project_id': str(project.id),
            'overall_quality_score': crew_results.get('overall_quality_score'),
            'per_agent_reports': crew_results.get('per_agent_reports', []),
            'final_report_url': f'/projects/{project.id}/final-report/' if project.final_report_path else None,
            'report_url': f'/projects/{project.id}/',
        })


class ProjectFinalReportView(TemplateView):
    """Serve the generated final Quarto (HTML) report file."""

    def get(self, request, project_id):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())
        project = _get_project(project_id, request.user)
        if not project.final_report_path or not os.path.exists(project.final_report_path):
            raise Http404('Final report not generated yet')
        with open(project.final_report_path, 'r', encoding='utf-8') as handle:
            return HttpResponse(handle.read(), content_type='text/html; charset=utf-8')
