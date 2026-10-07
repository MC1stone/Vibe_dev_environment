"""Canonical spectral axis units for the NIR-IP (M1 of the
interoperability implementation plan).

Loads any spectral dataset's x-axis onto a canonical unit so similarity
search, reference-database matching and wavelength comparisons never mix
nanometers with wavenumbers.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

XUNIT_NM = "nm"
XUNIT_CM = "cm^-1"
XUNIT_UM = "um"
XUNIT_UNKNOWN = "unknown"

_CANONICAL_UNITS = (XUNIT_NM, XUNIT_CM, XUNIT_UM, XUNIT_UNKNOWN)

_ALIASES = {
    "nm": XUNIT_NM, "nanometer": XUNIT_NM, "nanometers": XUNIT_NM,
    "nanometre": XUNIT_NM, "nanometres": XUNIT_NM,
    "cm^-1": XUNIT_CM, "cm-1": XUNIT_CM, "1/cm": XUNIT_CM, "cm⁻¹": XUNIT_CM,
    "wavenumber (cm-1)": XUNIT_CM, "wavenumber": XUNIT_CM, "kayser": XUNIT_CM,
    "um": XUNIT_UM, "µm": XUNIT_UM, "micrometer": XUNIT_UM,
    "micrometers": XUNIT_UM, "micron": XUNIT_UM, "microns": XUNIT_UM,
}

_SPC_XUNIT_MAP = {
    1: XUNIT_CM,
    2: XUNIT_UM,
    3: XUNIT_NM,
}


class UnitConversionError(ValueError):
    pass


def canonical_xunit(raw: Any) -> str:
    if raw is None:
        return XUNIT_UNKNOWN
    key = str(raw).strip().lower()
    if key in _CANONICAL_UNITS:
        return key
    return _ALIASES.get(key, XUNIT_UNKNOWN)


def convert_values(values: List[float], from_unit: str, to_unit: str) -> List[float]:
    src = canonical_xunit(from_unit)
    dst = canonical_xunit(to_unit)
    if src == XUNIT_UNKNOWN or dst == XUNIT_UNKNOWN:
        raise UnitConversionError(
            f"cannot convert x-axis units: {src!r} -> {dst!r}")
    if src == dst:
        return list(values)
    if src == XUNIT_NM and dst == XUNIT_CM:
        return [1e7 / v if v else v for v in values]
    if src == XUNIT_CM and dst == XUNIT_NM:
        return [1e7 / v if v else v for v in values]
    if src == XUNIT_NM and dst == XUNIT_UM:
        return [v / 1000.0 for v in values]
    if src == XUNIT_UM and dst == XUNIT_NM:
        return [v * 1000.0 for v in values]
    if src == XUNIT_CM and dst == XUNIT_UM:
        return [1e4 / v if v else v for v in values]
    if src == XUNIT_UM and dst == XUNIT_CM:
        return [1e4 / v if v else v for v in values]
    raise UnitConversionError(f"unsupported conversion {src} -> {dst}")


@dataclass
class AxisSpec:
    unit: str
    label: str


@dataclass
class SpectrumAxis:
    x_values: List[float]
    x_unit: str
    y_unit: str = "unknown"
    provenance: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.x_unit = canonical_xunit(self.x_unit)
        self.y_unit = str(self.y_unit or "unknown").strip().lower() or "unknown"

    @property
    def x_label(self) -> str:
        return f"x ({self.x_unit})"

    def converted(self, to_unit: str) -> "SpectrumAxis":
        return SpectrumAxis(
            x_values=convert_values(self.x_values, self.x_unit, to_unit),
            x_unit=canonical_xunit(to_unit),
            y_unit=self.y_unit,
            provenance=dict(self.provenance, converted_from=self.x_unit),
        )

    def is_comparable(self, other: "SpectrumAxis") -> bool:
        return (
            self.x_unit != XUNIT_UNKNOWN
            and other.x_unit != XUNIT_UNKNOWN
            and self.x_unit == other.x_unit
        )


def axis_from_load_result(loaded: Optional[Dict[str, Any]]) -> Optional[SpectrumAxis]:
    if not loaded or not isinstance(loaded.get("data"), object):
        return None
    df = loaded.get("data")
    if df is None or not hasattr(df, "iloc"):
        return None
    x_col = loaded.get("wavelength_column")
    if x_col is None or x_col not in df.columns or len(df) == 0:
        return None
    metadata = loaded.get("metadata") or {}
    raw_unit = (
        metadata.get("x_unit")
        or metadata.get("x_units")
        or XUNIT_UNKNOWN
    )
    spc_code = metadata.get("spc_x_units_code")
    if canonical_xunit(raw_unit) == XUNIT_UNKNOWN and spc_code in _SPC_XUNIT_MAP:
        raw_unit = _SPC_XUNIT_MAP[spc_code]
    return SpectrumAxis(
        x_values=[float(v) for v in df[x_col].tolist()],
        x_unit=raw_unit,
        y_unit=metadata.get("y_unit") or metadata.get("y_units") or "unknown",
        provenance={"source_file": loaded.get("source_file"),
                    "format": loaded.get("format")},
    )
