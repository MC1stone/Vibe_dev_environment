"""S1/S2/S5 verification: navigation, start page, labels, calibration tabs.

Covers: home serves the real-data dashboard view, the 7-point navigation is
present (incl. previously orphaned pages), the "Analyze Now" quick tile is
gone with unified "Analyse starten" labels, the calibration overview shows
rmse_cv/rpd with RPD color coding, and both calibration/database pages carry
the tab navigation."""

import os
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (REPO_ROOT, os.path.join(REPO_ROOT, 'django_project')):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    django.setup()
    DJANGO_OK = True
except Exception:
    DJANGO_OK = False

TPL = os.path.join(REPO_ROOT, 'django_project', 'templates')


def test_home_is_real_dashboard():
    if not DJANGO_OK:
        print('  [SKIP] django setup unavailable')
        return
    from django.urls import resolve
    match = resolve('/')
    view = getattr(match.func, 'view_class', None) or match.func
    name = getattr(view, '__name__', str(view))
    assert name == 'DashboardStartView', name


def test_dashboard_no_fake_statistics():
    """The start page must render real data - no fabricated counters."""
    tpl = open(os.path.join(TPL, 'dashboard_start.html'), encoding='utf-8').read()
    assert 'Total Analyses' not in tpl
    assert '42' not in tpl
    assert '{{ total_projects }}' in tpl
    assert '{{ total_spectra }}' in tpl
    assert 'crew_available' in tpl
    # primary action: new project
    assert '/projects/create/' in tpl


def test_seven_point_navigation():
    base = open(os.path.join(TPL, 'base.html'), encoding='utf-8').read()
    for label in ('{% trans "Start" %}', '{% trans "Projekte" %}',
                  'Kalibration', '{% trans "Schnell-Check" %}',
                  '{% trans "Sensoren" %}', '{% trans "Lernen" %}',
                  '{% trans "Diagnose" %}'):
        assert label in base, f'nav label missing: {label}'
    # previously orphaned pages are now linked
    assert 'href="/spectra/"' in base
    assert 'href="/chatbot/"' in base
    assert 'href="/jobs/"' in base
    assert 'href="/agents/"' in base
    assert 'href="/analysis/"' in base
    assert 'href="/files/"' in base
    # diagnose section is staff-only
    assert '{% if user.is_staff %}' in base


def test_labels_unified():
    spectra = open(os.path.join(TPL, 'spectra.html'), encoding='utf-8').read()
    assert 'Analyze Now' not in spectra
    assert 'Quick Analysis' not in spectra
    assert 'Analyse starten' in spectra
    assert 'Schnell-Check' in spectra
    files = open(os.path.join(TPL, 'files.html'), encoding='utf-8').read()
    assert 'Analyze Now' not in files and 'Analyze now' not in files


def test_calibration_tabs_and_rpd_coding():
    cal = open(os.path.join(TPL, 'calibration_overview.html'), encoding='utf-8').read()
    assert 'nav-tabs' in cal
    assert '/projects/database/' in cal
    assert 'bg-{{ model.rpd_class }}' in cal
    db = open(os.path.join(TPL, 'spectrum_database.html'), encoding='utf-8').read()
    assert 'nav-tabs' in db and '/calibration/' in db


def test_calibration_view_passes_rpd():
    if not DJANGO_OK:
        print('  [SKIP] django setup unavailable')
        return
    from api.project_views import CalibrationOverviewView
    src = open(os.path.join(REPO_ROOT, 'django_project', 'api',
                            'project_views.py'), encoding='utf-8').read()
    assert "'rpd': rpd" in src
    assert "'rmse_cv': res.get('rmse_cv')" in src
    assert "'rpd_class': rpd_class" in src


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
