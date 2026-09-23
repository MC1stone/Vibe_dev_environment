# NIR Intelligence Platform - Project ingest service (OP10)
# Phase 1 of the project workflow: turns the files of an AnalysisProject into
# usable datasets (measurement series + metadata) using the S3 format-agnostic
# loader (EnhancedDataPreparationAgent) and assesses metadata quality and
# data usability with improvement recommendations for the user. File-type
# and spectrometer agnostic per the init prompt ground rules.
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("Service.ProjectIngest")


def _finite_pairs(df, wavelength_column, intensity_column):
    """Extract (wavelength, intensity) pairs where both values are finite
    numbers. Tolerates header/metadata rows inside numeric columns (same
    conversion contract as the OP7 crew bridge in file_views.py)."""
    from agents.data_preparation_agent import EnhancedDataPreparationAgent

    pairs = []
    for wl_raw, it_raw in zip(df[wavelength_column].tolist(), df[intensity_column].tolist()):
        try:
            wl = float(EnhancedDataPreparationAgent._normalise_decimal_string(wl_raw))
            it = float(EnhancedDataPreparationAgent._normalise_decimal_string(it_raw))
        except (TypeError, ValueError):
            continue
        if wl == wl and it == it:  # filter NaN
            pairs.append((wl, it))
    return pairs


def _extract_numeric_reference(metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Collect numeric reference/target columns (e.g. brix, temperature) from
    parsed file metadata so supervised analyses can use them later."""
    references = []
    if not isinstance(metadata, dict):
        return references
    for key in ("brix", "reference_values", "reference", "y", "target"):
        value = metadata.get(key)
        if isinstance(value, (int, float)):
            references.append({"name": key, "value": value})
        elif isinstance(value, (list, tuple)) and value:
            references.append({"name": key, "count": len(value)})
    return references


def ingest_file(file_record) -> Dict[str, Any]:
    """Ingest one GenericFile into a dataset entry for the preparation report.

    Returns a dict with dataset info (wavelengths/intensities preview,
    quality metrics, metadata) or a usable=False marker with the reason.
    Never raises: unusable files are reported, not fatal, so the user can
    adapt and re-upload.
    """
    from agents.data_preparation_agent import EnhancedDataPreparationAgent

    entry: Dict[str, Any] = {
        "file_id": str(file_record.id),
        "file_name": file_record.name,
        "file_extension": file_record.file_extension,
        "file_category": file_record.file_category,
    }
    file_path = file_record.get_file_path()
    if not file_path or not Path(file_path).exists():
        entry.update({"usable": False, "reason": "File not found on server"})
        return entry

    loader = EnhancedDataPreparationAgent(
        input_directory=str(Path(file_path).parent),
        output_directory=str(Path(file_path).parent / "processed"),
    )
    spectral = loader._load_spectral_data(file_path)
    if not spectral or spectral.get("data") is None or len(spectral.get("data", [])) == 0:
        entry.update({"usable": False, "reason": "Not parseable as spectral data (S3 loader)"})
        return entry

    df = spectral.get("data")
    wavelength_column = spectral.get("wavelength_column")
    intensity_column = spectral.get("intensity_column")
    if wavelength_column not in getattr(df, "columns", []) or intensity_column not in getattr(df, "columns", []):
        entry.update({"usable": False, "reason": "Wavelength/intensity columns missing"})
        return entry

    pairs = _finite_pairs(df, wavelength_column, intensity_column)
    if not pairs:
        entry.update({"usable": False, "reason": "No finite wavelength/intensity rows"})
        return entry

    wavelengths = [p[0] for p in pairs]
    intensities = [p[1] for p in pairs]
    entry.update({
        "usable": True,
        "dataset_type": "measurement",
        "wavelength_column": str(wavelength_column),
        "intensity_column": str(intensity_column),
        "num_points": len(pairs),
        "wavelength_min": min(wavelengths),
        "wavelength_max": max(wavelengths),
        "preview": {
            "wavelengths": wavelengths[:64],
            "intensities": intensities[:64],
        },
        "metadata": spectral.get("metadata") or {},
        "numeric_references": _extract_numeric_reference(spectral.get("metadata") or {}),
    })
    return entry


def _assess_metadata(datasets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Assess metadata completeness across the usable datasets (MO 2-4)."""
    usable = [d for d in datasets if d.get("usable")]
    assessed = {"datasets_usable": len(usable), "datasets_total": len(datasets)}
    fields_found: Dict[str, int] = {}
    for dataset in usable:
        for key in dataset.get("metadata", {}):
            fields_found[key] = fields_found.get(key, 0) + 1
    assessed["metadata_fields"] = sorted(fields_found)
    recommended = RECOMMENDED_METADATA_FIELDS
    missing = [f for f in recommended if f not in fields_found]
    assessed["missing_recommended_fields"] = missing
    assessed["overall_quality_score"] = round(
        100.0 * (len(recommended) - len(missing)) / len(recommended), 1
    ) if usable else 0.0
    return assessed


def _recommendations(datasets: List[Dict[str, Any]], metadata_assessment: Dict[str, Any]) -> List[str]:
    """Concrete improvement recommendations for the user (phase 1 report)."""
    recommendations: List[str] = []
    for dataset in datasets:
        if not dataset.get("usable"):
            recommendations.append(
                f"„{dataset.get('file_name')}“ ist nicht als Spektrum auswertbar "
                f"({dataset.get('reason')}). Bitte Datei prüfen und ggf. angepasst neu hochladen."
            )
    for field in metadata_assessment.get("missing_recommended_fields", []):
        recommendations.append(
            f"Metadatenfeld „{field}“ fehlt: ergänzen, um die Metadatenbewertung zu verbessern."
        )
    if not recommendations:
        recommendations.append(
            "Alle Dateien sind als Messdaten verwertbar und die Metadaten sind vollständig - "
            "das Projekt kann zur Analyse freigegeben werden."
        )
    return recommendations


RECOMMENDED_METADATA_FIELDS = [
    "operator", "humidity", "temperature", "instrument", "acquisition_time"
]


def apply_metadata_overrides(entry: Dict[str, Any], overrides: Dict[str, Any]) -> None:
    """Merge user-entered metadata overrides (OP13) into a dataset entry.

    Empty values are ignored so a user can clear a typo by keeping other
    fields intact; the merged fields are tracked for the report UI.
    """
    if not overrides:
        return
    merged = dict(entry.get("metadata") or {})
    applied = []
    for key, value in (overrides or {}).items():
        if value in (None, ""):
            continue
        merged[key] = value
        applied.append(key)
    entry["metadata"] = merged
    entry["metadata_user_entered"] = applied


def build_preparation_report(project) -> Dict[str, Any]:
    """Build the full phase-1 preparation report for an AnalysisProject.

    The report contains: usable datasets (measurement series + metadata),
    metadata quality assessment and improvement recommendations. It is
    stored on project.preparation_report and rendered to the user.
    User-entered metadata overrides (project.metadata_overrides, OP13) are
    applied per file before the assessment.
    """
    overrides = getattr(project, "metadata_overrides", None) or {}
    datasets = []
    for f in project.files.all():
        entry = ingest_file(f)
        apply_metadata_overrides(entry, overrides.get(str(f.id), {}))
        datasets.append(entry)
    metadata_assessment = _assess_metadata(datasets)
    recommendations = _recommendations(datasets, metadata_assessment)
    usable_count = sum(1 for d in datasets if d.get("usable"))
    report = {
        "datasets": datasets,
        "metadata_quality": metadata_assessment,
        "recommendations": recommendations,
        "usable_dataset_count": usable_count,
        "total_dataset_count": len(datasets),
    }
    project.preparation_report = report
    if usable_count:
        project.save(update_fields=["preparation_report", "updated_at"])
    else:
        project.save(update_fields=["preparation_report", "updated_at"])
    logger.info(
        "Preparation report for project %s: %s/%s usable datasets",
        project.id, usable_count, len(datasets),
    )
    return report
