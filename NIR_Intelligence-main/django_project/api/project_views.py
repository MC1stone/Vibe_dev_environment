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
from django.core import files as django_files
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
from .workflow_context import project_workflow_context, create_decision, resolve_decision
from core.models import WorkflowDecision
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
        similar_to = request.GET.get('similar_to')
        query_record = None
        similar_ids = None
        if similar_to:
            try:
                query_record = records.get(id=similar_to)
            except Exception:
                query_record = None
            if query_record is not None:
                from services.similarity_search import find_similar_records
                similar_ids = {m['record_id']
                               for m in find_similar_records(
                                   request.user, query_record, top_k=10)
                               if m.get('record_id')}
        spectra = []
        for record in records:
            summary = record.get_summary()
            summary['is_own'] = record.user_id == request.user.id
            summary['is_shared'] = record.visibility == 'lab_shared'
            if similar_ids is not None and str(record.id) in similar_ids:
                summary['is_similar_match'] = True
            try:
                from services.project_report import single_spectrum_chart_data_url
                summary['spectrum_chart'] = single_spectrum_chart_data_url(
                    record.wavelengths, record.intensities,
                    title=f'Spektrum: {record.file_name}')
            except Exception:
                summary['spectrum_chart'] = None
                logger.exception('Spectrum chart rendering failed (non-fatal)')
            spectra.append(summary)
        if similar_ids is not None:
            spectra = [s for s in spectra if s.get('is_similar_match')]
        context = {
            'page_title': 'Spektrendatenbank',
            'spectra': spectra,
            'total_count': len(spectra),
            'similar_to': (query_record.get_summary()
                           if query_record is not None else None),
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
                record_ids = summary.get('record_ids') or []
                if record_ids:
                    from services.similarity_search import find_similar_records
                    from core.models import SpectrumRecord
                    record = SpectrumRecord.objects.get(id=record_ids[0])
                    similar = find_similar_records(
                        request.user, record, top_k=10)
                    if similar:
                        messages.info(request, gettext(
                            'Ähnliche Referenzspektren in der Datenbank: ') +
                            str(len(similar)) + ' · ' + gettext(
                            'Treffer unter') + ' ' +
                            '/projects/database/?similar_to=' +
                            record_ids[0])
                    return redirect(
                        '/projects/database/?similar_to=' + record_ids[0])
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
        # KI-gestuetzte Zuordnungsvorschlaege fuer ungematchte Sensoren
        # (User-Anforderung 2026-10-15): Rueckfrage statt stiller
        # Redundanz - 'SparkFun Triad' vs. 'Triad' soll die KI erkennen
        # bzw. nachfragen, nie still zuordnen.
        sensor_match_suggestions = []
        try:
            from services.sensor_catalog import suggest_sensor_matches
            unmatched_names = [u.get('instrument_type', '')
                               for u in data.get('unmatched_usage', [])]
            sensor_match_suggestions = list(
                suggest_sensor_matches(unmatched_names).values())
        except Exception:
            logger.exception('Sensor match suggestions failed (non-fatal)')
        context = {
            'page_title': 'Sensoren',
            'registered_sensors': data.get('registered_sensors', []),
            'setting_options': data.get('setting_options', []),
            'usage': data.get('usage', []),
            'unmatched_usage': data.get('unmatched_usage', []),
            'sensor_match_suggestions': sensor_match_suggestions,
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
        # OP77: Freie Analyse-Wuensche beim Upload (nicht hardcodiert):
        # der Nutzer formuliert z. B. '5 Reifeklassen der Tomaten' oder
        # '3 Feuchtegruppen' - parse_wishes uebersetzt generisch.
        analysis_wishes_text = str(
            request.data.get('analysis_wishes') or '').strip()[:2000]
        if not file_ids:
            return Response({'success': False, 'error': gettext('file_ids required')},
                            status=status.HTTP_400_BAD_REQUEST)
        files = GenericFile.objects.filter(id__in=file_ids, user=request.user)
        if not files.exists():
            return Response({'success': False, 'error': gettext('No matching files')},
                            status=status.HTTP_404_NOT_FOUND)
        if not name:
            name = f"Projekt {files.first().name}"
        description = request.data.get('description', '')
        project = AnalysisProject.objects.create(user=request.user, name=name,
                                                 description=description)
        project.files.set(files)
        if analysis_wishes_text:
            from services.analysis_wishes import parse_wishes
            parsed = parse_wishes(analysis_wishes_text)
            project.preparation_report = {
                'user_options': {
                    'analysis_wishes': analysis_wishes_text,
                    'parsed_wishes': parsed['wishes'],
                    'unparsed_wishes': parsed['unparsed'],
                }}
            project.save(update_fields=['preparation_report'])

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
        progress = report.get('progress') or {}
        return Response({
            'success': True,
            'ready': ready,
            'error': report.get('preparation_error'),
            'dataset_count': len(report.get('datasets') or []),
            # OP78: schrittweiser Fortschritts-Trace statt Black Box -
            # aktuelle Datei, Schritt, Zähler und Zeitdaten fuer die
            # Fahrplan-Karte (project_report.html).
            'progress': progress,
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
            'workflow_context': project_workflow_context(project),
        }
        return render(request, self.template_name, context)


class ProjectDecisionCreateView(APIView if DRF_AVAILABLE else object):
    """Register a pending user decision for a project (WORKFLOW_DESIGN.md §3a)."""

    def post(self, request, project_id):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        project = _get_project(project_id, request.user)
        station = request.data.get('station')
        question = (request.data.get('question') or '').strip()
        options = request.data.get('options') or []
        try:
            station = int(station)
        except (TypeError, ValueError):
            station = None
        if not station or not 1 <= station <= 6:
            return Response({'success': False, 'error': gettext('station must be 1-6')},
                            status=status.HTTP_400_BAD_REQUEST)
        if not question:
            return Response({'success': False, 'error': gettext('question required')},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            decision = create_decision(
                project, station, question, options,
                ki_basis=request.data.get('ki_basis', ''))
        except ValueError as exc:
            return Response({'success': False, 'error': str(exc)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({'success': True, 'decision_id': str(decision.id)})


class ProjectDecisionResolveView(APIView if DRF_AVAILABLE else object):
    """Resolve a pending decision with one of its options (WORKFLOW_DESIGN.md §3c)."""

    def post(self, request, project_id, decision_id):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        project = _get_project(project_id, request.user)
        try:
            decision = WorkflowDecision.objects.get(id=decision_id, project=project,
                                                    resolved_at__isnull=True)
        except (WorkflowDecision.DoesNotExist, ValueError):
            return Response({'success': False, 'error': gettext('Decision not found')},
                            status=status.HTTP_404_NOT_FOUND)
        option_id = request.data.get('option_id')
        if not option_id:
            return Response({'success': False, 'error': gettext('option_id required')},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            resolve_decision(decision, option_id,
                             modified_values=request.data.get('modified_values'))
        except ValueError as exc:
            return Response({'success': False, 'error': str(exc)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({'success': True})


class ProjectKIAcceptView(APIView if DRF_AVAILABLE else object):
    """Accept/Adapt eines KI-Vorschlags mit EINEM Klick (User-Wunsch
    2026-10-09): der Nutzer bestaetigt die Zuordnung eines Rohwerts auf
    ein kanonisches Feld (oder passt den Wert an) - die Antwort wird als
    Metadaten-Override gespeichert, der Preparation-Report neu gebaut,
    die Frage ist damit beantwortet und verschwindet."""
    def post(self, request, project_id):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        project = _get_project(project_id, request.user)
        if project.phase != 'drafted':
            return Response({'success': False,
                             'error': gettext('Project already released')},
                            status=status.HTTP_409_CONFLICT)
        file_id = str(request.data.get('file_id') or '')
        field = str(request.data.get('field') or '').strip()
        value = str(request.data.get('value') or '').strip()
        action = str(request.data.get('action') or 'accept').strip()
        if not file_id or not field:
            return Response({'success': False,
                             'error': gettext('file_id and field required')},
                            status=status.HTTP_400_BAD_REQUEST)
        known_file_ids = {str(f.id) for f in project.files.all()}
        from services.project_ingest import _project_dataset_names
        known_file_ids.update(
            f'{fid}:{name}' for fid in list(known_file_ids)
            for name in _project_dataset_names(project, fid))
        if file_id not in known_file_ids:
            return Response({'success': False,
                             'error': gettext('Unknown file_id')},
                            status=status.HTTP_400_BAD_REQUEST)
        overrides = dict(project.metadata_overrides or {})
        merged = dict(overrides.get(file_id, {}))
        if action == 'dismiss':
            merged.pop(field, None)
            merged[f'__dismissed__{field}'] = '1'
        else:
            if len(value) > 512:
                return Response({'success': False,
                                 'error': gettext('Value too long')},
                                status=status.HTTP_400_BAD_REQUEST)
            merged[field] = value
            merged.pop(f'__dismissed__{field}', None)
        overrides[file_id] = merged
        project.metadata_overrides = overrides
        project.save(update_fields=['metadata_overrides', 'updated_at'])
        from services.project_ingest import build_preparation_report
        report = build_preparation_report(project)
        remaining = 0
        for q in report.get('metadata_quality', {}).get('open_questions', []):
            remaining += 1
        return Response({
            'success': True,
            'accepted': {'file_id': file_id, 'field': field, 'value': value},
            'metadata_quality_score': report.get('metadata_quality', {}).get('overall_quality_score'),
            'open_question_count': remaining,
        })


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


class ProjectAddSpectrumView(APIView if DRF_AVAILABLE else object):
    """Quick-Check-Anschluss (Vorfall 2026-10-15): ein analysiertes
    NIRSpectrum als Datei zu einem bestehenden Projekt hinzufuegen und
    die Vorbereitung neu berechnen. Nutzt die Originaldatei des
    Spektrums; die Projekt-Semantik ist die von ProjectFilesAddView
    (Projekt kehrt in die Vorbereitung zurueck, Review und erneute
    Freigabe durch den Nutzer)."""

    def post(self, request, project_id):
        if not request.user.is_authenticated:
            return Response({'success': False,
                             'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        project = _get_project(project_id, request.user)
        spectrum_id = request.data.get('spectrum_id')
        if not spectrum_id:
            return Response({'success': False,
                             'error': gettext('spectrum_id required')},
                            status=status.HTTP_400_BAD_REQUEST)
        from core.models import NIRSpectrum
        spectrum = NIRSpectrum.objects.filter(
            id=spectrum_id, user=request.user).first()
        if spectrum is None:
            return Response({'success': False,
                             'error': gettext('Spectrum not found')},
                            status=status.HTTP_404_NOT_FOUND)
        file_path = spectrum.get_file_path()
        if not file_path or not os.path.exists(file_path):
            return Response({'success': False,
                             'error': gettext(
                                 'Original file of the spectrum not found - '
                                 'please re-upload the source file.')},
                            status=status.HTTP_400_BAD_REQUEST)
        existing = GenericFile.objects.filter(
            user=request.user, name=spectrum.name or spectrum.sample_id,
            project=project).exists()
        if existing:
            return Response({
                'success': True,
                'already_present': True,
                'message': gettext(
                    'Spektrum ist bereits Teil des Projekts.'),
                'report_url': f'/projects/{project.id}/'})
        import mimetypes
        mime, _ = mimetypes.guess_type(file_path)
        with open(file_path, 'rb') as f:
            generic = GenericFile(
                user=request.user,
                name=spectrum.name or spectrum.sample_id or 'spectrum',
                content_type=mime or 'application/octet-stream',
                description=spectrum.description or '')
            generic.file.save(os.path.basename(file_path),
                              django_files.File(f), save=True)
        project.files.add(generic)
        if project.phase != 'drafted':
            project.phase = 'drafted'
            project.save(update_fields=['phase', 'updated_at'])
        from services.project_ingest import build_preparation_report
        report = build_preparation_report(project)
        return Response({
            'success': True,
            'file_id': str(generic.id),
            'usable_dataset_count': report.get('usable_dataset_count'),
            'total_dataset_count': report.get('total_dataset_count'),
            'report_url': f'/projects/{project.id}/'})


class ProjectReingestView(APIView if DRF_AVAILABLE else object):
    """Re-run the phase 1 preparation after the user adapted the files
    or edited the metadata online (OP13)."""

    def post(self, request, project_id):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        project = _get_project(project_id, request.user)
        # OP13-Logik wie ProjectFilesAddView: Der Reingest nach einer
        # Freigabe bedeutet neue/geaenderte Datenbasis - das Projekt kehrt
        # in die Vorbereitung zurueck und muss fuer eine erneute Analyse
        # explizit freigegeben werden (User-Befund 2026-10-09: Buttons
        # fuer released Projekte nicht erreichbar).
        phase_returned = False
        if project.phase != 'drafted':
            project.phase = 'drafted'
            project.save(update_fields=['phase', 'updated_at'])
            phase_returned = True
        # OP78: Reingest asynchron im Hintergrund (OP55-Muster wie beim
        # Projekt-Anlegen und Wunsch-Save) - der SYNCHRONE Lauf liess den
        # Request minutenlang im Button-Spinner haengen, OHNE dass die
        # OP78-Fahrplan-Karte je erschien (Nutzer-Befund 2026-10-21:
        # 'Ich sehe die Fahrplan-Karte nicht'). Der alte Report wird
        # geleert -> nach dem Reload zeigt die Karte den _PrepTrace.
        # OP82-Fix: Die fusion-Sektion (source_projects) muss erhalten
        # bleiben - sonst erkennt der OP80-Hook das Fusionsprojekt nach
        # dem Leeren NICHT mehr, es wird kein kombinierter Datensatz
        # gebaut und die Herkunft (Stufe-3-Vergleich, OP65-Doppel-
        # schutz) geht still verloren (Nutzer-Versuch 2026-10-22:
        # Reingest am zusammengefuehrten Projekt).
        report = (project.preparation_report or {})
        user_options = report.get('user_options') or {}
        preserved = {'user_options': user_options}
        if report.get('fusion'):
            preserved['fusion'] = report['fusion']
        report = preserved
        project.preparation_report = report
        project.save(update_fields=['preparation_report', 'updated_at'])
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
                    'Background reingest failed for project %s: %s', pid, exc)
                try:
                    proj = AP.objects.get(id=pid)
                    rep = proj.preparation_report or {}
                    rep['preparation_error'] = str(exc)
                    proj.preparation_report = rep
                    proj.save(update_fields=['preparation_report',
                                             'updated_at'])
                except Exception:
                    pass

        thread = Thread(target=_prepare, args=(project.id,), daemon=True)
        thread.start()
        return Response({
            'success': True,
            'phase_returned_to_preparation': phase_returned,
            'preparing': True,
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
        # OP77b: Analyse-Wuensche koennen auch am BESTEHENDEN Projekt
        # angebracht werden (Nutzer-Befund: 'Wo kann ich meine
        # Versuchsfrage anbringen?' - nicht nur beim Upload) - auch in
        # released/completed: der Wunsch wirkt ueber den Reingest, das
        # Projekt kehrt dafuer in die Vorbereitung zurueck (wie beim
        # Reingest-Button). Nur der Metadaten-Editor bleibt drafted-only.
        wishes_text = str(request.data.get('analysis_wishes') or '').strip()[:2000]
        metadata = request.data.get('metadata')
        if not wishes_text and project.phase != 'drafted':
            return Response({
                'success': False,
                'error': gettext('Project already released'),
                'message': gettext('Metadaten können nur vor der Freigabe angepasst werden.'),
            }, status=status.HTTP_409_CONFLICT)
        if wishes_text and project.phase != 'drafted':
            project.phase = 'drafted'
            project.save(update_fields=['phase', 'updated_at'])
        if wishes_text:
            from services.analysis_wishes import parse_wishes
            parsed = parse_wishes(wishes_text)
            report = (project.preparation_report or {})
            opts = report.setdefault('user_options', {})
            opts['analysis_wishes'] = wishes_text
            opts['parsed_wishes'] = parsed['wishes']
            opts['unparsed_wishes'] = parsed['unparsed']
            project.preparation_report = report
            project.save(update_fields=['preparation_report', 'updated_at'])
            if not isinstance(metadata, dict) or not metadata:
                # Nur Wunsch gesetzt, keine Felder - Aufbereitung im
                # HINTERGRUND neu aufbauen (OP55-Muster wie beim
                # Projekt-Anlegen): der synchrone Lauf blockte den
                # Request still, der Nutzer sah nicht, dass die
                # Aufbereitung laeuft (Nutzer-Befund 2026-10-21). Die
                # Detailseite zeigt nach dem Reload die Fortschritts-
                # karte 'Datenaufbereitung laeuft...' mit Polling.
                report.pop('datasets', None)
                report.pop('preparation_error', None)
                project.preparation_report = report
                project.save(update_fields=['preparation_report',
                                            'updated_at'])
                from threading import Thread

                def _prepare_wishes(pid):
                    try:
                        from core.models import AnalysisProject as AP
                        proj = AP.objects.get(id=pid)
                        from services.project_ingest import \
                            build_preparation_report
                        build_preparation_report(proj)
                    except Exception as exc:
                        import logging
                        logging.getLogger(__name__).warning(
                            'Background preparation failed for project '
                            '%s: %s', pid, exc)
                        try:
                            proj = AP.objects.get(id=pid)
                            rep = proj.preparation_report or {}
                            rep['preparation_error'] = str(exc)
                            proj.preparation_report = rep
                            proj.save(update_fields=[
                                'preparation_report', 'updated_at'])
                        except Exception:
                            pass
                thread = Thread(target=_prepare_wishes,
                                 args=(project.id,), daemon=True)
                thread.start()
                return Response({
                    'success': True,
                    'wishes_applied': bool(parsed['wishes']),
                    'wishes_unparsed': parsed['unparsed'],
                    'preparing': True,
                    'report_url': f'/projects/{project.id}/',
                })
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
                # OP74: CSRF-Formularfeld nie als Metadatum uebernehmen
                # (auch bei alten Clients / anderen Formularen).
                if str(key).lower() == 'csrfmiddlewaretoken':
                    continue
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
            project_record_id = None
            similar_count = None
            try:
                from core.models import SpectrumRecord
                record = (SpectrumRecord.objects
                          .filter(user=request.user, project_id=project.id)
                          .order_by('-created_at').first())
                if record is not None:
                    project_record_id = str(record.id)
                    from services.similarity_search import find_similar_records
                    similar_count = len(find_similar_records(
                        request.user, record, top_k=10))
            except Exception:
                logger.exception(
                    'Similarity lookup for calibration entry failed '
                    '(non-fatal)')
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
                spectrum_chart = None
                for s in sections:
                    if s.get('agent') == 'spectral_analysis':
                        spectrum_chart = (s.get('charts') or {}).get('spectrum')
                        break
                n_samples = None
                for key in ('n_measurements', 'num_samples', 'n_samples'):
                    if isinstance(data.get(key), int):
                        n_samples = data.get(key)
                        break
                equation = data.get('calibration_equation') or {}
                charts = section.get('charts') or {}
                ordered_charts = dict(charts)
                if spectrum_chart:
                    ordered = {'spectrum': spectrum_chart}
                    ordered.update(ordered_charts)
                    ordered_charts = ordered
                entries.append({
                    'project_id': str(project.id),
                    'project_name': project.name,
                    'phase': project.phase,
                    'status': section.get('status', ''),
                    'best_model': data.get('best_model'),
                    'target_name': data.get('target_name'),
                    'models': models,
                    'charts': ordered_charts,
                    'chart_keys': list(ordered_charts),
                    'notes': data.get('notes') or [],
                    'updated_at': project.updated_at,
                    'n_samples': n_samples,
                    'equation': equation,
                    'similar_count': similar_count,
                    'similar_link': (f'/projects/database/?similar_to='
                                     f'{project_record_id}'
                                     if project_record_id else None),
                })
        context = {'entries': entries,
                   'has_entries': bool(entries)}
        return render(request, self.template_name, context)


class ProjectFusionPreviewView(APIView if DRF_AVAILABLE else object):
    """OP63 Stufe 2: Metadaten-Abgleich vor der Zusammenfuehrung (schreibfrei).

    POST {project_ids: [id_a, id_b]} liefert die Differenzliste und die
    Datenmengen aller beteiligten Projekte - der Nutzer entscheidet auf
    dieser Basis, ob der Analyse-Zweig ausgefuehrt wird."""
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        project_ids = request.data.get('project_ids') or []
        if len(project_ids) < 2:
            return Response({'success': False,
                             'error': gettext('project_ids (min. 2) required')},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            from services.project_fusion import preview_fusion
            result = preview_fusion(request.user, project_ids)
            result['success'] = True
            return Response(result)
        except Exception as exc:
            logger.exception('Fusion preview failed')
            return Response({'success': False, 'error': str(exc)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProjectFusionExecuteView(APIView if DRF_AVAILABLE else object):
    """OP63 Stufe 2: Zusammenfuehrung in ein NEUES Projekt.

    POST {project_ids: [id_a, id_b], name?, description?}. Die Quell-
    Projekte bleiben unangetastet (PO-Entscheidung: neues Projekt statt
    Merge-in-place); das Fusionsprojekt referenziert die Original-Dateien
    und startet die Aufbereitung im Hintergrund (OP55-Muster)."""
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        project_ids = request.data.get('project_ids') or []
        if len(project_ids) < 2:
            return Response({'success': False,
                             'error': gettext('project_ids (min. 2) required')},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            from services.project_fusion import execute_fusion
            result = execute_fusion(
                request.user, project_ids,
                name=(request.data.get('name') or '').strip(),
                description=(request.data.get('description') or '').strip(),
                # OP79b: FREIE Analyse-Wuensche bei der Fusion (flexibel,
                # generisch) - der Text geht durch die parse_wishes-
                # Pipeline; das alte analysis_intent bleibt als Shortcut.
                analysis_intent=str(
                    request.data.get('analysis_intent') or '').strip(),
                analysis_wishes=str(
                    request.data.get('analysis_wishes') or '').strip())
            status_code = (status.HTTP_200_OK if result.get('success')
                          else status.HTTP_422_UNPROCESSABLE_ENTITY)
            return Response(result, status=status_code)
        except Exception as exc:
            logger.exception('Fusion execute failed')
            return Response({'success': False, 'error': str(exc)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProjectFusionCalibrationView(APIView if DRF_AVAILABLE else object):
    """OP63 Stufe 3: vergleichende Kalibration des Fusion-Zweigs.

    GET/POST /api/projects/<id>/fusion/calibration/ - nur fuer
    Fusionsprojekte (OP63). Rechnet die drei Kalibrationen (Quelle A,
    Quelle B, kombiniert) via CalibrationAgent (PLS) und den
    Signifikanz-Test der Residuen pro Herkunftsgruppe (Levene + Welch).
    Liefert den vollstaendigen Vergleich als JSON fuer das Berichts-Panel.
    """
    def get(self, request, project_id):
        return self._compare(request, project_id)

    def post(self, request, project_id):
        return self._compare(request, project_id)

    def _compare(self, request, project_id):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        project = _get_project(project_id, request.user)
        fusion = (project.preparation_report or {}).get('fusion') or {}
        if not fusion.get('source_projects'):
            return Response({'success': False,
                             'error': gettext('Not a fusion project')},
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        try:
            from core.models import AnalysisProject
            from services.fusion_calibration import comparative_calibration
            source_ids = [s['project_id'] for s in fusion['source_projects']
                          if s.get('project_id')]
            sources = AnalysisProject.objects.filter(
                id__in=source_ids, user=request.user)
            if sources.count() < 2:
                return Response({'success': False,
                                 'error': gettext('Source projects not accessible')},
                                status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            comparison = comparative_calibration(project, list(sources))
            comparison['success'] = True
            comparison['fusion_project_name'] = project.name
            comparison['source_projects'] = [
                {'project_id': str(p.id), 'project_name': p.name}
                for p in sources]
            return Response(comparison)
        except Exception as exc:
            logger.exception('Fusion calibration comparison failed')
            return Response({'success': False, 'error': str(exc)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProjectFusionMetadataSuggestionsView(APIView if DRF_AVAILABLE else object):
    """OP65: KI-Metadaten-Vorschlaege fuer das Fusionsprojekt - Felder aus
    dem Datensatz MIT Metadaten als Uebernahme-Vorschlag fuer die Datensatze
    OHNE (Livetest-Feedback: 'die Metadaten koennen ergaenzt werden, aber
    die Vorschlaege der KI habe ich vermisst'). Nur fuer Fusionsprojekte."""
    def get(self, request, project_id):
        if not request.user.is_authenticated:
            return Response({'success': False, 'error': gettext('Authentication required')},
                            status=status.HTTP_401_UNAUTHORIZED)
        project = _get_project(project_id, request.user)
        fusion = (project.preparation_report or {}).get('fusion') or {}
        if not fusion.get('source_projects'):
            return Response({'success': False,
                             'error': gettext('Not a fusion project')},
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        try:
            from services.project_fusion import metadata_suggestions
            result = metadata_suggestions(project)
            result['success'] = True
            return Response(result)
        except Exception as exc:
            logger.exception('Fusion metadata suggestions failed')
            return Response({'success': False, 'error': str(exc)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
