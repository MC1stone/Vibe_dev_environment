"""Reference-spectrum import for the NIR-IP (M3 of the interoperability
plan).

Populates the spectral database with external reference spectra (public NIR
datasets). License gate (AGENTS.md / THIRD_PARTY_LICENSES.md): every dataset
must carry source, license and version metadata BEFORE import; datasets with
unknown or non-redistributable licenses are rejected. Matching endpoints show
source and license alongside every hit so users can trace provenance.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Service.ReferenceImport")

REQUIRED_SOURCE_KEYS = ("source", "license", "version")


class LicenseViolationError(ValueError):
    pass


def validate_reference_metadata(metadata: Dict[str, Any]) -> None:
    """Raise LicenseViolationError when source/license/version are missing
    or the license is explicitly rejected."""
    missing = [k for k in REQUIRED_SOURCE_KEYS
               if not str(metadata.get(k, "") or "").strip()]
    if missing:
        raise LicenseViolationError(
            f"reference dataset rejected: missing {', '.join(missing)} "
            "(source, license and version are mandatory for reference imports)")
    license_name = str(metadata.get("license", "")).strip().lower()
    rejected = ("unknown", "unklar", "proprietary", "commercial",
                "all rights reserved", "restrictive")
    if license_name in rejected:
        raise LicenseViolationError(
            f"reference dataset rejected: non-redistributable license "
            f"{metadata.get('license')!r}")


def normalize_reference_axis(wavelengths: List[float],
                             x_unit: str) -> Dict[str, Any]:
    """Normalize a reference axis to nanometers via the M1 unit service so
    imported references are comparable with platform spectra."""
    from services.spectrum_units import (
        XUNIT_NM,
        UnitConversionError,
        convert_values,
        canonical_xunit,
    )
    unit = canonical_xunit(x_unit)
    if unit == "unknown":
        raise LicenseViolationError(
            "reference dataset rejected: x-axis unit unknown; "
            "cannot normalize to nm")
    if unit == XUNIT_NM:
        return {"wavelengths_nm": list(map(float, wavelengths)),
                "x_unit": XUNIT_NM}
    try:
        converted = convert_values(list(map(float, wavelengths)),
                                   unit, XUNIT_NM)
    except UnitConversionError as e:
        raise LicenseViolationError(f"reference dataset rejected: {e}")
    return {"wavelengths_nm": converted, "x_unit": XUNIT_NM}


def import_reference_dataset(entries: List[Dict[str, Any]],
                             user,
                             visibility: str = "lab_shared",
                             project=None) -> Dict[str, Any]:
    """Import external reference spectra as SpectrumRecords.

    Each entry: {wavelengths, intensities, x_unit, metadata, file_name}.
    metadata must include source, license, version. Rejected entries are
    counted, never abort the whole import. Returns a summary dict.
    """
    summary: Dict[str, Any] = {"imported": 0, "rejected": 0, "errors": 0,
                                "rejections": []}
    from core.models import SpectrumRecord

    for entry in entries:
        try:
            metadata = dict(entry.get("metadata") or {})
            validate_reference_metadata(metadata)
            normalized = normalize_reference_axis(
                entry.get("wavelengths") or [],
                entry.get("x_unit") or metadata.get("x_units") or "")
            wavelengths = normalized["wavelengths_nm"]
            intensities = [float(v) for v in (entry.get("intensities") or [])]
            if not wavelengths or len(wavelengths) != len(intensities):
                summary["rejected"] += 1
                summary["rejections"].append(
                    f"{entry.get('file_name', '?')}: empty or mismatched "
                    "wavelength/intensity axis")
                continue
            metadata["x_unit"] = normalized["x_unit"]
            metadata["reference_import"] = True
            SpectrumRecord.objects.create(
                user=user,
                project=project,
                file_name=entry.get("file_name", "reference"),
                visibility=visibility,
                wavelengths=wavelengths,
                intensities=intensities,
                metadata=metadata,
                wavelength_grid=SpectrumRecord.grid_key(wavelengths),
                instrument_type=metadata.get("instrument", ""),
                sample_type=metadata.get("sample_type", ""),
            )
            summary["imported"] += 1
        except LicenseViolationError as e:
            summary["rejected"] += 1
            summary["rejections"].append(str(e))
        except Exception:
            summary["errors"] += 1
            logger.exception("reference import failed for %s",
                             entry.get("file_name", "?"))
    logger.info("Reference import: %s", summary)
    return summary


def reference_hit_display(record) -> Dict[str, Any]:
    """Display form of a matched reference record with provenance (source,
    license, version) so similarity results always show their origin."""
    metadata = record.metadata or {}
    return {
        "id": str(record.id),
        "file_name": record.file_name,
        "sample_type": record.sample_type,
        "source": metadata.get("source", ""),
        "license": metadata.get("license", ""),
        "version": metadata.get("version", ""),
        "is_reference_import": bool(metadata.get("reference_import")),
    }
