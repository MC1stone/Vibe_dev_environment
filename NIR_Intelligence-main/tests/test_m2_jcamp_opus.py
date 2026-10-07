"""M2 verification: JCAMP-DX parser and OPUS loader wiring.

Covers AFFN/PAC, SQZ/DUP compressed XYDATA, XYPOINTS blocks, XFACTOR/YFACTOR
application, non-JCAMP rejection, and the OPUS loader's graceful degradation
when opusfc is not installed."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from services.jcamp_parser import JCAMPError, parse_jcamp_dx, load_jcamp_file
from services.opus_reader import opusfc_available, load_opus_spectrum

AFFN_JDX = """##TITLE=Test AFFN spectrum
##DATATYPE=Infrared Spectrum
##XUNITS=1/CM
##YUNITS=TRANSMITTANCE
##XFACTOR=1.0
##YFACTOR=1.0
##FIRSTX=4000.0
##LASTX=400.0
##DELTAX=-100.0
##NPOINTS=37
##XYDATA= (X++(Y..Y))
4000.0 0.95 0.90 0.85
3600.0 0.80 0.75 0.70
##END=
"""

SQZ_JDX = """##TITLE=Test SQZ spectrum
##XUNITS=NANOMETERS
##YUNITS=ARBITRARY UNITS
##XFACTOR=1.0
##YFACTOR=0.01
##FIRSTX=1000.0
##DELTAX=10.0
##XYDATA= (X++(Y..Y))
1000.0 A5 B6 C7 A5
1040.0 J1 K2 A9
##END=
"""

XYPOINTS_JDX = """##TITLE=Test XYPOINTS
##XUNITS=1/CM
##YUNITS=ABSORBANCE
##XYPOINTS= (XY..XY)
4000.0, 0.10
3500.0, 0.20
3000.0, 0.15
##END=
"""

NOT_JCAMP = "wavelength,intensity\n1000,0.5\n1100,0.6\n"


def test_affn_xydata():
    r = parse_jcamp_dx(AFFN_JDX)
    df = r["data"]
    assert len(df) == 6
    assert abs(df["wavelength"].iloc[0] - 4000.0) < 1e-9
    assert abs(df["wavelength"].iloc[1] - 3900.0) < 1e-9
    assert abs(df["intensity"].iloc[0] - 0.95) < 1e-9
    assert abs(df["intensity"].iloc[5] - 0.70) < 1e-9
    assert r["metadata"]["x_units"] == "1/CM"


def test_sqz_xydata_with_factors():
    r = parse_jcamp_dx(SQZ_JDX)
    df = r["data"]
    assert len(df) == 7
    assert abs(df["intensity"].iloc[0] - 0.15) < 1e-9
    assert abs(df["intensity"].iloc[1] - 0.26) < 1e-9
    assert abs(df["intensity"].iloc[2] - 0.37) < 1e-9
    assert abs(df["intensity"].iloc[3] - 0.15) < 1e-9
    assert abs(df["intensity"].iloc[4] - (-0.11)) < 1e-9
    assert abs(df["intensity"].iloc[5] - (-0.22)) < 1e-9
    assert abs(df["intensity"].iloc[6] - 0.19) < 1e-9
    assert abs(df["wavelength"].iloc[1] - 1010.0) < 1e-9


def test_xypoints_block():
    r = parse_jcamp_dx(XYPOINTS_JDX)
    df = r["data"]
    assert len(df) == 3
    assert abs(df["wavelength"].iloc[0] - 4000.0) < 1e-9
    assert abs(df["intensity"].iloc[2] - 0.15) < 1e-9


def test_non_jcamp_rejected():
    assert load_jcamp_file is not None
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".jdx", delete=False) as f:
        f.write(NOT_JCAMP)
        path = f.name
    try:
        r = load_jcamp_file(path)
        assert r is None
    finally:
        os.unlink(path)


def test_missing_data_raises():
    try:
        parse_jcamp_dx("##TITLE=empty\n##END=\n")
        raised = False
    except JCAMPError:
        raised = True
    assert raised


def test_opus_graceful_without_opusfc():
    if opusfc_available():
        assert load_opus_spectrum("nonexistent.d") is None
    else:
        assert load_opus_spectrum("nonexistent.d") is None


def test_agent_routing_jdx_and_d():
    import logging
    logging.disable(logging.WARNING)
    from agents.data_preparation_agent import EnhancedDataPreparationAgent
    import tempfile
    agent = EnhancedDataPreparationAgent(
        input_directory=tempfile.gettempdir(),
        output_directory=tempfile.gettempdir(),
        temp_directory=tempfile.gettempdir(),
    )
    with tempfile.NamedTemporaryFile("w", suffix=".jdx", delete=False) as f:
        f.write(AFFN_JDX)
        jdx_path = f.name
    try:
        r = agent._load_spectral_data(jdx_path)
        assert r is not None and len(r["data"]) == 6
        assert r["format"] == ".jdx"
    finally:
        os.unlink(jdx_path)
    r = agent._load_spectral_data("does-not-exist.d")
    assert r is None


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
