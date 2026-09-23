# NIR Intelligence Platform - Spectral database service (OP15)
# Phase 2 companion of the project workflow: when a project is released,
# its usable datasets are persisted as SpectrumRecords so later projects can
# compare against them (MO 10/11). Visibility defaults to the owner (FL ground
# rule: raw spectra stay local); lab sharing is an explicit opt-in via the
# project settings. Provenance fields double as non-IID sharding dimensions
# for federated learning (S9 grouping by spectrometer/sample type).
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Service.SpectrumDatabase")


def _dataset_grid(dataset: Dict[str, Any]) -> Optional[str]:
    """Canonical wavelength-grid key of a preparation-report dataset, or
    None when the dataset has no usable wavelength axis."""
    wavelengths = dataset.get('preview', {}).get('wavelengths') or []
    if not wavelengths:
        return None
    try:
        from core.models import SpectrumRecord
        return SpectrumRecord.grid_key(wavelengths)
    except Exception:
        return None


def persist_project_spectra(project, visibility: str = 'private') -> Dict[str, Any]:
    """Persist the usable datasets of a released project as SpectrumRecords.

    Idempotent: datasets already persisted from this project (same file id)
    are updated, not duplicated, so a re-release does not grow the database.
    Never raises - a persistence failure must not abort the crew analysis.
    Returns a summary dict for logging and tests.
    """
    from core.models import SpectrumRecord

    summary: Dict[str, Any] = {'created': 0, 'updated': 0, 'skipped': 0}
    preparation = project.preparation_report or {}
    datasets = [d for d in preparation.get('datasets', []) if d.get('usable')]
    for dataset in datasets:
        wavelengths = dataset.get('preview', {}).get('wavelengths') or []
        intensities = dataset.get('preview', {}).get('intensities') or []
        if not wavelengths or not intensities:
            summary['skipped'] += 1
            continue
        grid = _dataset_grid(dataset)
        if grid is None:
            summary['skipped'] += 1
            continue
        metadata = dict(dataset.get('metadata') or {})
        instrument = (metadata.get('instrument_type')
                      or metadata.get('instrument') or '')
        sample_type = metadata.get('sample_type') or metadata.get('sample') or ''
        try:
            record = SpectrumRecord.objects.filter(
                project=project, file_name=dataset.get('file_name', '')
            ).first()
            if record is None:
                SpectrumRecord.objects.create(
                    user_id=project.user_id,
                    project=project,
                    file_name=dataset.get('file_name', ''),
                    visibility=visibility,
                    wavelengths=wavelengths,
                    intensities=intensities,
                    metadata=metadata,
                    wavelength_grid=grid,
                    instrument_type=instrument,
                    sample_type=sample_type,
                )
                summary['created'] += 1
            else:
                record.wavelengths = wavelengths
                record.intensities = intensities
                record.metadata = metadata
                record.wavelength_grid = grid
                record.instrument_type = instrument
                record.sample_type = sample_type
                record.visibility = visibility
                record.save()
                summary['updated'] += 1
        except Exception:
            summary['skipped'] += 1
            logger.exception('Failed to persist spectrum for %s',
                             dataset.get('file_name'))
    logger.info('Spectral database persist for project %s: %s',
                project.id, summary)
    return summary


def visible_records(user, grid: Optional[str] = None):
    """SpectrumRecords visible to one user: own records plus lab-shared ones.
    Optionally filtered to one wavelength grid so only equally-dimensioned
    spectra are compared (no cross-grid interpolation, by design)."""
    from core.models import SpectrumRecord
    from django.db.models import Q

    query = SpectrumRecord.objects.filter(
        Q(user=user) | Q(visibility='lab_shared')
    )
    if grid is not None:
        query = query.filter(wavelength_grid=grid)
    return query.order_by('-created_at')


def references_for_dataset(user, dataset: Dict[str, Any],
                           exclude_project_id=None) -> Dict[str, List]:
    """FAISS reference set for one dataset: all visible database records on
    the same wavelength grid, excluding spectra from the given project
    (they are already compared as sibling datasets by the crew runner).
    Returns {'references': [...], 'ids': [...]} in unified schema form."""
    grid = _dataset_grid(dataset)
    if grid is None:
        return {'references': [], 'ids': []}
    records = visible_records(user, grid=grid)
    if exclude_project_id is not None:
        records = records.exclude(project_id=exclude_project_id)
    references = []
    ids = []
    for record in records:
        references.append({
            'data': {'wavelength': record.wavelengths,
                     'intensity': record.intensities},
            'wavelength_column': 'wavelength',
            'intensity_column': 'intensity',
        })
        ids.append(record.file_name or str(record.id))
    return {'references': references, 'ids': ids}
