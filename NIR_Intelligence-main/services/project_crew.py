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
from datetime import datetime
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

    query = {
        "wavelengths": dataset.get("preview", {}).get("wavelengths", []),
        "intensities": dataset.get("preview", {}).get("intensities", []),
    }
    if not query["wavelengths"]:
        return {"agent": "faiss_similarity", "title": "Spektren-Datenbankvergleich",
                "status": "failed", "data": {"reason": "Keine Messdaten"}}

    references = []
    reference_ids = []
    for other in (project.preparation_report or {}).get("datasets", []):
        if other.get("usable") and other.get("file_id") != dataset.get("file_id"):
            references.append({
                "wavelengths": other.get("preview", {}).get("wavelengths", []),
                "intensities": other.get("preview", {}).get("intensities", []),
            })
            reference_ids.append(other.get("file_name", other.get("file_id")))

    output = FaissAgent().execute({
        "reference_spectra": references,
        "reference_ids": reference_ids,
        "query_spectrum": query,
        "top_k": 5,
    })
    return _agent_report("faiss_similarity", "Spektren-Datenbankvergleich (FAISS)", output)


def _per_agent_reports(crew, result, project, dataset) -> List[Dict[str, Any]]:
    """Build the per-agent report sections from a real crew result."""
    sections: List[Dict[str, Any]] = []

    if result.spectral_analysis is not None:
        sections.append({
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
        })
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
        sections.append(_agent_report(
            "sensor_quality", "Sensorqualität (Drift, Rauschen)", type("O", (), {
                "status": type("S", (), {"name": "COMPLETED"})(),
                "data": result.sensor_quality_results,
            })()))
    if result.statistical_analysis_results:
        sections.append(_agent_report(
            "statistical_analysis", "Statistische Analyse (PCA, PLS, Cluster)", type("O", (), {
                "status": type("S", (), {"name": "COMPLETED"})(),
                "data": result.statistical_analysis_results,
            })()))
    if result.neural_network_results:
        sections.append(_agent_report(
            "neural_network", "Neuronale Netzwerkanalyse (CNN, MLP)", type("O", (), {
                "status": type("S", (), {"name": "COMPLETED"})(),
                "data": result.neural_network_results,
            })()))
    if result.calibration_results:
        sections.append(_agent_report(
            "calibration", "Kalibration (PLS, PCR)", type("O", (), {
                "status": type("S", (), {"name": "COMPLETED"})(),
                "data": result.calibration_results,
            })()))
    sections.append(_similarity_section(project, dataset))
    return sections


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
                      **(dataset.get('metadata') or {})},
            file_paths=[],
            analysis_mode=AnalysisMode.STANDARD,
            report_type=ReportType.COMPREHENSIVE,
            report_format=ReportFormat.HTML,
            include_calibration=True,
            user_id=str(getattr(project, 'user_id', None) or getattr(getattr(project, 'user', None), 'id', None)),
        )
        result = crew.analyze_sample(request_obj)
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
    project.completed_at = datetime.now()
    project.save(update_fields=['crew_results', 'final_report_path', 'phase',
                                'completed_at', 'updated_at'])
    logger.info('Project crew completed for %s: %s datasets, %s agent reports',
                project.id, len(results), len(all_reports))
    return crew_results
