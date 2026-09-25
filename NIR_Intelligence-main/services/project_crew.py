# NIR Intelligence Platform - Project crew runner (OP10)
# Phase 2 of the project workflow: runs the full NIRAnalysisCrew over every
# usable dataset of a released AnalysisProject, collects one report section
# per agent (content + chart data, from real agent outputs) and generates
# the final comprehensive Quarto report covering original data, code,
# evaluation and graphics (MO 6-9, 13).
import json
import logging
import os
import tempfile
from enum import Enum
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("Service.ProjectCrew")


def _agent_report(agent_key: str, title: str, output) -> Dict[str, Any]:
    """Normalize one agent output into a per-agent report section."""
    completed = getattr(getattr(output, "status", None), "name", "") == "COMPLETED"
    section: Dict[str, Any] = {
        "agent": agent_key,
        "title": title,
        "status": "completed" if completed else "failed",
        "data": _json_safe(getattr(output, "data", {}) or {}),
    }
    if completed:
        for warning in (getattr(output, "data", {}) or {}).get("warnings", []):
            section.setdefault("warnings", []).append(str(warning))
    return section


def _json_safe(data: Any) -> Any:
    """Strict-JSON sanitization (NaN/Infinity -> None, enums -> values), same
    contract as the crew (NIRAnalysisCrew._json_safe plus enum conversion so
    the report template renderer can serialize agent outputs)."""
    import math

    if isinstance(data, float):
        return data if math.isfinite(data) else None
    if isinstance(data, dict):
        return {k: _json_safe(v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [_json_safe(i) for i in data]
    if isinstance(data, Enum):  # real enum members only (duck typing would
        return data.value        # misfire on dataclasses with a .value field)
    if hasattr(data, "__dict__") and not isinstance(data, str):  # dataclasses
        return {k: _json_safe(v) for k, v in vars(data).items()}
    return data


def _similarity_section(project, dataset: Dict[str, Any]) -> Dict[str, Any]:
    """Compare the released dataset against the spectral database (MO 11-12):
    reference set = the other usable datasets of the project plus the repo
    reference spectra when available. Uses the FAISS agent (S5 engine)."""
    from agents.faiss_agent import FaissAgent

    wavelengths = dataset.get("preview", {}).get("wavelengths", [])
    intensities = dataset.get("preview", {}).get("intensities", [])
    if not wavelengths or not intensities:
        return {"agent": "faiss_similarity", "title": "Spektren-Datenbankvergleich",
                "status": "failed", "data": {"reason": "Keine Messdaten"}}
    query = {
        "data": {"wavelength": wavelengths, "intensity": intensities},
        "wavelength_column": "wavelength",
        "intensity_column": "intensity",
    }

    references = []
    reference_ids = []
    for other in (project.preparation_report or {}).get("datasets", []):
        if other.get("usable") and other.get("file_id") != dataset.get("file_id"):
            other_wl = other.get("preview", {}).get("wavelengths", [])
            other_it = other.get("preview", {}).get("intensities", [])
            if not other_wl or not other_it:
                continue
            references.append({
                "data": {"wavelength": other_wl, "intensity": other_it},
                "wavelength_column": "wavelength",
                "intensity_column": "intensity",
            })
            reference_ids.append(other.get("file_name", other.get("file_id")))

    # OP15: include the persisted spectral database - records visible to
    # the project owner on the same wavelength grid (no cross-grid
    # interpolation by design); records from this project are excluded
    # (already covered as sibling datasets above).
    db_sources = 0
    try:
        from services.spectrum_database import references_for_dataset
        user_id = getattr(project, 'user_id', None)
        if user_id:
            db = references_for_dataset(user_id, dataset,
                                        exclude_project_id=project.id)
            references.extend(db['references'])
            reference_ids.extend(f'Datenbank: {i}' for i in db['ids'])
            db_sources = len(db['references'])
    except Exception:
        logger.exception('Spectral database lookup failed (non-fatal)')

    output = FaissAgent().execute({
        "reference_spectra": references,
        "reference_ids": reference_ids,
        "query_spectrum": query if references else None,
        "top_k": 5,
    })
    section = _agent_report("faiss_similarity", "Spektren-Datenbankvergleich (FAISS)", output)
    section['data']['database_references'] = db_sources

    # OP22: overlay the three most similar spectra on the query curve
    try:
        matches = (section.get('data') or {}).get('matches') or []
        if matches and references:
            reference_curves = {
                rid: (ref.get('data', {}).get('wavelength'),
                      ref.get('data', {}).get('intensity'))
                for rid, ref in zip(reference_ids, references)
            }
            from services.similarity_charts import similarity_top3_chart_data_url
            url = similarity_top3_chart_data_url(
                wavelengths, intensities, matches, reference_curves)
            if url:
                section['charts'] = {'similarity_top3': url}
                section['charts_note'] = (
                    'Messung mit den 3 ähnlichsten Spektren aus Datenbank '
                    'und Projekt')
    except Exception:
        logger.exception('Similarity top-3 chart rendering failed (non-fatal)')
    return section


def _per_agent_reports(crew, result, project, dataset) -> List[Dict[str, Any]]:
    """Build the per-agent report sections from a real crew result."""
    sections: List[Dict[str, Any]] = []

    if result.spectral_analysis is not None:
        spectral_section = {
            "agent": "spectral_analysis",
            "title": "Spektralanalyse (Qualität)",
            "status": "completed",
            "data": {
                "quality_score": result.spectral_analysis.quality_score,
                "quality_grade": result.spectral_analysis.quality_grade.value,
                "wavelength_range": list(result.spectral_analysis.wavelength_range),
                "data_points": getattr(result.spectral_analysis, "data_points", 0),
                "issues_detected": [
                    i.value if hasattr(i, "value") else str(i)
                    for i in getattr(result.spectral_analysis, "issues_detected", [])
                ],
                "recommendations": list(result.spectral_analysis.recommendations or []),
            },
        }
        preview_wl = dataset.get('preview', {}).get('wavelengths', [])
        preview_it = dataset.get('preview', {}).get('intensities', [])
        if preview_wl and preview_it:
            try:
                from services.similarity_charts import spectrum_chart_data_url
                url = spectrum_chart_data_url(
                    preview_wl, preview_it,
                    title='Hochgeladenes Spektrum (Messdaten)')
                if url:
                    spectral_section['charts'] = {'spectrum': url}
                    spectral_section['charts_note'] = (
                        'Spektrum der hochgeladenen Messdaten')
            except Exception:
                logger.exception('Spectrum chart rendering failed (non-fatal)')
        sections.append(spectral_section)
    if result.metadata_quality is not None:
        sections.append({
            "agent": "metadata_quality",
            "title": "Metadatenbewertung",
            "status": "completed",
            "data": {
                "overall_quality_score": result.metadata_quality.overall_quality_score,
                "overall_quality_grade": result.metadata_quality.overall_quality_grade.value,
                "recommendations": list(result.metadata_quality.recommendations or []),
            },
        })
    if result.sensor_quality_results:
        sensor_section = _agent_report(
            "sensor_quality", "Sensorqualität (Drift, Rauschen)", type("O", (), {
                "status": type("S", (), {"name": "COMPLETED"})(),
                "data": result.sensor_quality_results,
            })())
        measurement_samples = (dataset.get('measurement_samples') or [])
        # OP29: deduplicated optimization suggestions - the three existing
        # recommendation sources (analytical parameter recommendations,
        # data-preparation heuristics, generic sensor-quality texts) merged
        # into one prioritized list per parameter - plus the assessment of
        # the settings recorded in the dataset metadata.
        try:
            from services.sensor_catalog import (
                assess_settings,
                get_optimization_suggestions,
            )
            parameter_recommendations = list(
                getattr(result, 'parameter_recommendations', []) or [])
            merged_suggestions = get_optimization_suggestions(
                sensor_results=result.sensor_quality_results,
                parameter_recommendations=parameter_recommendations,
                crew_recommendations=list(result.recommendations or []),
            )
            sensor_section['data'] = dict(sensor_section.get('data') or {})
            if merged_suggestions:
                sensor_section['data']['optimization_suggestions'] = merged_suggestions
            metadata = dataset.get('metadata') or {}
            setting_assessment = assess_settings(metadata)
            sensor_section['data']['setting_assessment'] = setting_assessment
        except Exception:
            logger.exception('OP29 sensor catalog merge failed (non-fatal)')
        if measurement_samples:
            try:
                from services.sensor_charts import (
                    sensor_dashboard_data_urls, sensor_recommendations)
                recommendations = sensor_recommendations(result.sensor_quality_results)
                if recommendations:
                    sensor_section['data'] = dict(sensor_section.get('data') or {})
                    sensor_section['data']['optimization_recommendations'] = recommendations
                sensor_section['charts'] = sensor_dashboard_data_urls(
                    measurement_samples, result.sensor_quality_results,
                    dataset.get('preview', {}).get('wavelengths', []),
                )
                if sensor_section.get('charts'):
                    sensor_section['charts_note'] = (
                        "SPC-Dashboard (Kontrollkarte, Overlay, Kanal-Rauschen, Gauge)")
            except Exception:
                logger.exception('Sensor dashboard rendering failed (non-fatal)')
        sections.append(sensor_section)
    if result.statistical_analysis_results:
        section = _agent_report(
            "statistical_analysis", "Statistische Analyse (PCA, PLS, Cluster)", type("O", (), {
                "status": type("S", (), {"name": "COMPLETED"})(),
                "data": result.statistical_analysis_results,
            })())
        measurement_samples = (dataset.get('measurement_samples') or [])
        if measurement_samples:
            try:
                from services.pca_charts import pca_chart_data_urls
                section['charts'] = pca_chart_data_urls(
                    measurement_samples,
                    dataset.get('preview', {}).get('wavelengths', []),
                )
                section['charts_note'] = (
                    f"{len(section.get('charts', {}))} PCA-Diagramme aus "
                    f"{len(measurement_samples)} Messreplikaten")
            except Exception:
                logger.exception('PCA chart rendering failed (non-fatal)')
        sections.append(section)
    if result.neural_network_results:
        nn_section = _agent_report(
            "neural_network", "Neuronale Netzwerkanalyse (CNN, MLP)", type("O", (), {
                "status": type("S", (), {"name": "COMPLETED"})(),
                "data": result.neural_network_results,
            })())
        calibration_samples = (dataset.get('calibration_samples') or [])
        reference_values = (dataset.get('reference_values') or [])
        if calibration_samples and reference_values:
            try:
                from services.xai_charts import xai_chart_data_urls
                nn_section['charts'] = xai_chart_data_urls(
                    calibration_samples, reference_values,
                    dataset.get('preview', {}).get('wavelengths', []),
                    epochs=60,
                    target_name=(dataset.get('metadata', {})
                                 .get('target_name') or 'Zielwert'),
                )
                if nn_section.get('charts'):
                    nn_section['charts_note'] = (
                        f"{len(nn_section['charts'])} XAI-Diagramme aus "
                        f"{len(calibration_samples)} Kalibrationsmessungen"
                    )
            except Exception:
                logger.exception('XAI chart rendering failed (non-fatal)')
        sections.append(nn_section)
    if result.calibration_results:
        cal_section = _agent_report(
            "calibration", "Kalibration (PLS, PCR)", type("O", (), {
                "status": type("S", (), {"name": "COMPLETED"})(),
                "data": result.calibration_results,
            })())
        calibration_samples = (dataset.get('calibration_samples') or [])
        reference_values = (dataset.get('reference_values') or [])
        if calibration_samples and reference_values:
            try:
                from services.calibration_charts import calibration_chart_data_urls
                cal_section['charts'] = calibration_chart_data_urls(
                    calibration_samples, reference_values,
                    dataset.get('preview', {}).get('wavelengths', []),
                    target_name=(dataset.get('metadata', {})
                                 .get('target_name') or 'Zielwert'),
                )
                if cal_section.get('charts'):
                    cal_section['charts_note'] = (
                        f"{len(cal_section['charts'])} Kalibrierungs-Diagramme aus "
                        f"{len(calibration_samples)} Kalibrationsmessungen")
            except Exception:
                logger.exception('Calibration chart rendering failed (non-fatal)')
        sections.append(cal_section)
    sections.append(_similarity_section(project, dataset))
    sections.append(_outlier_section(dataset))
    return sections


def _outlier_section(dataset: Dict[str, Any]) -> Dict[str, Any]:
    """OP37: documented outlier analysis for the dataset's measurement
    replicas - robust z-score (SNV + MAD) against the median spectrum,
    rendered charts and German findings. Never raises; honest verdict
    when there are too few measurements to assess."""
    from services.outlier_analysis import analyse_dataset
    try:
        result = analyse_dataset(dataset)
    except Exception:
        logger.exception('Outlier analysis failed (non-fatal)')
        result = {'file_name': dataset.get('file_name', 'Datensatz'),
                  'verdict': {'assessable': False,
                              'reason': 'interner Fehler'},
                  'charts': {}, 'findings': []}
    section: Dict[str, Any] = {
        'agent': 'outlier_analysis',
        'title': 'Ausreisser-Analyse',
        'status': 'completed',
        'data': {
            'file_name': result['file_name'],
            'assessable': bool(result['verdict'].get('assessable')),
            'measurement_count': result['verdict'].get('measurement_count', 0),
            'outlier_indices': result['verdict'].get('outlier_indices', []),
            'threshold': result['verdict'].get('threshold'),
            'findings': result['findings'],
        },
    }
    if result['charts']:
        section['charts'] = result['charts']
        section['charts_note'] = (
            f"{len(result['charts'])} Ausreisser-Diagramme aus "
            f"{result['verdict'].get('measurement_count', 0)} Messungen")
    return section


def _metadata_quality_dict(result) -> Dict[str, Any]:
    """Convert the MetadataQualityResult to a plain dict the reporting agent
    can render (same field conversion contract as analyze_sample)."""
    if result is None or result.metadata_quality is None:
        return {}
    data = _json_safe(result.metadata_quality.__dict__)
    fields = []
    for field in data.get("fields_assessed", []):
        if hasattr(field, "__dict__"):
            fields.append({k: (v.value if hasattr(v, "value") else v)
                           for k, v in field.__dict__.items()})
        else:
            fields.append(field)
    data["fields_assessed"] = fields
    if hasattr(data.get("overall_quality_grade"), "value"):
        data["overall_quality_grade"] = data["overall_quality_grade"].value
    return data


def _generate_final_report(project, crew, result, per_agent: List[Dict[str, Any]],
                            full_series: List[Dict[str, Any]] = None) -> str:
    """Generate the final comprehensive project report (OP11: rendered HTML
    with embedded charts, original data, source code and evaluation) and
    return its file path. Falls back to the reporting agent's template
    rendering when the report builder is unavailable (same behaviour as
    OP7 for single files)."""
    from services.project_report import generate_final_html_report

    return generate_final_html_report(project, {
        'request_id': result.request_id,
        'overall_quality_score': result.overall_quality_score,
        'recommendations': list(result.recommendations or []),
        'warnings': list(result.warnings or []),
        'errors': list(result.errors or []),
        'processing_time': result.processing_time,
        'datasets_analyzed': len(full_series) if full_series is not None else None,
        'per_agent_reports': per_agent,
    }, full_series=full_series)


def _generate_final_report_legacy(project, crew, result, per_agent: List[Dict[str, Any]]) -> str:
    """Legacy single-file path (OP7 behaviour): reporting agent template
    rendering. Kept as the fallback when the OP11 report builder fails."""
    from agents.reporting_agent import ReportType, ReportFormat

    output_dir = Path(tempfile.mkdtemp(prefix='project_report_'))
    data = {
        "sample_id": str(project.id),
        "project_name": project.name,
        "report_type": ReportType.COMPREHENSIVE.value,
        "spectral_analysis": (
            _json_safe(result.spectral_analysis.__dict__)
            if result.spectral_analysis else {}
        ),
        "metadata_quality_result": _metadata_quality_dict(result),
        "processed_data": {},
        "calibration_results": _json_safe(result.calibration_results or {}),
        "sensor_quality_results": _json_safe(result.sensor_quality_results or {}),
        "statistical_analysis_results": _json_safe(result.statistical_analysis_results or {}),
        "neural_network_results": _json_safe(result.neural_network_results or {}),
        "per_agent_reports": _json_safe(per_agent),
        "recommendations": list(result.recommendations or []),
        "warnings": list(result.warnings or []),
        "errors": list(result.errors or []),
        "overall_quality_score": result.overall_quality_score,
        "request_id": result.request_id,
        "analysis_mode": "project",
        "privacy_level": result.privacy_level.value,
        "include_calibration": True,
    }
    if result.spectral_analysis is not None:
        data["spectral_analysis"]["quality_grade"] = result.spectral_analysis.quality_grade.value
    report = crew.reporting_agent.generate_report(
        report_type=ReportType.COMPREHENSIVE,
        data=data,
        format=ReportFormat.HTML,
        sample_id=str(project.id),
    )
    return report.file_path if report.file_path else ""


def run_project_crew(project) -> Dict[str, Any]:
    """Run phase 2 for a released project: full crew analysis over every
    usable dataset, per-agent reports, final Quarto report. Stores the
    results on project.crew_results and returns them."""
    import sys

    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from agents.nir_analysis_crew import (
        NIRAnalysisCrew, CrewConfiguration, AnalysisRequest, AnalysisMode,
    )
    from agents.reporting_agent import ReportType, ReportFormat

    preparation = project.preparation_report or {}
    datasets = [d for d in preparation.get('datasets', []) if d.get('usable')]
    if not datasets:
        raise ValueError('No usable datasets in project preparation report')

    try:
        import crewai  # noqa: F401
        import requests as _requests
        _llm_up = _requests.get(
            f"{os.environ.get('OLLAMA_URL', 'http://localhost:11434').rstrip('/')}/api/tags",
            timeout=2,
        ).ok
    except Exception:
        _llm_up = False

    config = CrewConfiguration(
        enable_crewai=_llm_up,
        temp_dir=tempfile.mkdtemp(prefix='project_crew_'),
        output_dir=str(Path(project_root) / 'output' / 'projects'),
    )
    crew = NIRAnalysisCrew(config)

    all_reports: List[Dict[str, Any]] = []
    results = []
    for dataset in datasets:
        wavelengths = dataset.get('preview', {}).get('wavelengths', [])
        intensities = dataset.get('preview', {}).get('intensities', [])
        if not wavelengths:
            continue
        request_obj = AnalysisRequest(
            sample_id=dataset.get('file_name', str(dataset.get('file_id'))),
            spectral_data={'wavelengths': wavelengths, 'intensities': intensities},
            metadata={'file_name': dataset.get('file_name', ''),
                      'file_extension': dataset.get('file_extension', ''),
                      'measurement_samples': dataset.get('measurement_samples') or [],
                      'calibration_samples': dataset.get('calibration_samples') or [],
                      **({'reference_values': dataset['reference_values']}
                         if dataset.get('reference_values') else {}),
                      **(dataset.get('metadata') or {})},
            file_paths=[],
            analysis_mode=AnalysisMode.STANDARD,
            report_type=ReportType.COMPREHENSIVE,
            report_format=ReportFormat.HTML,
            include_calibration=True,
            user_id=str(getattr(project, 'user_id', None) or getattr(getattr(project, 'user', None), 'id', None)),
        )
        result = crew.analyze_sample(request_obj)
        saturated = int((dataset.get('metadata') or {}).get('saturated_measurements') or 0)
        if saturated:
            result.warnings.append(
                f"{dataset.get('file_name')}: {saturated} Messung(en) mit "
                "übersteuertem (saturiertem) Kanalwert - ADC-Überlauf des Sensors, "
                "diese Messungen wurden von der Replica-Analyse ausgeschlossen."
            )
        results.append(result)
        all_reports.extend(_per_agent_reports(crew, result, project, dataset))

    if not results:
        raise ValueError('Crew analysis produced no results')

    primary = results[0]
    full_series = [{'file_name': d.get('file_name', str(d.get('file_id'))),
                    'wavelengths': d.get('preview', {}).get('wavelengths', []),
                    'intensities': d.get('preview', {}).get('intensities', [])}
                   for d in datasets]
    crew_results: Dict[str, Any] = {
        'request_id': primary.request_id,
        'overall_quality_score': primary.overall_quality_score,
        'recommendations': primary.recommendations,
        'warnings': primary.warnings,
        'errors': primary.errors,
        'processing_time': primary.processing_time,
        'datasets_analyzed': len(results),
        'per_agent_reports': all_reports,
        'spectral_series': {
            'wavelengths': datasets[0].get('preview', {}).get('wavelengths', []),
            'intensities': datasets[0].get('preview', {}).get('intensities', []),
        },
    }
    project.crew_results = crew_results

    try:
        final_path = _generate_final_report(project, crew, primary, all_reports,
                                            full_series=full_series)
    except Exception:
        logger.exception('OP11 report builder failed, falling back to the '
                         'reporting agent template rendering')
        final_path = _generate_final_report_legacy(project, crew, primary, all_reports)
    project.final_report_path = final_path
    project.phase = 'completed'
    project.completed_at = datetime.now(tz=timezone.utc)
    project.save(update_fields=['crew_results', 'final_report_path', 'phase',
                                'completed_at', 'updated_at'])
    logger.info('Project crew completed for %s: %s datasets, %s agent reports',
                project.id, len(results), len(all_reports))
    return crew_results
