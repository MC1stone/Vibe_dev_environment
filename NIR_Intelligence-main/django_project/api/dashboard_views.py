"""Start-page view (S1 of the workflow UI redesign).

Serves the real user state: their projects with phase/quality/file counts
and the true CrewAI availability. No fabricated statistics - scientific
integrity applies to dashboards exactly as it does to spectra.
"""

from django.shortcuts import redirect, render
from django.views.generic import TemplateView


class DashboardStartView(TemplateView):
    """Start page: real projects, real counts, honest system status."""

    template_name = 'dashboard_start.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())

        from core.models import AnalysisProject, NIRSpectrum
        projects = []
        for project in (AnalysisProject.objects
                        .filter(user=request.user)
                        .order_by('-updated_at')[:8]):
            summary = project.get_summary()
            summary['updated_at'] = project.updated_at
            projects.append(summary)

        try:
            from api.crewai_views import CREW_AVAILABLE
        except Exception:
            CREW_AVAILABLE = False

        context = {
            'page_title': 'Start',
            'projects': projects,
            'total_projects': AnalysisProject.objects
                .filter(user=request.user).count(),
            'total_spectra': NIRSpectrum.objects
                .filter(user=request.user).count(),
            'crew_available': bool(CREW_AVAILABLE),
        }
        return render(request, self.template_name, context)
