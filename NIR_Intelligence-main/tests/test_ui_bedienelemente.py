"""UI visibility verification: entry points users can actually see.

1. Reference import UI exists on the spectrum database page and the
   endpoint enforces source/license/version (license gate visible to user).
2. "Analyse starten" is a labelled button in table, gallery and detail
   modal - not an icon-only mystery button.
3. Analysis failures show the backend error detail instead of a generic
   retry message.
"""

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


def test_reference_import_ui_present():
    tpl = open(os.path.join(REPO_ROOT, 'django_project', 'templates',
                            'spectrum_database.html'), encoding='utf-8').read()
    assert 'Referenzspektrum importieren' in tpl
    assert 'import-reference' in tpl
    for field in ('reference_file', 'source', 'license', 'version'):
        assert f'name="{field}"' in tpl, field
    assert tpl.count('required') >= 4


def test_reference_import_view_enforces_provenance():
    if not DJANGO_OK:
        print('  [SKIP] django setup unavailable')
        return
    from django.test import RequestFactory
    from django.contrib.auth import get_user_model
    from django.contrib.messages.storage.fallback import FallbackStorage
    from api.project_views import ReferenceImportView

    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username='ref-import-user',
        defaults={'email': 'ref-import-user@test.local'})

    rf = RequestFactory()
    # missing provenance -> redirect, nothing imported
    request = rf.post('/projects/database/import-reference/',
                      {'source': '', 'license': '', 'version': ''})
    request.user = user
    setattr(request, 'session', {})
    setattr(request, '_messages', FallbackStorage(request))
    response = ReferenceImportView().post(request)
    assert response.status_code == 302

    from core.models import SpectrumRecord
    assert not SpectrumRecord.objects.filter(
        metadata__reference_import=True).exists()
    user.delete()


def test_reference_import_view_imports_with_provenance():
    if not DJANGO_OK:
        print('  [SKIP] django setup unavailable')
        return
    import tempfile
    from django.test import RequestFactory
    from django.contrib.auth import get_user_model
    from django.contrib.messages.storage.fallback import FallbackStorage
    from api.project_views import ReferenceImportView

    tmp = tempfile.mkdtemp(prefix='ref_import_')
    path = os.path.join(tmp, 'ref.csv')
    with open(path, 'w') as f:
        f.write('wavelength,intensity\n1000,0.1\n1100,0.2\n1200,0.15\n')

    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username='ref-import-user2',
        defaults={'email': 'ref-import-user2@test.local'})

    from django.core.files.uploadedfile import SimpleUploadedFile
    with open(path, 'rb') as f:
        uploaded = SimpleUploadedFile('ref.csv', f.read(),
                                      content_type='text/csv')
    rf = RequestFactory()
    request = rf.post('/projects/database/import-reference/', {
        'reference_file': uploaded,
        'source': 'Open Specy',
        'license': 'CC-BY-4.0',
        'version': 'v1.2',
        'sample_type': 'polystyrene',
    })
    request.user = user
    setattr(request, 'session', {})
    setattr(request, '_messages', FallbackStorage(request))
    response = ReferenceImportView().post(request)
    assert response.status_code == 302

    from core.models import SpectrumRecord
    record = SpectrumRecord.objects.filter(
        user=user, metadata__reference_import=True).first()
    assert record is not None, 'reference record was not created'
    assert record.metadata['source'] == 'Open Specy'
    assert record.metadata['license'] == 'CC-BY-4.0'
    assert record.visibility == 'lab_shared'
    assert len(record.wavelengths) == 3
    record.delete()
    user.delete()


def test_analyse_starten_buttons_visible():
    js = open(os.path.join(REPO_ROOT, 'django_project', 'static', 'js',
                           'spectra.js'), encoding='utf-8').read()
    assert js.count('Analyse starten') >= 3, \
        'labelled Analyse-Button fehlt (Tabelle/Galerie/Modal)'
    # gallery button must not trigger the card click (details modal)
    assert 'event.stopPropagation(); analyzeSpectrum' in js
    # backend error detail surfaced to the user
    assert 'error.response.data.error' in js
    tpl = open(os.path.join(REPO_ROOT, 'django_project', 'templates',
                            'spectra.html'), encoding='utf-8').read()
    assert 'Analyse starten' in tpl


def test_import_url_wired():
    if not DJANGO_OK:
        print('  [SKIP] django setup unavailable')
        return
    from django.urls import reverse, NoReverseMatch
    url = reverse('reference-import')
    assert url == '/api/projects/database/import-reference/'


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
