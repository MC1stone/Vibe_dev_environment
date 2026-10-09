"""Workflow integration of the ingest result (WORKFLOW_DESIGN.md steps 3 and 4).

After the phase-1 preparation report is built, this service translates the
agent findings into the workflow model:
- Station 3 (sensor assignment): if the sensor database offers suggested
  standard values for the sensor used, the user gets a decision with the
  options accept / modify / decline (no dead ends).
- Station 4 (spectrum comparison): if a spectrum can be constructed from the
  datasets, the spectral database is searched for comparable spectra; matches
  are offered with a shortcut decision (evaluate with the existing model,
  e.g. BRIX) versus the full analysis cycle.
"""
import logging

logger = logging.getLogger(__name__)

STATION_SENSOR = 3
STATION_COMPARISON = 4


def _create_decision(project, station, question, options, ki_basis):
    from api.workflow_context import create_decision
    return create_decision(project, station, question, options, ki_basis=ki_basis)


def _has_open_decision(project, station):
    from core.models import WorkflowDecision
    return WorkflowDecision.objects.filter(
        project=project, station__station=station,
        resolved_at__isnull=True).exists()


def offer_sensor_defaults(project, sensor_entry):
    """Station 3: propose the sensor database's standard values as a decision.

    The proposed values are attached to the options so the user can accept them
    unchanged or open them for modification - never a silent auto-assignment.
    """
    sensor = (sensor_entry or {}).get('sensor') or ''
    suggested = (sensor_entry or {}).get('suggested_settings') or {}
    if not sensor or not suggested or _has_open_decision(project, STATION_SENSOR):
        return None

    question = (
        f"Für den Sensor '{sensor}' wurden Standardwerte in der "
        f"Sensordatenbank gefunden. Übernehmen?")
    options = [
        {'id': 'accept', 'label': 'Standardwerte übernehmen',
         'effect': 'sensor_defaults_applied', 'values': suggested},
        {'id': 'modify', 'label': 'Werte abändern',
         'effect': 'opens_inline_editor', 'values': suggested},
        {'id': 'decline', 'label': 'Nicht übernehmen',
         'effect': 'manual_entry_required'},
    ]
    decision = _create_decision(
        project, STATION_SENSOR, question, options,
        ki_basis=f"Sensordatenbank-Eintrag '{sensor}'")
    logger.info('Sensor defaults decision %s for project %s (sensor %s)',
                decision.id, project.id, sensor)
    return decision


def _query_spectrum_from_datasets(datasets):
    """The first usable dataset that can construct a spectrum (or None)."""
    for dataset in datasets or []:
        if not dataset.get('usable'):
            continue
        data = dataset.get('data') or {}
        wavelength = data.get('wavelength') or data.get('x')
        intensity = data.get('intensity') or data.get('y')
        if wavelength and intensity and len(wavelength) == len(intensity):
            return dataset, wavelength, intensity
    return None


def offer_spectrum_comparison(project, datasets, user=None):
    """Station 4: compare the first constructable spectrum against the
    spectral database (FAISS) and offer matches with a shortcut decision.

    Returns the created decision or None (no spectrum, no matches or an
    already open comparison decision - all honest no-ops, no dead ends).
    """
    if _has_open_decision(project, STATION_COMPARISON):
        return None
    found = _query_spectrum_from_datasets(datasets)
    if not found:
        return None
    dataset, wavelength, intensity = found

    matches = _faiss_matches(wavelength, intensity, user)
    if not matches:
        return None

    best = matches[0]
    best_label = best.get('id') or best.get('reference_id') or 'unbekannt'
    sample_name = dataset.get('name') or dataset.get('file_name') or 'Datensatz'
    question = (
        f"Spektrenabgleich: vergleichbare Spektren gefunden "
        f"(beste Übereinstimmung: {best_label}). "
        f"Wie soll '{sample_name}' bewertet werden?")
    options = [
        {'id': 'use_existing_model',
         'label': 'Shortcut: mit vorhandenem Modell bewerten',
         'effect': 'evaluate_with_existing_model', 'match': best},
        {'id': 'full_cycle', 'label': 'Vollen Analyse-Zyklus starten',
         'effect': 'start_analysis_cycle'},
        {'id': 'dismiss', 'label': 'Keine der Optionen - Daten zuerst anpassen',
         'effect': 'back_to_data_preparation'},
    ]
    decision = _create_decision(
        project, STATION_COMPARISON, question, options,
        ki_basis=f"FAISS-Spektrenabgleich, top {len(matches)} Treffer")
    logger.info('Spectrum comparison decision %s for project %s',
                decision.id, project.id)
    return decision


def _faiss_matches(wavelength, intensity, user=None):
    """Comparable spectra from the local spectral database (FAISS, top-3)."""
    try:
        from core.models import SpectrumRecord
        from agents.faiss_agent import FaissAgent
        records = SpectrumRecord.objects.filter(user=user)
        if user is None:
            records = SpectrumRecord.objects.none()
        references = [{
            'data': {'wavelength': r.wavelengths, 'intensity': r.intensities},
            'wavelength_column': 'wavelength',
            'intensity_column': 'intensity',
        } for r in records]
        if not references:
            return []
        ids = [r.file_name or str(r.id) for r in records]
        output = FaissAgent().execute({
            'reference_spectra': references,
            'reference_ids': ids,
            'query_spectrum': {
                'data': {'wavelength': list(wavelength),
                         'intensity': list(intensity)},
                'wavelength_column': 'wavelength',
                'intensity_column': 'intensity',
            },
            'top_k': 3,
        })
        return output.data.get('matches', []) if output else []
    except Exception as exc:
        logger.warning('FAISS comparison failed (degraded, non-fatal): %s', exc)
        return []


def integrate_preparation_report(project, report):
    """Entry point after build_preparation_report: translate agent findings
    into workflow decisions (stations 3 and 4). Never raises."""
    try:
        for entry in (report.get('sensor_reference') or {}).get('checked', []):
            offer_sensor_defaults(project, entry)
        offer_spectrum_comparison(
            project, report.get('datasets') or [],
            user=getattr(project, 'user', None))
    except Exception as exc:
        logger.warning('Workflow integration failed (non-fatal): %s', exc)
