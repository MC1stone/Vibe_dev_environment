"""
Views for the Analysis app in NIR Intelligence Platform.
"""

import os
import sys
import json
import logging
import uuid
from datetime import datetime
from django.utils import timezone as django_timezone
from typing import Any, Dict
import asyncio

# Add the package roots to Python path so the `agents` module is importable.
# views.py lives at nir_platform/django_app/analysis/views.py; the `agents`
# package lives at nir_platform/agents. In the Docker layout the app is
# flattened to /app/analysis/views.py with /app/agents, so we add both the
# django_app directory and its parent to sys.path to cover both layouts.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DJANGO_APP_DIR = os.path.dirname(_THIS_DIR)
_PLATFORM_DIR = os.path.dirname(_DJANGO_APP_DIR)
sys.path.insert(0, _PLATFORM_DIR)
sys.path.insert(0, _DJANGO_APP_DIR)

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, FileResponse
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from django.views.decorators.http import require_http_methods
from .models import SpectralData, AnalysisProject, Report, ChatSession, SystemLog
from .forms import UploadFileForm, AnalysisForm, ChatForm
from agents.data_loader_agent import DataLoaderAgent
from agents.spectral_analysis_agent import SpectralAnalysisAgent
from agents.spectral_search_agent import SpectralSearchAgent
from agents.metadata_quality_agent import MetadataQualityAgent
from agents.calibration_agent import CalibrationAgent
from agents.reporting_agent import ReportingAgent
from agents.quality_assurance_agent import QualityAssuranceAgent

# Configure logging
logger = logging.getLogger(__name__)


# Initialize agents (singleton instances)
data_loader_agent = DataLoaderAgent()
spectral_agent = SpectralAnalysisAgent()
spectral_search_agent = SpectralSearchAgent()
metadata_agent = MetadataQualityAgent()
calibration_agent = CalibrationAgent()
reporting_agent = ReportingAgent()
qa_agent = QualityAssuranceAgent()


def home(request):
    """Home page view."""
    recent_analyses = SpectralData.objects.filter(user=request.user if request.user.is_authenticated else None).order_by('-upload_date')[:5]
    
    context = {
        'page_title': 'NIR Intelligence Platform',
        'recent_analyses': recent_analyses,
        'app_description': 'Open Science NIR Spectral Analysis System',
        'features': [
            {'title': 'Spectral Analysis', 'description': 'Analyze NIR spectra from any spectrometer'},
            {'title': 'Metadata Quality', 'description': 'Evaluate metadata against international standards'},
            {'title': 'Calibration', 'description': 'Generate and apply spectrometer calibration'},
            {'title': 'Reporting', 'description': 'Generate comprehensive Quarto reports'},
            {'title': 'Federated Learning', 'description': 'Share data with the federated learning network'},
        ]
    }
    
    return render(request, 'analysis/home.html', context)


def _spectral_data_brief(sd: SpectralData) -> Dict[str, Any]:
    """Compact summary of one analysis for the overview/comparison views."""
    md = sd.metadata or {}
    brix = md.get('Brix') or md.get('brix') or md.get('BRIX') or []
    brix_range = None
    if brix:
        try:
            vals = [float(x) for x in brix if x not in (None, '')]
            if vals:
                brix_range = (min(vals), max(vals))
        except (TypeError, ValueError):
            brix_range = None
    ac = (sd.calibration_results or {}).get('analyte_calibration') if isinstance(sd.calibration_results, dict) else None
    return {
        'id': str(sd.id),
        'original_filename': sd.original_filename,
        'spectrometer_type': sd.spectrometer_type or 'Auto-detect',
        'upload_date': sd.upload_date,
        'is_processed': sd.is_processed,
        'wavelength_count': len(sd.wavelengths or []),
        'sample_count': len(md.get('intensity_matrix', [])) if isinstance(md, dict) else 0,
        'brix_range': brix_range,
        'overall_quality_score': sd.overall_quality_score,
        'data_quality_score': sd.data_quality_score,
        'calibration_quality_score': sd.calibration_quality_score,
        'calibration_r2_cv': ac.get('r_squared_cv') if ac else None,
        'calibration_rmse_cv': ac.get('rmse_cv') if ac else None,
        'has_report': Report.objects.filter(spectral_data=sd).exists(),
    }


def analyses_overview(request):
    """Overview of all past analyses and reports.

    Lets the customer recall already-created reports/analyses, and links
    into the comparison and recalibration workflows.
    """
    qs = SpectralData.objects.all().order_by('-upload_date')
    rows = [(_spectral_data_brief(sd), sd) for sd in qs]
    # Index all of them into the vector DB so the search/comparison works
    # even if the index was empty (e.g. after a DB restore).
    for brief, sd in rows:
        try:
            spectral_search_agent.index_analysis(
                analysis_id=brief['id'],
                intensities=sd.intensities or [],
                metadata=sd.metadata or {},
                original_filename=sd.original_filename,
                spectrometer_type=sd.spectrometer_type or '',
                quality_score=sd.data_quality_score,
                upload_date=sd.upload_date.isoformat() if sd.upload_date else None,
            )
        except Exception:
            pass
    context = {
        'page_title': 'Analyses Overview',
        'analyses': [b for b, _ in rows],
        'indexed_count': spectral_search_agent.count(),
        'search_backend': spectral_search_agent.backend,
    }
    return render(request, 'analysis/analyses_overview.html', context)


def compare_analyses(request):
    """Compare 2+ analyses side by side and find comparable measurements.

    Accepts a list of analysis ids (GET ?ids=...&ids=... or POST). Shows
    side-by-side quality/calibration metrics and, for the first selected
    analysis, the most similar past measurements found via the vector DB
    (Qdrant / numpy) so the customer can see whether comparable
    measurements were already executed.
    """
    selected_ids = request.GET.getlist('ids') or request.POST.getlist('ids')
    selected = []
    comparison_rows = []
    comparable = None
    base_id = None
    for aid in selected_ids:
        try:
            sd = SpectralData.objects.get(pk=aid)
        except (SpectralData.DoesNotExist, ValueError):
            continue
        selected.append(sd)
        comparison_rows.append(_spectral_data_brief(sd))
    if selected:
        base = selected[0]
        base_id = str(base.id)
        try:
            result = spectral_search_agent.search_similar(
                query_analysis_id=base_id,
                limit=10,
                min_similarity=0.5,
                same_spectrometer_only=True,
            )
            comparable = result.to_dict()
        except Exception as e:
            logger.warning(f'compare search failed: {e}')
            comparable = {'hits': [], 'backend': spectral_search_agent.backend,
                          'note': f'Search failed: {e}', 'count': 0}
    # If nothing selected, offer all analyses for selection.
    all_analyses = [_spectral_data_brief(sd) for sd in
                    SpectralData.objects.all().order_by('-upload_date')]
    context = {
        'page_title': 'Compare Analyses',
        'comparison_rows': comparison_rows,
        'comparable': comparable,
        'base_id': base_id,
        'all_analyses': all_analyses,
        'selected_ids': selected_ids,
    }
    return render(request, 'analysis/compare_analyses.html', context)


def recalibrate(request):
    """Recalculate the NIR->Brix calibration from combined analyses.

    The customer selects 2+ analyses; their per-sample intensity matrices
    and Brix references are stacked and a new PLS regression is fitted so
    the calibration can be recalculated with potential additional data.
    """
    selected_ids = request.GET.getlist('ids') or request.POST.getlist('ids')
    samples = []
    used = []
    combined_cal = None
    error = None
    for aid in selected_ids:
        try:
            sd = SpectralData.objects.get(pk=aid)
        except (SpectralData.DoesNotExist, ValueError):
            continue
        md = sd.metadata or {}
        mat = md.get('intensity_matrix') if isinstance(md, dict) else None
        brix = md.get('Brix') or md.get('brix') or md.get('BRIX')
        if not mat or not brix:
            continue
        samples.append({
            'intensity_matrix': mat,
            'analyte': brix,
            'wavelengths': sd.wavelengths or [],
            'label': sd.original_filename,
        })
        used.append(_spectral_data_brief(sd))
    combined_neural = None
    if request.method == 'POST' and samples:
        try:
            ac = calibration_agent.recalibrate_from_samples(samples)
            if ac is not None:
                combined_cal = ac.to_dict()
            else:
                error = ('Could not recalibrate: not enough combined samples, '
                         'or scikit-learn is unavailable.')
            # Fit a combined neural-network model in parallel to PLS.
            try:
                ncal = calibration_agent.recalibrate_neural_from_samples(samples)
                if ncal is not None:
                    combined_neural = ncal.to_dict()
            except Exception as ne:
                logger.warning(f'Neural recalibration failed: {ne}')
        except Exception as e:
            error = f'Recalibration failed: {e}'
    # Pair wavelengths with their coefficients so the template can iterate
    # without relying on a non-existent index filter.
    coeff_table = []
    if combined_cal:
        wls = combined_cal.get('wavelengths') or []
        coefs = combined_cal.get('coefficients') or []
        for i, wl in enumerate(wls):
            c = coefs[i] if i < len(coefs) else None
            coeff_table.append({'wavelength': wl, 'coefficient': c})
    all_analyses = [_spectral_data_brief(sd) for sd in
                    SpectralData.objects.all().order_by('-upload_date')]
    context = {
        'page_title': 'Recalculate Calibration',
        'used': used,
        'combined_cal': combined_cal,
        'coeff_table': coeff_table,
        'combined_neural': combined_neural,
        'error': error,
        'all_analyses': all_analyses,
        'selected_ids': selected_ids,
    }
    return render(request, 'analysis/recalibrate.html', context)


def upload_file(request):
    """File upload view."""
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Save uploaded file
                uploaded_file = request.FILES['file']
                
                # Parse optional metadata JSON submitted via the form
                metadata_raw = form.cleaned_data.get('metadata', '')
                metadata = {}
                if metadata_raw:
                    try:
                        metadata = json.loads(metadata_raw)
                        if not isinstance(metadata, dict):
                            messages.error(request, 'Metadata must be a JSON object.')
                            metadata = {}
                    except (json.JSONDecodeError, TypeError) as me:
                        messages.error(request, f'Invalid metadata JSON: {me}')
                        metadata = {}
                
                # Create unique filename
                file_ext = os.path.splitext(uploaded_file.name)[1]
                unique_id = uuid.uuid4().hex
                filename = f"{unique_id}{file_ext}"
                file_path = os.path.join(settings.UPLOAD_DIR, filename)
                
                # Save file
                with open(file_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                
                # Parse the uploaded spectral file via the Data Loader Agent,
                # which runs on every new upload and returns the structured
                # LoadResult (wavelengths, representative intensities, the full
                # per-sample intensity matrix, metadata incl. Brix, and the
                # detected spectrometer type).
                wavelengths = []
                intensities = []
                spectrometer_type = form.cleaned_data.get('spectrometer_type', None)
                try:
                    loaded = asyncio.run(data_loader_agent.load(file_path))
                    wavelengths = list(loaded.wavelengths)
                    intensities = list(loaded.intensities)
                    # Merge metadata detected from the file (file comments, header
                    # cols, Brix/Temp reference columns).
                    file_metadata = loaded.metadata or {}
                    if isinstance(file_metadata, dict):
                        for k, v in file_metadata.items():
                            metadata.setdefault(k, v)
                    # Carry the full per-sample intensity matrix + spectral
                    # column order + spectrometer info into metadata so the
                    # calibration agent can build the NIR->Brix regression.
                    if loaded.intensity_matrix:
                        metadata['intensity_matrix'] = loaded.intensity_matrix
                        metadata['spectral_columns'] = loaded.spectral_columns
                    if loaded.spectrometer_info:
                        metadata['spectrometer_info'] = loaded.spectrometer_info
                    # Persist the structured header metadata + proposed quality
                    # rating so the metadata-quality agent and the UI can use them
                    # and the user can fill in missing fields.
                    if loaded.standard_metadata:
                        metadata['standard_metadata'] = loaded.standard_metadata
                    if loaded.metadata_quality:
                        metadata['metadata_quality'] = loaded.metadata_quality
                    if not spectrometer_type:
                        spectrometer_type = loaded.spectrometer_type
                except Exception as pe:
                    logger.error(f'Error parsing spectral file {uploaded_file.name}: {pe}')
                    messages.error(
                        request,
                        f'File saved, but could not parse spectral data: {pe}. '
                        'Analysis will not be available until a valid file is uploaded.'
                    )
                    metadata_error = True
                else:
                    metadata_error = False
                
                # Create SpectralData record
                spectral_data = SpectralData(
                    user=request.user if request.user.is_authenticated else None,
                    original_filename=uploaded_file.name,
                    file_path=file_path,
                    file_type=file_ext.lower(),
                    wavelengths=wavelengths,
                    intensities=intensities,
                    metadata=metadata,
                    spectrometer_type=spectrometer_type
                )
                spectral_data.save()
                logger.info(
                    f'Uploaded spectral data saved id={spectral_data.id} '
                    f'wl_len={len(wavelengths)} int_len={len(intensities)} '
                    f'spec_type={spectrometer_type!r} metadata_error={metadata_error}'
                )
                
                # Log the upload
                SystemLog.objects.create(
                    level='INFO',
                    message=f'File uploaded: {uploaded_file.name}',
                    module='analysis.views',
                    function='upload_file',
                    context={'file_id': str(spectral_data.id), 'user': str(request.user)}
                )
                
                if metadata_error:
                    return redirect('analysis_detail', analysis_id=spectral_data.id)
                
                messages.success(request, f'File "{uploaded_file.name}" uploaded successfully!')
                return redirect('analysis_detail', analysis_id=spectral_data.id)
                
            except Exception as e:
                logger.error(f'Error uploading file: {e}')
                messages.error(request, f'Error uploading file: {str(e)}')
        else:
            messages.error(request, 'Invalid form data')
    else:
        form = UploadFileForm()
    
    context = {
        'page_title': 'Upload Spectral Data',
        'form': form,
        'allowed_extensions': settings.NIR_PLATFORM['allowed_extensions'],
        'max_upload_size': settings.NIR_PLATFORM['max_upload_size'] // (1024 * 1024)  # MB
    }
    
    return render(request, 'analysis/upload.html', context)


async def analyze_spectral_data(spectral_data: SpectralData):
    """Analyze spectral data using agents."""
    try:
        # Load spectral data
        # Build the data dict from the parsed spectral data so the agents
        # receive the real wavelengths/intensities captured at upload time.
        data_dict = {
            'wavelengths': spectral_data.wavelengths,
            'intensities': spectral_data.intensities,
            'metadata': spectral_data.metadata,
            'spectrometer_type': spectral_data.spectrometer_type,
            'file_path': spectral_data.file_path
        }
        
        # Run spectral analysis
        spectral_result = await spectral_agent.analyze_spectral_data(data=data_dict)
        
        # Run metadata quality assessment. Merge the structured header
        # metadata extracted by the Data Loader Agent so the metadata agent
        # grades on the real extracted fields, not just the raw columns.
        md_for_eval = dict(spectral_data.metadata or {})
        std_md = md_for_eval.get('standard_metadata') or {}
        if isinstance(std_md, dict):
            for k, v in std_md.items():
                md_for_eval.setdefault(k, v)
        metadata_result = await metadata_agent.evaluate_metadata_quality(md_for_eval)
        
        # Run calibration
        calibration_result = await calibration_agent.generate_calibration(data_dict)
        
        # Run QA check
        qa_result = await qa_agent.perform_qa_check(
            spectral_result.to_dict(),
            metadata_result.to_dict(),
            calibration_result.to_dict()
        )
        
        # Generate report (return the report object so the view can render it)
        report = await reporting_agent.generate_spectral_analysis_report(
            spectral_result.to_dict(),
            metadata_result.to_dict(),
            calibration_result.to_dict()
        )
        
        # Index the spectral fingerprint in the vector DB (Qdrant / numpy)
        # so this analysis can be recalled and compared against future
        # uploads and other past analyses.
        try:
            spectral_search_agent.index_analysis(
                analysis_id=str(spectral_data.id),
                intensities=spectral_data.intensities or [],
                metadata=spectral_data.metadata or {},
                original_filename=spectral_data.original_filename,
                spectrometer_type=spectral_data.spectrometer_type or '',
                quality_score=spectral_data.data_quality_score,
                upload_date=spectral_data.upload_date.isoformat() if spectral_data.upload_date else None,
            )
        except Exception as ie:
            logger.warning(f'Failed to index spectral fingerprint: {ie}')
        
        return {
            'spectral_result': spectral_result.to_dict(),
            'metadata_result': metadata_result.to_dict(),
            'calibration_result': calibration_result.to_dict(),
            'qa_result': qa_result.to_dict(),
            'report': report
        }
        
    except Exception as e:
        logger.error(f'Error analyzing spectral data: {e}')
        raise


def analysis_detail(request, analysis_id):
    """Analysis detail view."""
    spectral_data = get_object_or_404(SpectralData, pk=analysis_id)

    # Allow the user to re-run the analysis (and regenerate the report)
    # on an existing record without re-uploading the file. This is needed
    # when a previous run generated an empty/broken report (e.g. a missing
    # dependency that has since been installed).
    if request.method == 'POST' and request.POST.get('action') == 'rerun_analysis':
        Report.objects.filter(spectral_data=spectral_data).delete()
        spectral_data.is_processed = False
        spectral_data.processing_date = None
        spectral_data.save()
        logger.info(
            f'Re-run requested for id={spectral_data.id}; resetting analysis.')
        messages.success(request, 'Re-running analysis and regenerating report...')
        return redirect('analysis_detail', analysis_id=spectral_data.id)

    # Allow the user to add/append missing metadata and re-run the analysis.
    if request.method == 'POST' and request.POST.get('action') == 'add_metadata':
        md = dict(spectral_data.metadata or {})
        std_md = dict(md.get('standard_metadata') or {})
        for field in (
            'title', 'description', 'date', 'identifier', 'spectrometer_type',
            'wavelength_range', 'resolution', 'sample_type', 'temperature',
            'creator', 'data_owner', 'humidity', 'sample_preparation',
            'measurement_geometry', 'license',
        ):
            val = request.POST.get(field, '').strip()
            if val:
                std_md[field] = val
        md['standard_metadata'] = std_md
        spectral_data.metadata = md
        # Re-run the analysis with the enriched metadata.
        spectral_data.is_processed = False
        spectral_data.processing_date = None
        spectral_data.save()
        logger.info(
            f'Metadata added by user for id={spectral_data.id}; re-running analysis.')
        messages.success(request, 'Metadata added. Re-running analysis...')
        return redirect('analysis_detail', analysis_id=spectral_data.id)

    # Check if analysis has been performed
    if not spectral_data.is_processed:
        logger.info(
            f'Analysis pending for id={spectral_data.id} '
            f'wl_len={len(spectral_data.wavelengths or [])} '
            f'int_len={len(spectral_data.intensities or [])}'
        )
        # Guard: require parsed spectral data before analysis
        if not spectral_data.wavelengths or not spectral_data.intensities:
            messages.error(
                request,
                'No spectral data was parsed from this file. Please re-upload a valid '
                'spectral data file (CSV, TXT, Excel, JSON).'
            )
        else:
            # Perform analysis
            try:
                async def perform_analysis():
                    return await analyze_spectral_data(spectral_data)
                
                logger.info(f'Starting analysis for id={spectral_data.id}...')
                results = asyncio.run(perform_analysis())
                logger.info(
                    f'Analysis completed for id={spectral_data.id} '
                    f'keys={list(results.keys()) if isinstance(results, dict) else type(results).__name__}'
                )
                
                # Save results
                spectral_data.analysis_results = results.get('spectral_result', {})
                spectral_data.calibration_results = results.get('calibration_result', {})
                # Keep the full standards-compliance assessment for reference,
                # but the headline metadata quality score is the Data Loader
                # Agent's rating (metadata['metadata_quality']), which grades the
                # fields actually extracted from the file header. The
                # MetadataQualityAgent demands ISO 19115 / Open Science /
                # Federated-Learning fields a single NIR measurement never has,
                # so its score would otherwise drag the overview grade down to a
                # low value that disagrees with the Data Loader's 'A' rating.
                spectral_data.metadata_quality_results = results.get('metadata_result', {})
                dl_md = (spectral_data.metadata or {}).get('metadata_quality') or {}
                dl_score = dl_md.get('score') if isinstance(dl_md, dict) else None
                if dl_score is None:
                    dl_score = results.get('metadata_result', {}).get('overall_score', 0) or 0
                spectral_data.data_quality_score = results.get('spectral_result', {}).get('quality_score', 0) or 0
                spectral_data.metadata_quality_score = dl_score
                spectral_data.calibration_quality_score = results.get('calibration_result', {}).get('calibration_quality', {}).get('overall_quality', 0) or 0
                spectral_data.overall_quality_score = (
                    (spectral_data.data_quality_score or 0) * 0.4 +
                    (spectral_data.metadata_quality_score or 0) * 0.3 +
                    (spectral_data.calibration_quality_score or 0) * 0.3
                )
                spectral_data.is_processed = True
                spectral_data.processing_date = django_timezone.now()
                spectral_data.save()
                
                # Generate and render the Quarto HTML report
                report_obj = results.get('report')
                report_obj = report_obj if hasattr(report_obj, 'to_dict') else None
                report_dict = report_obj.to_dict() if report_obj else {}
                
                html_file_path = os.path.join(settings.REPORT_DIR, f"{spectral_data.id}.html")
                html_content = ''
                try:
                    if report_obj is not None:
                        render_result = asyncio.run(
                            reporting_agent.render_report(report_obj, settings.REPORT_DIR)
                        )
                        candidate_html = render_result.get('html_file')
                        if candidate_html and os.path.exists(candidate_html):
                            html_file_path = candidate_html
                        # Prefer the embeddable fragment (scoped styles, no
                        # <html>/<head> wrapper) so the report renders cleanly
                        # inside the Django page via {{ report.html_content|safe }}.
                        html_content = render_result.get('html_content') or ''
                        if not html_content and candidate_html and os.path.exists(candidate_html):
                            with open(candidate_html, 'r', encoding='utf-8') as hf:
                                html_content = hf.read()
                except Exception as re:
                    logger.error(f'Error rendering Quarto report: {re}')
                
                report = Report(
                    spectral_data=spectral_data,
                    report_type='spectral_analysis',
                    title=f"Analysis Report - {spectral_data.original_filename}",
                    file_path=html_file_path,
                    quarto_content=json.dumps(report_dict, indent=2, default=str),
                    html_content=html_content,
                    python_source=json.dumps(report_dict.get('python_source', []), indent=2, default=str),
                    is_generated=bool(html_content),
                    generation_date=django_timezone.now()
                )
                report.save()
                
                # Log the analysis
                SystemLog.objects.create(
                    level='INFO',
                    message=f'Analysis completed for {spectral_data.original_filename}',
                    module='analysis.views',
                    function='analysis_detail',
                    context={'analysis_id': str(spectral_data.id)}
                )
                
                messages.success(request, 'Analysis completed successfully!')
                
            except Exception as e:
                logger.error(f'Error performing analysis: {e}', exc_info=True)
                messages.error(request, f'Error performing analysis: {str(e)}')
                # Mark as processed to avoid retrying the same failing analysis on
                # every reload; user can re-upload a corrected file to retry.
                spectral_data.is_processed = True
                spectral_data.processing_date = django_timezone.now()
                spectral_data.save()
    
    # Get analysis results
    analysis_results = spectral_data.analysis_results
    calibration_results = spectral_data.calibration_results
    metadata_quality = spectral_data.metadata_quality_results
    
    # Get report
    report = Report.objects.filter(spectral_data=spectral_data).first()
    
    context = {
        'page_title': f'Analysis: {spectral_data.original_filename}',
        'spectral_data': spectral_data,
        'analysis_results': analysis_results,
        'calibration_results': calibration_results,
        'metadata_quality': metadata_quality,
        'report': report,
        'quality_grade': spectral_data.get_quality_grade(),
        'is_owner': request.user == spectral_data.user or not spectral_data.user
    }
    
    return render(request, 'analysis/detail.html', context)


def delete_analysis(request, analysis_id):
    """Delete a stale/failed analysis record.

    Removes the SpectralData row, its reports, and the indexed vector from
    the Qdrant/numpy search backend. POST-only to avoid CSRF-unsafe GET
    deletion. Redirects back to the analyses overview.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    spectral_data = get_object_or_404(SpectralData, pk=analysis_id)
    filename = spectral_data.original_filename
    # Remove the on-disk source file if it is private to this analysis.
    file_path = getattr(spectral_data, 'file_path', '')
    # Drop the vector index entry so stale data no longer shows up in
    # comparison / similarity search results.
    try:
        spectral_search_agent.remove_analysis(str(spectral_data.id))
    except Exception as e:
        logger.warning(f'Failed to remove analysis {spectral_data.id} from vector index: {e}')
    # Cascade-adjacent cleanup: reports reference this SpectralData.
    Report.objects.filter(spectral_data=spectral_data).delete()
    spectral_data.delete()
    logger.info(f'Deleted analysis id={analysis_id} ({filename!r}) by request.')
    messages.success(request, f'Deleted analysis \u201c{filename}\u201d.')
    return redirect('analyses_overview')


def analysis_report(request, analysis_id):
    """Analysis report view."""
    spectral_data = get_object_or_404(SpectralData, pk=analysis_id)
    report = Report.objects.filter(spectral_data=spectral_data).first()

    # No report row yet. Two cases:
    #  * is_processed=False -> the analysis has not run yet (or a re-run is
    #    pending). The detail page runs the pipeline on a GET and creates the
    #    Report row; tell the user to open it (the auto-refresh will then flip
    #    to the report once the row appears).
    #  * is_processed=True  -> the analysis ran but produced no report (it
    #    failed, or the report step errored). Offer an explicit re-run.
    if not report:
        analysis_pending = not spectral_data.is_processed
        if analysis_pending:
            messages.info(
                request,
                'The analysis has not run yet. Open the analysis page to start '
                'it (the report is generated automatically when it finishes); '
                'this page will refresh itself while you wait.'
            )
        else:
            messages.info(
                request,
                'The analysis ran but produced no report (it may have failed, '
                'or the report step errored). Re-run the analysis to produce one.'
            )
        return render(
            request,
            'analysis/report.html',
            {
                'page_title': f'Report: {spectral_data.original_filename}',
                'spectral_data': spectral_data,
                'report': None,
                'analysis_pending': analysis_pending,
            },
        )

    context = {
        'page_title': f'Report: {report.title}',
        'spectral_data': spectral_data,
        'report': report
    }

    return render(request, 'analysis/report.html', context)


def download_analysis(request, analysis_id):
    """Download analysis results."""
    spectral_data = get_object_or_404(SpectralData, pk=analysis_id)
    
    # Create download package
    import zipfile
    import io
    
    # Create in-memory zip file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add original file
        if os.path.exists(spectral_data.file_path):
            zip_file.write(spectral_data.file_path, 
                          os.path.basename(spectral_data.original_filename))
        
        # Add processed data
        processed_data = {
            'wavelengths': spectral_data.analysis_results.get('processed_data', {}).get('wavelengths', []),
            'intensities': spectral_data.analysis_results.get('processed_data', {}).get('intensities', []),
            'metadata': spectral_data.metadata
        }
        zip_file.writestr('processed_data.json', json.dumps(processed_data, indent=2))
        
        # Add analysis results
        zip_file.writestr('analysis_results.json', 
                         json.dumps(spectral_data.analysis_results, indent=2))
        
        # Add calibration results
        zip_file.writestr('calibration_results.json', 
                         json.dumps(spectral_data.calibration_results, indent=2))
        
        # Add metadata quality results
        zip_file.writestr('metadata_quality.json', 
                         json.dumps(spectral_data.metadata_quality_results, indent=2))
        
        # Add report
        report = Report.objects.filter(spectral_data=spectral_data).first()
        if report:
            zip_file.writestr('report.html', report.html_content or '')
            zip_file.writestr('report.qmd', report.quarto_content)
            zip_file.writestr('python_source.py', report.python_source or '')
    
    # Return zip file
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="analysis_{spectral_data.id}.zip"'
    return response


def chat_interface(request, analysis_id=None):
    """Chat interface with AI agents."""
    spectral_data = None
    if analysis_id:
        spectral_data = get_object_or_404(SpectralData, pk=analysis_id)
    
    # Get or create chat session
    session_id = request.session.get('chat_session_id')
    chat_session = None
    
    if session_id:
        try:
            chat_session = ChatSession.objects.get(id=session_id)
        except ChatSession.DoesNotExist:
            pass
    
    if not chat_session:
        chat_session = ChatSession(
            user=request.user if request.user.is_authenticated else None,
            spectral_data=spectral_data,
            session_name=f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            agent_type='analysis'
        )
        chat_session.save()
        request.session['chat_session_id'] = str(chat_session.id)
    
    if request.method == 'POST':
        form = ChatForm(request.POST)
        if form.is_valid():
            message = form.cleaned_data['message']
            
            # Add user message
            chat_session.messages.append({
                'sender': 'user',
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
            chat_session.save()
            
            # Generate AI response
            try:
                import asyncio
                import httpx

                # Build a short context summary of the current analysis so the
                # assistant can answer questions about this dataset.
                ctx_lines = []
                if spectral_data:
                    ctx_lines.append(f"File: {spectral_data.original_filename}")
                    ctx_lines.append(f"Spectrometer: {spectral_data.spectrometer_type or 'auto-detected'}")
                    ctx_lines.append(f"Data points: {len(spectral_data.wavelengths or [])}")
                    ar = spectral_data.analysis_results or {}
                    cr = spectral_data.calibration_results or {}
                    if ar.get('quality_score') is not None:
                        ctx_lines.append(f"Spectral quality score: {ar['quality_score']}")
                    cal = cr.get('analyte_calibration') if isinstance(cr, dict) else None
                    if cal:
                        ctx_lines.append(
                            f"NIR->Brix calibration: {cal.get('method')} "
                            f"R2_cv={cal.get('r_squared_cv', 0):.3f} "
                            f"RMSE_cv={cal.get('rmse_cv', 0):.3f} Brix")
                    sm = (spectral_data.metadata or {}).get('standard_metadata') or {}
                    if sm:
                        ctx_lines.append(
                            f"Metadata: {', '.join(f'{k}={v}' for k, v in list(sm.items())[:6])}")
                context_summary = chr(10).join(ctx_lines)

                async def get_ai_response():
                    ollama_url = settings.AGENT_CONFIG.get(
                        'ollama_url', 'http://localhost:11434')
                    model = os.environ.get('NIR_OLLAMA_MODEL', 'mistral')
                    system_prompt = (
                        "You are the NIR Intelligence Platform assistant, an expert "
                        "in near-infrared spectroscopy, spectrometer calibration, and "
                        "tomato ripeness (Brix) analysis. Answer the user's question "
                        "about their spectral data concisely and in the user's language. "
                        "Use the provided analysis context where relevant.")
                    prompt = f"{system_prompt}\n\nAnalysis context:\n{context_summary}\n\nUser question: {message}"
                    try:
                        async with httpx.AsyncClient(timeout=60) as client:
                            resp = await client.post(
                                f"{ollama_url}/api/generate",
                                json={"model": model, "prompt": prompt, "stream": False},
                            )
                            if resp.status_code == 200:
                                data = resp.json()
                                return data.get('response', '').strip() or (
                                    "No response from the model.")
                            return f"(Ollama returned HTTP {resp.status_code}). Try starting the Ollama container."
                    except (httpx.HTTPError, Exception) as oe:
                        logger.warning(f"Ollama unavailable, using local fallback: {oe}")
                        return _local_chat_fallback(message, context_summary)

                def _local_chat_fallback(q: str, ctx: str) -> str:
                    ql = q.lower()
                    # Reference spectral_data from the enclosing closure so the
                    # canned reply can surface the real calibration numbers.
                    cal = None
                    if spectral_data and isinstance(spectral_data.calibration_results, dict):
                        cal = spectral_data.calibration_results.get('analyte_calibration')
                    if any(k in ql for k in ('brix', 'kalibrier', 'calibrat', 'ripeness', 'reifegrad')):
                        if cal:
                            return (
                                f"The NIR->Brix calibration is a {cal.get('method', 'PLS')} "
                                f"regression of the 18 SparkFun Triad channels onto the "
                                f"refractometer Brix reference ({cal.get('num_samples')} "
                                f"samples, {cal.get('num_components')} components). "
                                f"Cross-validated (5-fold): R2_cv={cal.get('r_squared_cv', 0):.3f}, "
                                f"RMSE_cv={cal.get('rmse_cv', 0):.3f} Brix. "
                                f"See the Calibration card on the analysis page for the "
                                f"full equation and calibration curve. Note: Ollama is "
                                f"offline, so this is a canned answer - start the "
                                f"nir_ollama container for full AI replies.")
                        return (
                            "The NIR->Brix calibration is a PLS regression of the 18 "
                            "SparkFun Triad channels onto the refractometer Brix "
                            "reference. It is cross-validated (5-fold); see the "
                            "Calibration card on the analysis page for R2_cv and "
                            "RMSE_cv. Note: Ollama is offline, so this is a canned "
                            "answer - start the nir_ollama container for full AI replies.")
                    if any(k in ql for k in ('metadata', 'metadaten', 'quality')):
                        sm = (spectral_data.metadata or {}).get('standard_metadata') if spectral_data else {}
                        mq = (spectral_data.metadata or {}).get('metadata_quality') if spectral_data else None
                        grade = mq.get('grade') if isinstance(mq, dict) else None
                        return (
                            "The Data Loader Agent extracts structured metadata "
                            "from the file header (instrument, wavelengths, "
                            "temperature, operators, Brix reference) and rates it"
                            + (f" (current grade: {grade})" if grade else "") + ". "
                            "Use the 'Extracted Metadata' panel to add missing "
                            "fields and re-run the analysis. (Ollama offline - "
                            "canned answer.)")
                    return (
                        "I'm the NIR Intelligence assistant. I can help interpret "
                        "your spectral data, the Brix calibration, and metadata. "
                        "The Ollama LLM is currently offline, so this is a local "
                        "fallback reply - start the nir_ollama container for full "
                        "AI responses.\n\nAnalysis context:\n" + (ctx or 'none'))
                
                ai_response = asyncio.run(get_ai_response())
                
                # Add AI response
                chat_session.messages.append({
                    'sender': 'ai',
                    'message': ai_response,
                    'timestamp': datetime.now().isoformat()
                })
                chat_session.save()
                
            except Exception as e:
                logger.error(f'Error getting AI response: {e}')
                chat_session.messages.append({
                    'sender': 'system',
                    'message': f'Error: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })
                chat_session.save()
            
            return redirect('chat_interface', analysis_id=analysis_id)
    else:
        form = ChatForm()
    
    context = {
        'page_title': 'Chat with AI Agents',
        'chat_session': chat_session,
        'form': form,
        'spectral_data': spectral_data
    }
    
    return render(request, 'analysis/chat.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def api_analyze(request):
    """API endpoint for spectral analysis."""
    try:
        data = json.loads(request.body)
        
        # Validate data
        if 'wavelengths' not in data or 'intensities' not in data:
            return JsonResponse({'error': 'Missing wavelengths or intensities'}, status=400)
        
        # Perform analysis
        import asyncio
        
        async def perform_analysis():
            spectral_result = await spectral_agent.analyze_spectral_data(data=data)
            metadata_result = await metadata_agent.evaluate_metadata_quality(
                data.get('metadata', {})
            )
            calibration_result = await calibration_agent.generate_calibration(data)
            
            return {
                'spectral': spectral_result.to_dict(),
                'metadata': metadata_result.to_dict(),
                'calibration': calibration_result.to_dict()
            }
        
        results = asyncio.run(perform_analysis())
        
        return JsonResponse({'status': 'success', 'results': results})
        
    except Exception as e:
        logger.error(f'API analysis error: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_chat(request):
    """API endpoint for chat with AI agents."""
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # For now, return mock response
        # In production, this would call the MCP server or Ollama directly
        response = {
            'message': f"I received your message: {message[:50]}...",
            'sender': 'ai',
            'timestamp': datetime.now().isoformat()
        }
        
        return JsonResponse({'status': 'success', 'response': response})
        
    except Exception as e:
        logger.error(f'API chat error: {e}')
        return JsonResponse({'error': str(e)}, status=500)


def about(request):
    """About page view."""
    context = {
        'page_title': 'About NIR Intelligence Platform',
        'app_name': settings.NIR_PLATFORM['app_name'],
        'version': settings.NIR_PLATFORM['version'],
        'description': settings.NIR_PLATFORM['description']
    }
    
    return render(request, 'analysis/about.html', context)


def documentation(request):
    """Documentation page view."""
    context = {
        'page_title': 'Documentation',
        'docs': [
            {
                'title': 'Getting Started',
                'content': 'Learn how to use the NIR Intelligence Platform for spectral analysis.',
                'sections': [
                    'Installation',
                    'Uploading Data',
                    'Running Analysis',
                    'Viewing Reports'
                ]
            },
            {
                'title': 'User Guide',
                'content': 'Detailed guide on all platform features and capabilities.',
                'sections': [
                    'Spectral Analysis',
                    'Metadata Quality',
                    'Calibration',
                    'Reporting',
                    'Federated Learning'
                ]
            },
            {
                'title': 'API Reference',
                'content': 'Technical documentation for developers.',
                'sections': [
                    'REST API',
                    'WebSocket API',
                    'Integration Examples'
                ]
            },
            {
                'title': 'DIY Spectrometer Guide',
                'content': 'Build your own NIR spectrometer for Open Science.',
                'sections': [
                    'Components',
                    'Assembly Instructions',
                    'Calibration',
                    'Usage Tips'
                ]
            }
        ]
    }
    
    return render(request, 'analysis/docs.html', context)
