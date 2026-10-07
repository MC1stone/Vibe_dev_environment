"""M1 verification: canonical x-axis units and conversion (spectrum_units).

Covers alias normalisation, nm/cm^-1/um conversions, comparable-axes checks
and Axis extraction from unified loader results (SPC units code, JCAMP
XUNITS header)."""

import os
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from services.spectrum_units import (
    XUNIT_CM,
    XUNIT_NM,
    XUNIT_UM,
    XUNIT_UNKNOWN,
    SpectrumAxis,
    UnitConversionError,
    axis_from_load_result,
    canonical_xunit,
    convert_values,
)


def test_alias_normalisation():
    assert canonical_xunit("Nanometers") == XUNIT_NM
    assert canonical_xunit("wavenumber (cm-1)") == XUNIT_CM
    assert canonical_xunit("µm") == XUNIT_UM
    assert canonical_xunit("1/CM") == XUNIT_CM
    assert canonical_xunit(None) == XUNIT_UNKNOWN
    assert canonical_xunit("furlongs") == XUNIT_UNKNOWN


def test_roundtrip_conversions():
    nm_vals = [1000.0, 1250.0, 2000.0, 2500.0]
    cm_vals = convert_values(nm_vals, XUNIT_NM, XUNIT_CM)
    assert abs(cm_vals[0] - 10000.0) < 1e-9
    assert abs(cm_vals[3] - 4000.0) < 1e-9
    back = convert_values(cm_vals, XUNIT_CM, XUNIT_NM)
    for a, b in zip(nm_vals, back):
        assert abs(a - b) < 1e-6
    um_vals = convert_values(nm_vals, XUNIT_NM, XUNIT_UM)
    assert abs(um_vals[0] - 1.0) < 1e-9


def test_unknown_units_rejected():
    try:
        convert_values([1.0], XUNIT_UNKNOWN, XUNIT_NM)
        raised = False
    except UnitConversionError:
        raised = True
    assert raised


def test_axis_comparability():
    a = SpectrumAxis(x_values=[1000.0, 2000.0], x_unit="nm")
    b = SpectrumAxis(x_values=[10000.0, 5000.0], x_unit="1/CM")
    c = SpectrumAxis(x_values=[1.0, 2.0], x_unit="µm")
    assert not a.is_comparable(b)
    assert a.converted(XUNIT_CM).is_comparable(b)
    assert a.is_comparable(c.converted(XUNIT_NM))


def test_axis_from_load_result_spc_code():
    loaded = {
        "data": pd.DataFrame({"wavelength": [400.0, 500.0],
                              "intensity": [0.1, 0.2]}),
        "wavelength_column": "wavelength",
        "format": ".spc",
        "source_file": "x.spc",
        "metadata": {"spc_x_units_code": 3, "x_units": "nanometers"},
    }
    axis = axis_from_load_result(loaded)
    assert axis is not None and axis.x_unit == XUNIT_NM


def test_axis_from_load_result_jcamp_header():
    loaded = {
        "data": pd.DataFrame({"wavelength": [4000.0, 5000.0],
                              "intensity": [0.5, 0.4]}),
        "wavelength_column": "wavelength",
        "format": ".jdx",
        "source_file": "x.jdx",
        "metadata": {"x_units": "1/CM"},
    }
    axis = axis_from_load_result(loaded)
    assert axis is not None and axis.x_unit == XUNIT_CM


def test_axis_unknown_unit_is_flagged_not_silent():
    loaded = {
        "data": pd.DataFrame({"wavelength": [1.0, 2.0], "intensity": [0.1, 0.2]}),
        "wavelength_column": "wavelength",
        "format": ".txt",
        "metadata": {},
    }
    axis = axis_from_load_result(loaded)
    assert axis is not None and axis.x_unit == XUNIT_UNKNOWN
    try:
        axis.converted(XUNIT_NM)
        raised = False
    except UnitConversionError:
        raised = True
    assert raised


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {t.__name__}: {e}")
    if failed:
        raise SystemExit(f"{failed} test(s) failed")
    print(f"All {len(tests)} tests passed.")


if __name__ == "__main__":
    main()
