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
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

logger = logging.getLogger("API.ProjectViews")

try:
    from rest_framework import status
    from rest_framework.response import Response
    from rest_framework.views import APIView
    DRF_AVAILABLE = True
except ImportError:  # offline test mode without djangorestframework
    DRF_AVAILABLE = False

from core.models import AnalysisProject, GenericFile, SensorDocument
from django.utils.translation import gettext


class SpectrumDatabaseView(TemplateView):
    """Browse the local spectral database (OP15): all spectra visible to the
    user (own records plus lab-shared ones) with provenance and a link to the
    source project. The FAISS similarity section of released projects
    compares against exactly this set (same wavelength grid only)."""

    template_name = 'spectrum_database.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())
        from services.spectrum_database import visible_records
        records = visible_records(request.user)
        spectra = []
        for record in records:
            summary = record.get_summary()
            summary['is_own'] = record.user_id == request.user.id
            summary['is_shared'] = record.visibility == 'lab_shared'
            spectra.append(summary)
        context = {
            'page_title': 'Spektrendatenbank',
            'spectra': spectra,
            'total_count': len(spectra),
        }
        return render(request, self.template_name, context)


class ReferenceImportView(View):
    """Import external reference spectra into the spectral database (M3 UI).

    POST with multipart: file (CSV/JDX/SPC... via the format-agnostic loader),
    source, license, version (all mandatory - the license gate rejects
    entries without provenance), optional sample_type. Creates one
    SpectrumRecord per spectrum in the file, visible lab-wide, normalised
    to nm, and redirects back to the database page with a summary."""

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())
        return redirect('/projects/database/')

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())
        from django.contrib import messages
        from services.spectrum_curve import extract_curve
        from services.reference_import import (
            import_reference_dataset, LicenseViolationError,
        )
        from core.models import SpectrumRecord

        uploaded = request.FILES.get('reference_file')
        source = (request.POST.get('source') or '').strip()
        license_name = (request.POST.get('license') or '').strip()
        version = (request.POST.get('version') or '').strip()
        sample_type = (request.POST.get('sample_type') or '').strip()

        if uploaded is None or not source or not license_name or not version:
            messages.error(request, gettext(
                'Bitte Datei, Quelle, Lizenz und Version angeben - Referenz-'
                'Import ohne Herkunft wird abgelehnt (Lizenz-Gate).'))
            return redirect('/projects/database/')

        import tempfile
        import os
        from django.conf import settings as dj_settings
        tmp_dir = os.path.join(dj_settings.MEDIA_ROOT, 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile(
                dir=tmp_dir, delete=False,
                suffix=os.path.splitext(uploaded.name)[1] or '.dat') as tmp:
            for chunk in uploaded.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        try:
            curve = extract_curve(tmp_path)
            if curve is None:
                messages.error(request, gettext(
                    'In der Datei konnte kein Spektrum erkannt werden '
                    '(unterstützt: CSV, JCAMP-DX, SPC, MATLAB, HDF5, TXT).'))
                return redirect('/projects/database/')
            entry = {
                'file_name': uploaded.name,
                'wavelengths': curve['wavelengths'],
                'intensities': curve['intensities'],
                'x_unit': curve['x_unit'],
                'metadata': {
                    'source': source,
                    'license': license_name,
                    'version': version,
                    'sample_type': sample_type,
                    'instrument': 'reference import',
                    'y_unit': curve['y_unit'],
                },
            }
            summary = import_reference_dataset(
                [entry], user=request.user, visibility='lab_shared')
            if summary['imported'] > 0:
                messages.success(request, gettext(
                    'Referenzspektrum importiert: ') + uploaded.name +
                    ' (' + curve['x_unit'] + ', ' +
                    str(len(curve['wavelengths'])) + ' Punkte). Quelle: ' +
                    source + ' · ' + license_name)
            else:
                reasons = '; '.join(summary.get('rejections') or
                                     ['unbekannter Fehler'])
                messages.error(request, gettext(
                    'Import abgelehnt: ') + reasons)
        except LicenseViolationError as e:
            messages.error(request, str(e))
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        return redirect('/projects/database/')


class SpectrumDatabaseDetailView(TemplateView):
    """One database spectrum: preview table plus the most similar visible
    spectra on the same wavelength grid (FAISS, top-k)."""

    template_name = 'spectrum_detail.html'

    def get(self, request, spectrum_id):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())
        from services.spectrum_database import visible_records
        records = visible_records(request.user)
        try:
            record = records.get(id=spectrum_id)
        except Exception:
            raise Http404('Spectrum not found')
        matches = []
        others = records.filter(wavelength_grid=record.wavelength_grid) \
                        .exclude(id=record.id)
        if others.exists():
            try:
                from agents.faiss_agent import FaissAgent
                references = [{
                    'data': {'wavelength': o.wavelengths,
                             'intensity': o.intensities},
                    'wavelength_column': 'wavelength',
                    'intensity_column': 'intensity',
                } for o in others]
                ids = [o.file_name or str(o.id) for o in others]
                output = FaissAgent().execute({
                    'reference_spectra': references,
                    'reference_ids': ids,
                    'query_spectrum': {
                        'data': {'wavelength': record.wavelengths,
                                 'intensity': record.intensities},
                        'wavelength_column': 'wavelength',
                        'intensity_column': 'intensity',
                    },
                    'top_k': 5,
                })
                matches = output.data.get('matches', []) if output else []
            except Exception:
                logger.exception('Similarity search failed (non-fatal)')
        chart = ''
        try:
            from services.project_report import single_spectrum_chart_data_url
            chart = single_spectrum_chart_data_url(
                record.wavelengths, record.intensities,
                title=f'Spektrum: {record.file_name}')
        except Exception:
            logger.exception('Spectrum chart rendering failed (non-fatal)')
        context = {
            'page_title': f'Spektrum {record.file_name}',
            'spectrum': record.get_summary(),
            'series': list(zip(record.wavelengths, record.intensities)),
            'matches': matches,
            'metadata': record.metadata or {},
            'chart': chart,
        }
        return render(request, self.template_name, context)


class SensorListView(TemplateView):
    """Sensor catalog overview (OP29): all sensors known to the platform -
    registered adapters with capabilities, the setting options the platform
    understands and the usage recorded in the existing database. The
    optimization suggestions from the crew analyses are listed per sensor."""

    template_name = 'sensor_list.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())
        from agents.sensor_agent import SensorAgent
        output = SensorAgent().execute({
            'operation': 'collect',
            'user_id': request.user.id,
        })
        data = output.data or {}
        context = {
            'page_title': 'Sensoren',
            'registered_sensors': data.get('registered_sensors', []),
            'setting_options': data.get('setting_options', []),
            'usage': data.get('usage', []),
            'unmatched_usage': data.get('unmatched_usage', []),
            'suggestions': data.get('optimization_suggestions', []),
        }
        return render(request, self.template_name, context)


class SensorDetailView(TemplateView):
    """One sensor (OP29 + OP53): the single KI-supported information page
    for a sensor. Everything the platform knows about it on one page:
    adapter profile, recorded usage from the existing database, setting
    values with completeness/plausibility assessment, optimization
    suggestions, the uploaded sensor documents (database extension) and
    a live KI-generated summary (local Ollama; honest fallback when
    unavailable)."""
    template_name = 'sensor_detail.html'

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, sensor_key):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())
        from urllib.parse import unquote

        from agents.sensor_agent import SensorAgent
        from services.sensor_catalog import assess_settings, match_model_id
        from services.sensor_documents import (DOC_TYPES, document_stats,
                                               sensor_documents)
        output = SensorAgent().execute({
            'operation': 'collect',
            'user_id': request.user.id,
        })
        data = output.data or {}
        name = unquote(sensor_key)
        model_id = match_model_id(name)
        sensor = next((s for s in data.get('registered_sensors', [])
                       if s['model_id'] == (model_id or name)), None)
        usage = next((u for u in data.get('usage', [])
                      if u['instrument_type'] == name
                      or (model_id and u['model_id'] == model_id)), None)
        documents = list(sensor_documents(name, request.user))
        if sensor is None and usage is None and not documents:
            raise Http404('Sensor not found')
        recorded = (usage or {}).get('recorded_settings') or {}
        assessment = assess_settings(
            {key: (values[-1] if isinstance(values, list) and values else values)
             for key, values in recorded.items()},
            setting_options=data.get('setting_options', []))
        suggestions = data.get('optimization_suggestions', [])
        context = {
            'page_title': f'Sensor {name}',
            'sensor': sensor,
            'sensor_name': name,
            'model_id': model_id,
            'usage': usage,
            'assessment': assessment,
            'setting_options': data.get('setting_options', []),
            'suggestions': suggestions,
            'documents': documents,
            'document_stats': document_stats(documents),
            'doc_types': DOC_TYPES,
        }
        return render(request, self.template_name, context)


class SensorSummaryView(APIView if DRF_AVAILABLE else object):
    """KI overview for one sensor (OP53b): generated live on request so
    the sensor page itself renders instantly even while Ollama is slow
    (model cold start); the page fetches this endpoint asynchronously."""

    def get(self, request, sensor_key):
        if not request.user.is_authenticated:
            return Response({'success': False,
                             'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        from urllib.parse import unquote

        from agents.sensor_agent import SensorAgent
        from services.sensor_catalog import match_model_id
        from services.sensor_documents import sensor_documents
        name = unquote(sensor_key)
        output = SensorAgent().execute({
            'operation': 'collect',
            'user_id': request.user.id,
        })
        data = output.data or {}
        model_id = match_model_id(name)
        sensor = next((s for s in data.get('registered_sensors', [])
                       if s['model_id'] == (model_id or name)), None)
        usage = next((u for u in data.get('usage', [])
                      if u['instrument_type'] == name
                      or (model_id and u['model_id'] == model_id)), None)
        documents = [d.get_summary()
                     for d in sensor_documents(name, request.user)]
        description = None
        if name.startswith('diy_'):
            project = DiyDetailView.get_project(name[len('diy_'):])
            description = project['description'] if project else None
        from services.sensor_summary import SensorSummaryService
        summary = SensorSummaryService().summarize(name, {
            'sensor': sensor,
            'usage': usage,
            'description': description,
            'documents': documents,
            'suggestions': data.get('optimization_suggestions', []),
        })
        if summary is None:
            return Response({
                'success': True,
                'available': False,
                'summary': None,
            })
        return Response({
            'success': True,
            'available': True,
            'summary': summary,
        })


class SensorDocumentUploadView(APIView if DRF_AVAILABLE else object):
    """Upload one or more documents for a sensor (OP53): extends the
    sensor database. Any information type is allowed (datasheet, manual,
    calibration, photo, software, publication, other)."""

    @method_decorator(ensure_csrf_cookie)
    def post(self, request, sensor_key):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        from urllib.parse import unquote

        name = unquote(sensor_key)
        files = request.FILES.getlist('files') or request.FILES.getlist('file')
        if not files:
            return Response({'success': False, 'error': gettext('No file provided')},
                            status=status.HTTP_400_BAD_REQUEST)
        doc_type = str(request.data.get('doc_type') or 'other')
        notes = str(request.data.get('notes') or '').strip()
        visibility = str(request.data.get('visibility') or 'lab_shared')
        if visibility not in ('private', 'lab_shared'):
            visibility = 'lab_shared'
        created = []
        for upload in files:
            doc = SensorDocument.objects.create(
                user=request.user,
                sensor_key=name,
                file=upload,
                original_name=upload.name,
                doc_type=doc_type,
                notes=notes,
                visibility=visibility,
            )
            created.append(doc.get_summary())
        return Response({
            'success': True,
            'sensor': name,
            'uploaded': len(created),
            'documents': created,
            'sensor_url': f'/projects/sensors/{name}/',
        })


class SensorDocumentDeleteView(APIView if DRF_AVAILABLE else object):
    """Delete one of the user's own sensor documents (OP53)."""

    def post(self, request, document_id):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        try:
            doc = SensorDocument.objects.get(id=document_id, user=request.user)
        except SensorDocument.DoesNotExist:
            return Response({'success': False, 'error': gettext('Document not found')},
                            status=status.HTTP_404_NOT_FOUND)
        sensor_name = doc.sensor_key
        if doc.file:
            doc.file.delete(save=False)
        doc.delete()
        return Response({
            'success': True,
            'sensor': sensor_name,
            'sensor_url': f'/projects/sensors/{sensor_name}/',
        })


class DiySpectrometerView(TemplateView):
    """DIY spectrometer overview (OP49): curated list of documented DIY
    spectrometer projects with working links, plus the opt-in sensor websearch
    lookup via the local Ollama instance (disabled by default)."""
    template_name = 'sensor_diy.html'

    DIY_PROJECTS = [
        {
            'name': 'OpenSpectrometer',
            'slug': 'open-spectrometer',
            'status': gettext('Aktiv, STL-Dateien verfügbar'),
            'description': gettext(
                'Open-Source-Spektrometer (DIY-Free-Spectrometer, GPL-3.0): '
                'vollstaendig 3D-druckbares Gehaeuse, druckbar ohne '
                'Stuetzstrukturen. Beugungsgitter aus einer geoeffneten DVD '
                '(kein Blu-ray); Spalt durch eine aufgeklebte '
                'Objekttraeger-Glasplatte abgedeckt. Beleuchtung: weisse LED '
                'ca. 3 W, Umlenkung ueber einen Spiegelscherbe. Weitere Teile: '
                'USB-Kamera, 2x 3Mx10mm-Schrauben, Heisskleber. Auswertung mit '
                'der Desktop-Software Theremino Spectrometer; STL-Dateien auf '
                'Printables.'),
            'urls': [
                ('Printables', 'https://www.printables.com/model/848877-openspectrometer-v1'),
                ('GitHub', 'https://github.com/mlinmg/DIY-Free-Spectrometer'),
            ],
            'features': [
                'Vollständig 3D-druckbares Gehäuse',
                'CCD/CMOS-basierter Spektrometer-Aufbau',
                'Für wissenschaftliche Messungen ausgelegt',
                'Erweiterbar mit Raspberry Pi und eigener Software',
            ],
            'suited_for': [
                'Laborprojekte',
                'Umweltanalytik',
                'Spektralanalyse von LEDs, Lasern und Lichtquellen',
            ],
        },
        {
            'name': 'DIY Spectroscope (Thingiverse)',
            'slug': 'thingiverse-spectroscope',
            'status': gettext('Verfügbar, Dokumentation vorhanden'),
            'description': gettext(
                '3D-gedrucktes Spektroskop (Thingiverse-Modell 4729351): '
                '1000 Linien/mm Beugungsgitter, ~0,1 mm Spalt, Aufloesung '
                'unter 2 nm, kalibrierte Genauigkeit ca. 0,35 nm '
                'Standardabweichung. Als Sensor dient eine Webcam, DSLR oder '
                'Astro-Kamera. STL-Dateien auf Thingiverse (automatischer '
                'Zugriff wird dort blockiert, Details siehe Projektseite).'),
            'urls': [
                ('Thingiverse', 'https://www.thingiverse.com/thing:4729351'),
            ],
            'features': [
                '1000 Linien/mm Beugungsgitter',
                '~0,1 mm Spalt',
                'Auflösung unter 2 nm',
                'Kalibrierte Genauigkeit ca. 0,35 nm Standardabweichung',
                'Unterstützt Webcam, DSLR oder Astro-Kamera',
            ],
            'suited_for': [
                'Eines der leistungsstärksten Open-Source-Spektrometer',
            ],
        },
        {
            'name': 'Public Lab Desktop Spectrometer',
            'slug': 'public-lab-desktop',
            'status': gettext('Aktiv gepflegte Plattform'),
            'description': gettext(
                'Desktop Spectrometry Starter Kit 3.0 (DSSK) der Public Lab '
                'Community: Referenz-Design aus Pappe/Kartenmaterial, '
                'urspruenglich zur Oelrueckstands-Erkennung nach der '
                'BP-Oelkatastrophe entwickelt. Faehigkeiten: Spektren mit '
                'ca. 3 nm Aufloesung, Messbereich 400-700 nm (roughly VIS, '
                'erweiterbar). Bekannte Grenze: Webcams lassen sich meist '
                'nicht abschalten (Exposure-/Gain-Kompensation), daher sind '
                'Geraeteuebergreifende Vergleiche nur bedingt moeglich. '
                'Auswertung browserbasiert ueber SpectralWorkbench.org '
                '(Chrome/Firefox/Opera); Konstruktionsdateien auf GitHub. '
                'Materialkosten typisch ca. 45 USD.'),
            'urls': [
                ('Projektbeschreibung', 'https://publiclab.org/wiki/raw/21568'),
                ('GitHub', 'https://github.com/publiclab/spectrometer3'),
                ('Spectral Workbench', 'https://spectralworkbench.org/'),
            ],
            'features': [
                'USB-Webcam als Sensor',
                'Browserbasierte Auswertung',
                'Open-Source Hardware und Software',
                'Zahlreiche Umbauten als 3D-Druck-Versionen verfügbar',
                'Typisch etwa 45 USD Materialkosten',
            ],
            'suited_for': [
                'Open-Science-Community-Projekte',
                'Bildungsarbeit',
            ],
        },
        {
            'name': 'Smartphone-CD-Spektrometer',
            'slug': 'smartphone-cd',
            'status': gettext('Aktuelles, druckbares Modell'),
            'description': gettext(
                'Komplett 3D-druckbares Smartphone-Spektrometer (MakerWorld-'
                'Modell 1459435): Smartphone-Kamera als Sensor, CD als '
                'Beugungsgitter, einstellbare Spaltbreite 0,1-0,2 mm. '
                'Geeignet fuer Smartphone-Kameras bis 16 mm Objektiv-'
                'durchmesser; Materialkosten oft unter 10 EUR inklusive '
                'Druckmaterial. Modellseite auf MakerWorld (automatischer '
                'Zugriff blockiert, Details siehe Link).'),
            'urls': [
                ('MakerWorld', 'https://makerworld.com/en/models/1459435-mobile-spectrometer'),
            ],
            'features': [
                'Smartphone-Kamera als Sensor',
                'CD als Beugungsgitter',
                'Spaltbreite 0,1 bis 0,2 mm',
                'Für Smartphone-Kameras bis 16 mm Objektivdurchmesser geeignet',
                'Komplett 3D-druckbar',
                'Oft unter 10 € inklusive Druckmaterial',
            ],
            'suited_for': [
                'Schnelle Einstiegsprojekte',
                'Demonstrationen im Unterricht',
            ],
        },
        {
            'name': 'SpecPhone / DualSpec',
            'slug': 'specphone-dualspec',
            'status': gettext('Wissenschaftlich publiziertes Projekt'),
            'description': gettext(
                '3D-druckbare Smart-Phone-Spektralphotometer fuer die '
                'Absorptionsmessung im sichtbaren Bereich (Smith Lab, Texas '
                'Tech). DualSpec ist die aktuelle Version: Dual-Beam-Design '
                'mit Referenzstrahl (deutlich besseres Signal-Rausch-'
                'Verhaeltnis), wechselbare Spaltmodule 0,1-5 mm zur '
                'Veranschaulichung des Aufloesungsprinzips, Standard-'
                '10-mm-Kuvetten. Teile: 1000 Linien/mm-Gitterfolie, '
                '1-Inch-Alu-Spiegel, LED- oder Tischlampenquelle, 3D-Druck-'
                'Gehaeuse (STL auf Thingiverse). Wissenschaftlich begleitete '
                'Publikation: J Chem Educ 2019, 96(7), 1527-1531 '
                '(DOI 10.1021/acs.jchemed.8b00870) und 2016, 93(1), 146-151.'),
            'urls': [
                ('Smith Lab', 'https://www.adamsmithlab.org/specphone'),
                ('Thingiverse (STL)', 'https://www.thingiverse.com/thing:3404762'),
            ],
            'features': [
                'Nutzt Standard-10-mm-Küvetten',
                'Wechselbare Spaltmodule von 0,1 bis 5 mm',
                'Dual-Beam-Design mit Referenzstrahl',
                'Für quantitative Konzentrationsmessungen geeignet',
            ],
            'suited_for': [
                'Quantitative Messungen',
                'Wissenschaftliche Arbeiten',
            ],
        },
    ]

    TUTORIAL_LINKS = [
        ('Bauanleitungen.pro - Spektroskop',
         'https://www.bauanleitungen.pro/Spektroskop'),
        ('Eureca - DIY-Spektrometer',
         'https://www.eureca.de/5109-0-DIY-Spektrometer.html'),
        ('Printed Labs Uni Bayreuth - BasisSpek',
         'https://printedlabs.uni-bayreuth.de/de/modelldatenbank/_spektrometer/spektroskopie/_basicspec/content'),
        ('Uni Würzburg Didaktik - Low-Cost VIS-Spektrometer',
         'https://www.chemie.uni-wuerzburg.de/didaktik/lehrpersonen/low-cost-messgeraete/vis-spektrometer/'),
        ('Umwelt-Campus - MINT-Absorptions-Spektrometer',
         'https://www.umwelt-campus.de/iot-werkstatt/tutorials/mint-absorptions-spektrometer'),
        ('Public Lab - Video Spectrometer Construction',
         'https://publiclab.org/#wiki/video-spectrometer-construction'),
        ('Reddit r/Optics - Cheap DIY Spectrometer',
         'https://www.reddit.com/r/Optics/comments/z9zxde/my_cheap_diy_spectrometer_sharpest_peak_has_a/'),
    ]

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())
        from services.sensor_websearch import (
            ollama_available, websearch_enabled,
        )
        websearch_query = request.GET.get('q', '').strip()
        websearch_result = None
        if websearch_query and websearch_enabled():
            from services.sensor_websearch import search_sensor
            websearch_result = search_sensor(websearch_query)
        context = {
            'page_title': gettext('DIY-Spektrometer'),
            'projects': self.DIY_PROJECTS,
            'tutorials': self.TUTORIAL_LINKS,
            'websearch_enabled': websearch_enabled(),
            'ollama_available': ollama_available(),
            'websearch_query': websearch_query,
            'websearch_result': websearch_result,
        }
        return render(request, self.template_name, context)


class DiyDetailView(TemplateView):
    """One DIY project page (OP54): same pattern as the sensor detail page.
    Curated info from the project pages, the uploaded documents and an
    asynchronous KI overview (local Ollama; honest fallback)."""
    template_name = 'sensor_diy_detail.html'

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    @staticmethod
    def _sensor_key(slug):
        return f'diy_{slug}'

    @classmethod
    def get_project(cls, slug):
        return next((p for p in DiySpectrometerView.DIY_PROJECTS
                     if p.get('slug') == slug), None)

    def get(self, request, slug):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())
        project = self.get_project(slug)
        if project is None:
            raise Http404('DIY project not found')
        from services.sensor_documents import (DOC_TYPES, document_stats,
                                               sensor_documents)
        sensor_key = self._sensor_key(slug)
        documents = sensor_documents(sensor_key, request.user)
        context = {
            'page_title': f"DIY: {project['name']}",
            'project': project,
            'diy_slug': slug,
            'sensor_key': sensor_key,
            'documents': documents,
            'document_stats': document_stats(documents),
            'doc_types': DOC_TYPES,
        }
        return render(request, self.template_name, context)

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
            return Response({'success': False, 'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        file_ids = request.data.get('file_ids', [])
        name = (request.data.get('name') or '').strip()
        if not file_ids:
            return Response({'success': False, 'error': gettext('file_ids required')},
                            status=status.HTTP_400_BAD_REQUEST)
        files = GenericFile.objects.filter(id__in=file_ids, user=request.user)
        if not files.exists():
            return Response({'success': False, 'error': gettext('No matching files')},
                            status=status.HTTP_404_NOT_FOUND)
        if not name:
            name = f"Projekt {files.first().name}"
        project = AnalysisProject.objects.create(user=request.user, name=name,
                                                 description=request.data.get('description', ''))
        project.files.set(files)

        from threading import Thread
        from services.project_ingest import build_preparation_report

        def _prepare(pid):
            try:
                from core.models import AnalysisProject as AP
                proj = AP.objects.get(id=pid)
                build_preparation_report(proj)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(
                    'Background preparation failed for project %s: %s', pid, exc)
                try:
                    proj = AP.objects.get(id=pid)
                    report = proj.preparation_report or {}
                    report['preparation_error'] = str(exc)
                    proj.preparation_report = report
                    proj.save(update_fields=['preparation_report', 'updated_at'])
                except Exception:
                    pass

        thread = Thread(target=_prepare, args=(project.id,), daemon=True)
        thread.start()
        return Response({
            'success': True,
            'project_id': str(project.id),
            'summary': project.get_summary(),
            'report_url': f'/projects/{project.id}/',
            'preparing': True,
        })


class ProjectPrepareStatusView(APIView if DRF_AVAILABLE else object):
    """Polling endpoint for the asynchronous preparation (OP55): the
    project is created immediately and the preparation report is built
    in the background; the detail page polls this endpoint until the
    report is ready."""

    def get(self, request, project_id):
        if not request.user.is_authenticated:
            return Response({'success': False,
                             'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        project = _get_project(project_id, request.user)
        report = project.preparation_report or {}
        ready = bool(report.get('datasets'))
        return Response({
            'success': True,
            'ready': ready,
            'error': report.get('preparation_error'),
            'dataset_count': len(report.get('datasets') or []),
        })


def _metadata_editor_fields(dataset: dict, recommended_fields: list) -> list:
    """Form fields for the OP13 online metadata editor of one dataset.

    Shows every recommended field (so existing values stay editable after a
    save - previously only *missing* fields were rendered, which made saved
    values disappear from the form on reload) plus all fields the user has
    already entered, each prefilled with its current value.
    """
    from services.project_ingest import RECOMMENDED_FIELD_ALIASES
    metadata = dataset.get('metadata') or {}
    names = []
    for name in list(recommended_fields or []):
        if name and name not in names:
            names.append(name)
    for name in metadata:
        if name and name not in names:
            names.append(name)
    # OP35: the fields the KI explicitly asked for (forward questions) are
    # offered as empty inputs as soon as the edit mode opens - the user
    # answers the question where it was asked, no field name hunting.
    import re as _re
    for question in (dataset.get('open_questions') or []):
        match = _re.search(r'Fehlende Felder: ([^.]+)', str(question))
        if match:
            for name in match.group(1).split(','):
                name = name.strip()
                if name and name not in names:
                    names.append(name)
    # The recommended field ('operator') and its canonical loader twin
    # ('operator_name') hold the SAME value after the alias sync - show
    # the information once, under the recommended name, so the user does
    # not see redundant fields in the editor.
    from services.project_ingest import RECOMMENDED_FIELD_ALIASES as _ALIASES

    def _value_of(name):
        value = metadata.get(name)
        if value in (None, ''):
            canonical = _ALIASES.get(name)
            if canonical:
                value = metadata.get(canonical, '')
        return value or ''

    return [{
        'name': name,
        'value': _value_of(name),
        'recommended': name in (recommended_fields or []),
    } for name in names
        if name not in RECOMMENDED_FIELD_ALIASES.values()]


class ProjectDetailView(TemplateView):
    """Phase 1 report (drafted) or phase 2 overview (released/completed).

    Drafted: datasets, metadata assessment, improvement recommendations,
    release button. Released/completed: per-agent crew reports, overall
    results, final Quarto report download.
    """

    template_name = 'project_report.html'

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, project_id):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())
        project = _get_project(project_id, request.user)
        preparation = project.preparation_report or {}
        crew_results = project.crew_results or {}
        from services.project_ingest import RECOMMENDED_METADATA_FIELDS
        datasets = preparation.get('datasets', [])
        for dataset in datasets:
            dataset['editor_fields'] = _metadata_editor_fields(
                dataset, RECOMMENDED_METADATA_FIELDS)
        context = {
            'page_title': f'Projekt: {project.name}',
            'project': project,
            'project_summary': project.get_summary(),
            'preparation': preparation,
            'datasets': datasets,
            'metadata_quality': preparation.get('metadata_quality', {}),
            'recommendations': preparation.get('recommendations', []),
            'sensor_reference': preparation.get('sensor_reference', {}),
            'crew_results': crew_results,
            'per_agent_reports': crew_results.get('per_agent_reports', []),
            'crew_analysis': crew_results.get('crew_analysis', {}),
            'final_report_path': project.final_report_path,
            'final_report_url': f'/projects/{project.id}/final-report/' if project.final_report_path else None,
        }
        return render(request, self.template_name, context)


class ProjectDeleteView(APIView if DRF_AVAILABLE else object):
    """Delete one of the user's projects (OP17). The uploaded files stay in
    the media store (they may be shared by other projects); persisted
    SpectrumRecords keep their data - only the project link is nulled by the
    SET_NULL rule - so the spectral database is not damaged by a deletion."""

    def post(self, request, project_id):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        project = _get_project(project_id, request.user)
        name = project.name
        project_id_str = str(project.id)
        project.delete()
        logger.info('Project %s (%s) deleted by user %s',
                    project_id_str, name, getattr(request.user, 'id', None))
        return Response({
            'success': True,
            'deleted_project_id': project_id_str,
            'deleted_project_name': name,
        })


class ProjectFilesAddView(APIView if DRF_AVAILABLE else object):
    """Add more files to an existing project (OP17): upload flow reuses
    /api/files/upload/, this view attaches the file_ids to the project and
    rebuilds the preparation report so the report page and metadata
    assessment reflect the new files immediately. Released/completed
    projects stay editable (further measurements): adding files moves the
    project back to the drafted phase so the user reviews the new data and
    re-releases for a fresh crew run. The crew results and persisted
    spectra of the earlier release are kept until then."""

    def post(self, request, project_id):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        project = _get_project(project_id, request.user)
        file_ids = request.data.get('file_ids', [])
        if not file_ids:
            return Response({'success': False, 'error': gettext('file_ids required')},
                            status=status.HTTP_400_BAD_REQUEST)
        files = GenericFile.objects.filter(id__in=file_ids, user=request.user)
        if not files.exists():
            return Response({'success': False, 'error': gettext('No matching files')},
                            status=status.HTTP_404_NOT_FOUND)
        existing_ids = set(project.files.values_list('id', flat=True))
        new_files = [f for f in files if f.id not in existing_ids]
        already_count = len(files) - len(new_files)
        if new_files:
            project.files.add(*new_files)
            if project.phase != 'drafted':
                project.phase = 'drafted'
                project.save(update_fields=['phase', 'updated_at'])
            from services.project_ingest import build_preparation_report
            report = build_preparation_report(project)
        else:
            report = project.preparation_report or {}
        return Response({
            'success': True,
            'added_file_count': len(new_files),
            'already_present_count': already_count,
            'file_count': project.files.count(),
            'usable_dataset_count': report.get('usable_dataset_count'),
            'total_dataset_count': report.get('total_dataset_count'),
            'report_url': f'/projects/{project.id}/',
        })


class ProjectReingestView(APIView if DRF_AVAILABLE else object):
    """Re-run the phase 1 preparation after the user adapted the files
    or edited the metadata online (OP13)."""

    def post(self, request, project_id):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': gettext('Authentication required')},
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


def _project_dataset_names(project, file_id: str) -> list:
    """Inner dataset names of one project file (OP30): an archive file
    yields one dataset per inner file ('OEL-MK_Train(1).csv'), a direct
    file yields none. Read from the stored preparation report - no
    re-ingest, and an empty report means no inner datasets exist."""
    datasets = (project.preparation_report or {}).get('datasets', [])
    return [d.get('file_name', '') for d in datasets
            if str(d.get('file_id', '')).startswith(f'{file_id}:')]


class ProjectMetadataView(APIView if DRF_AVAILABLE else object):
    """Edit dataset metadata online (OP13): the user enters/updates metadata
    fields per file directly on the project page; the overrides are stored
    on the project and the preparation report is rebuilt so the metadata
    quality assessment reflects the changes immediately - no external file
    versions or re-upload needed."""

    def post(self, request, project_id):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        project = _get_project(project_id, request.user)
        if project.phase != 'drafted':
            return Response({
                'success': False,
                'error': gettext('Project already released'),
                'message': gettext('Metadaten können nur vor der Freigabe angepasst werden.'),
            }, status=status.HTTP_409_CONFLICT)
        metadata = request.data.get('metadata')
        if not isinstance(metadata, dict) or not metadata:
            return Response({'success': False, 'error': gettext('metadata dict required')},
                            status=status.HTTP_400_BAD_REQUEST)

        known_file_ids = {str(f.id) for f in project.files.all()}
        # OP30: files inside an archive carry the inner id
        # '<archive-file-id>:<inner-name>' in their editor form. Built
        # from a snapshot of the plain file ids (mutating the set while
        # iterating it raises RuntimeError in Python).
        known_file_ids.update(
            f'{fid}:{name}' for fid in list(known_file_ids)
            for name in _project_dataset_names(project, fid))
        overrides = dict(project.metadata_overrides or {})
        for file_id, fields in metadata.items():
            if str(file_id) not in known_file_ids:
                continue
            if not isinstance(fields, dict):
                continue
            merged = dict(overrides.get(str(file_id), {}))
            for key, value in fields.items():
                if len(str(key)) > 64:
                    return Response({'success': False,
                                     'error': gettext('Metadatenfeld zu lang: {}').format(key)},
                                    status=status.HTTP_400_BAD_REQUEST)
                merged[str(key)] = '' if value is None else str(value)[:512]
            overrides[str(file_id)] = merged
        project.metadata_overrides = overrides
        project.save(update_fields=['metadata_overrides', 'updated_at'])

        from services.project_ingest import build_preparation_report
        report = build_preparation_report(project)
        return Response({
            'success': True,
            'metadata_quality_score': report.get('metadata_quality', {}).get('overall_quality_score'),
            'missing_recommended_fields': report.get('metadata_quality', {}).get('missing_recommended_fields', []),
            'usable_dataset_count': report.get('usable_dataset_count'),
            'report_url': f'/projects/{project.id}/',
        })


class ProjectReleaseView(APIView if DRF_AVAILABLE else object):
    """Release the project for analysis: run the full crew with per-agent
    reports and generate the final comprehensive Quarto report."""

    def post(self, request, project_id):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        project = _get_project(project_id, request.user)
        if project.phase == 'drafted':
            preparation = project.preparation_report or {}
            if not preparation.get('usable_dataset_count'):
                return Response({
                    'success': False,
                    'error': gettext('No usable datasets'),
                    'message': gettext('Mindestens ein verwertbarer Datensatz ist erforderlich, bevor die Analyse freigegeben werden kann.'),
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            project.phase = 'released'
            project.released_at = datetime.now(tz=timezone.utc)
            project.save(update_fields=['phase', 'released_at', 'updated_at'])

        # OP15: persist the released datasets into the spectral database
        # (visibility opt-in via the request; default stays owner-private)
        try:
            from services.spectrum_database import persist_project_spectra
            visibility = request.data.get('spectrum_visibility', 'private') \
                if hasattr(request, 'data') else 'private'
            if visibility not in ('private', 'lab_shared'):
                visibility = 'private'
            persist_project_spectra(project, visibility=visibility)
        except Exception:
            logger.exception('Spectral database persist failed (non-fatal)')
        # OP57: the full crew run (15 agents, LLM calls with up to 120s
        # timeout each) blocked the request for many minutes without any
        # feedback - exactly like the OP55 preparation problem. The crew
        # now runs in a background thread; the page polls the new status
        # endpoint (progress: elapsed time, per-agent sections so far)
        # until the phase flips to completed or an error is recorded.
        from threading import Thread

        def _run_crew(pid):
            try:
                from core.models import AnalysisProject as AP
                proj = AP.objects.get(id=pid)
                from services.project_crew import run_project_crew
                run_project_crew(proj)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).error(
                    'Background crew run failed for project %s: %s',
                    pid, exc, exc_info=True)
                try:
                    proj = AP.objects.get(id=pid)
                    proj.phase = 'drafted'
                    results = proj.crew_results or {}
                    results['crew_error'] = str(exc)
                    proj.crew_results = results
                    proj.save(update_fields=['crew_results', 'phase',
                                             'updated_at'])
                except Exception:
                    pass

        thread = Thread(target=_run_crew, args=(project.id,), daemon=True)
        thread.start()
        return Response({
            'success': True,
            'project_id': str(project.id),
            'analyzing': True,
            'report_url': f'/projects/{project.id}/',
        })


class ProjectCrewStatusView(APIView if DRF_AVAILABLE else object):
    """Polling endpoint for the asynchronous crew analysis (OP57): the
    release starts the full 15-agent crew in a background thread; the
    project page polls this endpoint until the analysis completes. The
    response carries honest progress: elapsed seconds and how many
    per-agent sections already exist."""

    def get(self, request, project_id):
        if not request.user.is_authenticated:
            return Response({'success': False,
                             'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        project = _get_project(project_id, request.user)
        results = project.crew_results or {}
        error = results.get('crew_error')
        completed = project.phase == 'completed'
        return Response({
            'success': True,
            'completed': completed,
            'error': error,
            'agent_sections': len(results.get('per_agent_reports') or []),
            'has_final_report': bool(project.final_report_path),
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

class ProjectFinalReportMarkdownView(TemplateView):
    """Serve the final report as Markdown download (OP39): renders the
    Markdown variant on demand from the stored crew results - no stored
    path needed, same data basis as the HTML report."""

    def get(self, request, project_id):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())
        project = _get_project(project_id, request.user)
        if not project.final_report_path or not os.path.exists(project.final_report_path):
            raise Http404('Final report not generated yet')
        from services.project_report import generate_markdown_report
        path = generate_markdown_report(project, project.crew_results or {})
        with open(path, 'r', encoding='utf-8') as handle:
            response = HttpResponse(handle.read(), content_type='text/markdown; charset=utf-8')
            response['Content-Disposition'] = (
                f'attachment; filename="final_report_{project.id}.md"')
            return response


class CalibrationOverviewView(TemplateView):
    """OP52 calibration overview (/calibration/): lists the calibration
    results (PLS/PCR and friends) of the user's completed/released
    projects, extracted from the stored per-agent crew results."""

    template_name = 'calibration_overview.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.get_full_path())
        from django.utils.translation import gettext as _
        entries = []
        for project in (AnalysisProject.objects
                        .filter(user=request.user)
                        .exclude(crew_results=None)
                        .order_by('-updated_at')):
            sections = ((project.crew_results or {})
                        .get('per_agent_reports') or [])
            cal_sections = [s for s in sections
                            if s.get('agent') == 'calibration']
            for section in cal_sections:
                data = section.get('data') or {}
                models = []
                for name, res in (data.get('models') or {}).items():
                    if not isinstance(res, dict):
                        continue
                    rpd = res.get('rpd')
                    rpd_class = 'secondary'
                    if rpd is not None:
                        if rpd > 5:
                            rpd_class = 'success'
                        elif rpd > 3:
                            rpd_class = 'info'
                        elif rpd > 2:
                            rpd_class = 'warning'
                        else:
                            rpd_class = 'danger'
                    models.append({
                        'name': name,
                        'status': res.get('status', ''),
                        'mean_r2': res.get('mean_r2'),
                        'rmse_cv': res.get('rmse_cv'),
                        'rpd': rpd,
                        'rpd_class': rpd_class,
                        'cv_folds': res.get('cv_folds'),
                    })
                entries.append({
                    'project_id': str(project.id),
                    'project_name': project.name,
                    'phase': project.phase,
                    'status': section.get('status', ''),
                    'best_model': data.get('best_model'),
                    'target_name': data.get('target_name'),
                    'models': models,
                    'charts': section.get('charts') or {},
                    'notes': data.get('notes') or [],
                })
        context = {'entries': entries,
                   'has_entries': bool(entries)}
        return render(request, self.template_name, context)
