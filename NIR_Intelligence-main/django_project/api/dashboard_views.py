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

class IntroSpectroscopyView(TemplateView):
    """OP72: Einfuehrungs-Seite 'Wie messe ich richtig Spektroskopie?' -
    unter Start erreichbar. Erklaert Grundprinzip, Lichtverhaeltnisse,
    Schwarz/Weiss-Abgleich und Metadaten fuer Einsteiger; nutzt die
    Sensor-Datenbank (registrierte Adapter + Setting-Katalog, OP29) und
    den Referenz-Vertrag der Fusion (OP68, >= 50 Wiederholungen)."""

    template_name = 'intro_spectroscopy.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())
        sensors = []
        setting_options = []
        try:
            from agents.sensor_agent import SensorAgent
            output = SensorAgent().execute({'operation': 'collect',
                                            'user_id': request.user.id})
            data = output.data or {}
            for r in data.get('registered_sensors', []):
                caps = r.get('capabilities') or {}
                meta = caps.get('metadata') or {}
                sensors.append({
                    'name': (r.get('display_name')
                             or str(r.get('model_id', '')).replace('_', ' ')
                             .title()),
                    'detector': str(caps.get('detector_type', '')
                                    or ', '.join(meta.get('sensors', [])
                                                 or [])),
                    'channels': (meta.get('num_channels')
                                 or caps.get('channel_count') or '-'),
                    'range': (('-'.join(f'{v:.0f}'
                                        for v in caps['wavelength_range_nm'])
                               + ' nm')
                              if caps.get('wavelength_range_nm') else '-'),
                    'interface': caps.get('interface_type', '-') or '-',
                })
            setting_options = data.get('setting_options') or []
        except Exception:
            sensors = []
            setting_options = []
        checklist = [
            ('Beleuchtung festlegen: eingebaute Sensor-LED einschalten, '
             'Raum gleichmäßig beleuchten, direktes Sonnenlicht vermeiden.'),
            ('Schwarz-Referenz messen: Sensoröffnung abdecken, '
             'mindestens 50 Wiederholungen aufnehmen.'),
            ('Weiß-Referenz messen: weiße, matte Referenzfläche, '
             'gleiche Geometrie wie bei der Probe, mindestens 50 '
             'Wiederholungen.'),
            ('Referenzen deklarieren: reference_type (dark/white), '
             'n_repeats und reference_artifact in die Metadaten eintragen.'),
            ('Probe vorbereiten: sauber, unverletzt, Raumtemperatur; '
             'Proben-ID vergeben.'),
            ('Messung: gleicher Abstand und Winkel wie bei der Referenz; '
             'mehrere Wiederholungen je Probe (Replikate).'),
            ('Referenzwert bestimmen: z. B. Brix mit dem Refraktometer '
             'messen und notieren.'),
            ('Alles als Projekt hochladen — die Plattform prüft Metadaten '
             'und Qualität automatisch.'),
        ]
        context = {
            'page_title': 'Einführung Spektroskopie',
            'sensors': sensors,
            'setting_options': setting_options,
            'checklist': checklist,
        }
        return render(request, self.template_name, context)
