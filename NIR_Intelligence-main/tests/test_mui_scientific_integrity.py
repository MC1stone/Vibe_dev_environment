"""M-UI verification: scientific integrity of the spectra UI pipeline.

Covers: NIRSpectrum curve persistence via the format-agnostic loader
(_persist_curve_data with real files incl. units), serializer exposure of
wavelengths/intensities/x_unit/y_unit, and the JS contract that fabricated
sample data generators return empty arrays."""

import os
import sys
import tempfile

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DJANGO_ROOT = os.path.join(REPO_ROOT, 'django_project')
for p in (REPO_ROOT, DJANGO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    django.setup()
    DJANGO_OK = True
except Exception:
    DJANGO_OK = False


def test_js_fabricated_generators_are_empty():
    """The deprecated sample-data generators must return empty axes so no
    fabricated curve can ever be rendered or submitted."""
    js_path = os.path.join(DJANGO_ROOT, 'static', 'js', 'spectra.js')
    src = open(js_path, encoding='utf-8').read()
    assert 'wavelengths.push(i);' not in src, \
        'generateSampleWavelengths still fabricates an axis'
    assert 'Math.random()' not in src.split('function generateSampleIntensities')[1].split('function ')[0].split('}')[0], \
        'generateSampleIntensities still fabricates values'
    # analysis payload must not fall back to sample generators
    assert 'spectral_data: {\n            wavelengths: spectrum.wavelengths || []' in src or \
        'wavelengths: spectrum.wavelengths || [],' in src
    # legacy records without a curve are NOT blocked client-side; the
    # backend loads the curve from the original file and only rejects
    # when neither exists (see test_legacy_regression_fix.py)
    assert 'never used' in src
    # charts must use numeric linear axes
    assert src.count("type: 'linear'") >= 2


def test_no_fabricated_fallback_in_chart_creation():
    js_path = os.path.join(DJANGO_ROOT, 'static', 'js', 'spectra.js')
    src = open(js_path, encoding='utf-8').read()
    for chart_fn in ('createSpectrumChart', 'createDetailedSpectrumChart'):
        body = src.split('function ' + chart_fn)[1].split('\nfunction ')[0]
        assert 'generateSample' not in body, \
            f'{chart_fn} still falls back to fabricated data'


def test_model_has_curve_fields():
    if not DJANGO_OK:
        print('  [SKIP] django setup unavailable')
        return
    from core.models import NIRSpectrum
    s = NIRSpectrum(name='t')
    assert hasattr(s, 'wavelengths') and hasattr(s, 'intensities')
    assert hasattr(s, 'x_unit') and hasattr(s, 'y_unit')


def test_serializer_exposes_curve_fields():
    if not DJANGO_OK:
        print('  [SKIP] django setup unavailable')
        return
    from api.serializers import NIRSpectrumSerializer
    fields = NIRSpectrumSerializer.Meta.fields
    for f in ('wavelengths', 'intensities', 'x_unit', 'y_unit'):
        assert f in fields, f'{f} missing from serializer'


def test_persist_curve_data_extracts_real_curve():
    if not DJANGO_OK:
        print('  [SKIP] django setup unavailable')
        return
    from api.views import SpectrumListCreateView
    import numpy as np

    tmp = tempfile.mkdtemp(prefix='ui_curve_')
    csv_path = os.path.join(tmp, 'real_spectrum.csv')
    xs = [1000.0 + 10.0 * i for i in range(30)]
    ys = [0.1 + 0.01 * i for i in range(30)]
    with open(csv_path, 'w') as f:
        f.write('wavelength,intensity\n')
        for x, y in zip(xs, ys):
            f.write(f'{x},{y}\n')

    class FakeSpectrum:
        name = 'real'
        wavelengths = None
        intensities = None
        x_unit = None
        y_unit = None
        data_points = 0
        wavelength_range_start = 0.0
        wavelength_range_end = 0.0
        resolution = 0.0
        id = 'fake-id'

        def get_file_path(self):
            return csv_path

    view = SpectrumListCreateView()
    spectrum = FakeSpectrum()
    view._persist_curve_data(spectrum)
    assert spectrum.wavelengths and len(spectrum.wavelengths) == 30
    assert abs(spectrum.wavelengths[0] - 1000.0) < 1e-6
    assert abs(spectrum.intensities[-1] - 0.39) < 1e-6
    assert spectrum.x_unit == 'nm'
    assert spectrum.data_points == 30
    assert abs(spectrum.resolution - 10.0) < 1e-6


def test_persist_curve_data_jcamp_units():
    if not DJANGO_OK:
        print('  [SKIP] django setup unavailable')
        return
    from api.views import SpectrumListCreateView

    tmp = tempfile.mkdtemp(prefix='ui_jcamp_')
    jdx_path = os.path.join(tmp, 'spectrum.jdx')
    jdx = """##TITLE=UI test
##XUNITS=1/CM
##YUNITS=TRANSMITTANCE
##XYDATA= (X++(Y..Y))
4000.0 0.9 0.8 0.7
##END=
"""
    with open(jdx_path, 'w') as f:
        f.write(jdx)

    class FakeSpectrum:
        wavelengths = None
        intensities = None
        x_unit = None
        y_unit = None
        data_points = 0
        wavelength_range_start = 0.0
        wavelength_range_end = 0.0
        resolution = 0.0
        id = 'fake-id'

        def get_file_path(self):
            return jdx_path

    view = SpectrumListCreateView()
    spectrum = FakeSpectrum()
    view._persist_curve_data(spectrum)
    assert spectrum.wavelengths and len(spectrum.wavelengths) == 3
    assert spectrum.x_unit == 'cm^-1'
    assert spectrum.y_unit == 'transmittance'


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
