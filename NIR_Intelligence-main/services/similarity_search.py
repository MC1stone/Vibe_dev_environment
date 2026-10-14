"""Similarity search helper against the visible spectral database.

Shared backend for the calibration overview link, the reference database
filter (?similar_to=<id>) and the reference import confirmation. Uses the
FAISS agent (S5 engine) over records visible to the user on the same
wavelength grid - no cross-grid interpolation, by design.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def find_similar_records(user, record, top_k: int = 5,
                         exclude_ids: Optional[List] = None) -> List[Dict[str, Any]]:
    """Return the most similar visible records for one SpectrumRecord.

    Returns a list of {'record_id', 'reference_id', 'similarity', 'distance'}
    sorted by descending similarity; empty list when no records share the
    wavelength grid or the FAISS agent is unavailable. Never raises.
    """
    matches: List[Dict[str, Any]] = []
    try:
        from services.spectrum_database import visible_records
        others = visible_records(user, grid=record.wavelength_grid)
        if exclude_ids:
            others = others.exclude(id__in=exclude_ids)
        others = others.exclude(id=record.id)
        if not others.exists():
            return matches
        from agents.faiss_agent import FaissAgent
        references = [{
            'data': {'wavelength': o.wavelengths,
                     'intensity': o.intensities},
            'wavelength_column': 'wavelength',
            'intensity_column': 'intensity',
        } for o in others]
        ids = [str(o.id) for o in others]
        output = FaissAgent().execute({
            'reference_spectra': references,
            'reference_ids': ids,
            'query_spectrum': {
                'data': {'wavelength': record.wavelengths,
                         'intensity': record.intensities},
                'wavelength_column': 'wavelength',
                'intensity_column': 'intensity',
            },
            'top_k': top_k,
        })
        raw = output.data.get('matches', []) if output else []
        by_id = {str(o.id): o for o in others}
        for m in raw:
            ref_id = str(m.get('reference_id', ''))
            rec = by_id.get(ref_id)
            if rec is None:
                continue
            matches.append({
                'record_id': str(rec.id),
                'reference_id': rec.file_name or str(rec.id),
                'similarity': m.get('similarity'),
                'distance': m.get('distance'),
            })
    except Exception:
        logger.exception('Similarity search failed (non-fatal)')
    return matches
