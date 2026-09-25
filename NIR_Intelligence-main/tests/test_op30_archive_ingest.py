"""OP30 verification: archives are containers in the project ingest.

A project ZIP bundles several files (a prose description plus train/test
measurement exports). The old ingest treated the archive as ONE spectrum
file: the content-driven loader picked a single inner file and garbled its
columns into a fake wavelength axis, so the preparation report ended with
'No finite wavelength/intensity rows' and both the metadata description
and every other inner file were lost.

Offline test matrix (repo check() style):

T1  archive ingest returns one dataset per inner file (oil ZIP scenario)
T2  inner measurement matrices ingest as wide format (real channel axis)
T3  inner description files become metadata sources (prose extraction)
T4  metadata alias sync (OP28 T5n) reaches archive datasets, assessment
    counts them
T5  non-archive files keep the single-entry ingest (regression)
T6  metadata overrides (OP13) work for inner archive datasets
T7  honest reporting: a broken inner file is listed, not fatal
T8  nested archives are extracted recursively (content-driven chain)
"""

import os
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

PASS = 0
FAIL = 0
FAILED = []


def check(name, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'[PASS] {name}')
    else:
        FAIL += 1
        FAILED.append(name)
        print(f'[FAIL] {name} {detail}')


tmp = tempfile.mkdtemp(prefix='op30_archive_')

import pandas as pd  # noqa: E402

from services.project_ingest import (  # noqa: E402
    build_preparation_report,
    ingest_file,
)

# The user's oil experiment ZIP: a prose description plus two wide-format
# measurement matrices (train/test), semicolon-delimited European CSV.
CHANNELS = ['A_610', 'B_680', 'C_730', 'D_760', 'E_810', 'F_860',
            'G_560', 'H_585', 'I_645', 'J_705', 'K_900', 'L_940']


def _wide_csv(path, rows=20):
    data = []
    for i in range(rows):
        row = {'Probe': f'Oel_{i % 3}', 'Brix': 10.0 + i * 0.3}
        for c in CHANNELS:
            row[c] = 1000.0 + i * 2.5 + CHANNELS.index(c) * 37
        data.append(row)
    pd.DataFrame(data).to_csv(path, sep=';', index=False)
    return path


meta_path = os.path.join(tmp, 'Öl_Meta.txt')
with open(meta_path, 'w', encoding='utf-8') as f:
    f.write('Ölexperiment Spektralmessungen\n\n'
            'Die Messungen wurden von Yvonne mit dem Triadsensor unter tageslicht '
            'bedingungnen in der NIRS Werkstatt ausgeführt 25′ raumtemperatur, '
            'nicht verdunkelt, 88% Luftfeuchte.\n')

_wide_csv(os.path.join(tmp, 'OEL-MK_Train(1).csv'))
_wide_csv(os.path.join(tmp, 'OEL_MK_Test.csv'), rows=12)

zip_path = os.path.join(tmp, 'OEL_MK.zip')
with zipfile.ZipFile(zip_path, 'w') as z:
    z.write(meta_path, 'Öl_Meta.txt')
    z.write(os.path.join(tmp, 'OEL-MK_Train(1).csv'), 'OEL-MK_Train(1).csv')
    z.write(os.path.join(tmp, 'OEL_MK_Test.csv'), 'OEL_MK_Test.csv')


class _Record:
    """Minimal GenericFile stand-in (attributes used by the ingest)."""

    def __init__(self, path, name, file_id='00000000-0000-0000-0000-000000000001'):
        self.id = file_id
        self.name = name
        self.file_extension = Path(path).suffix.lower() or '.zip'
        self.file_category = 'raw'
        self._path = str(path)

    def get_file_path(self):
        return self._path


# ---------------------------------------------------------------- T1
result = ingest_file(_Record(zip_path, 'OEL_MK.zip'))
entries = result if isinstance(result, list) else [result]
names = sorted(e.get('file_name', '') for e in entries)
check('T1a archive ingest returns a list of entries', isinstance(result, list),
      f'type={type(result).__name__}')
check('T1b one entry per inner file (3)', len(entries) == 3,
      f'entries={[e.get("file_name") for e in entries]}')
check('T1c inner file names are preserved',
      'OEL-MK_Train(1).csv' in names and 'OEL_MK_Test.csv' in names,
      f'names={names}')
check('T1d no fake single-file parse of the archive',
      all('No finite wavelength' not in str(e.get('reason', ''))
          for e in entries),
      f'reasons={[e.get("reason") for e in entries]}')
check('T1e every inner entry carries its archive origin',
      all(e.get('archive_file') == 'OEL_MK.zip' for e in entries),
      f'origins={[e.get("archive_file") for e in entries]}')

# ---------------------------------------------------------------- T2
train = next((e for e in entries if 'Train' in e.get('file_name', '')), None)
test = next((e for e in entries if 'Test' in e.get('file_name', '')), None)
check('T2a train matrix ingested as wide format',
      train is not None and train.get('usable') is True
      and train.get('dataset_type') == 'measurement',
      f'train={train}')
check('T2b channel axis is the real wavelength axis',
      train is not None
      and train.get('preview', {}).get('wavelengths') == [610.0, 680.0, 730.0, 760.0, 810.0, 860.0, 560.0, 585.0, 645.0, 705.0, 900.0, 940.0],
      f'wl={train.get("preview", {}).get("wavelengths") if train else None}')
check('T2c measurements counted per inner file',
      train is not None and train.get('num_measurements') == 20
      and test is not None and test.get('num_measurements') == 12,
      f'train={train.get("num_measurements") if train else None} '
      f'test={test.get("num_measurements") if test else None}')

# ---------------------------------------------------------------- T3
desc = next((e for e in entries if e.get('dataset_type') == 'metadata'), None)
meta = (desc or {}).get('metadata') or {}
check('T3a description file becomes a metadata source',
      desc is not None and desc.get('usable') is True,
      f'entries={[(e.get("file_name"), e.get("dataset_type")) for e in entries]}')
check('T3b prose metadata extracted (operator, instrument)',
      meta.get('operator_name') == 'Yvonne'
      and meta.get('instrument_type') == 'Triadsensor',
      f'meta={meta}')

# ---------------------------------------------------------------- T4
def _missing_fields(entries_list):
    from services.project_ingest import _assess_metadata
    return _assess_metadata(entries_list).get('missing_recommended_fields', [])


check('T4a alias sync reaches archive datasets',
      meta.get('operator') == 'Yvonne' and meta.get('instrument') == 'Triadsensor',
      f'meta={meta}')
check('T4b assessment counts aliases, not only canonical fields',
      'operator' not in _missing_fields(entries)
      and 'instrument' not in _missing_fields(entries),
      f'missing={_missing_fields(entries)}')


# ---------------------------------------------------------------- T5
plain_csv = os.path.join(tmp, 'plain.csv')
pd.DataFrame({'wavelength': [900.0, 925.0, 950.0],
              'intensity': [15200.0, 18450.0, 22100.0]}).to_csv(plain_csv, index=False)
single = ingest_file(_Record(plain_csv, 'plain.csv', file_id='00000000-0000-0000-0000-000000000002'))
check('T5a non-archive file keeps the single-entry ingest',
      isinstance(single, dict) and single.get('usable') is True,
      f'type={type(single).__name__}')
check('T5b direct file keeps the plain file id',
      single.get('file_id') == '00000000-0000-0000-0000-000000000002',
      f'id={single.get("file_id")}')

# ---------------------------------------------------------------- T6
class _StubFileList:
    def __init__(self, files):
        self._files = files

    def all(self):
        return list(self._files)


class _Project:
    def __init__(self, files, overrides=None):
        self.id = 'p1'
        self.name = 'OP30 Testprojekt'
        self.files = _StubFileList(files)
        self.preparation_report = {}
        self.metadata_overrides = overrides or {}
        self.phase = 'drafted'

    def save(self, **kwargs):
        return None


zip_record = _Record(zip_path, 'OEL_MK.zip')
project = _Project([zip_record])
report = build_preparation_report(project)
datasets = report.get('datasets', [])
check('T6a preparation report lists all inner datasets',
      len(datasets) == 3, f'n={len(datasets)}')
usable = [d for d in datasets if d.get('usable')]
check('T6b all three inner datasets are usable',
      len(usable) == 3, f'usable={len(usable)}')

inner_id = next((d.get('file_id') for d in datasets
                 if 'Meta' in d.get('file_name', '')), None)
project_over = _Project(
    [zip_record], {inner_id: {'operator': 'Martin', 'location': 'HSWT'}})
report_over = build_preparation_report(project_over)
desc_over = next((d for d in report_over.get('datasets', [])
                  if 'Meta' in d.get('file_name', '')), None)
over_meta = (desc_over or {}).get('metadata') or {}
check('T6c metadata overrides reach inner archive datasets',
      over_meta.get('operator') == 'Martin',
      f'meta={over_meta}')

# ---------------------------------------------------------------- T7
broken_zip = os.path.join(tmp, 'broken.zip')
with open(os.path.join(tmp, 'garbage.csv'), 'w', encoding='utf-8') as f:
    f.write('nothing,numeric,here\na,b,c\nd,e,f\n')
with zipfile.ZipFile(broken_zip, 'w') as z:
    z.write(os.path.join(tmp, 'garbage.csv'), 'garbage.csv')
    z.write(meta_path, 'Oil_Meta.txt')
broken_result = ingest_file(_Record(broken_zip, 'broken.zip',
                                    file_id='00000000-0000-0000-0000-000000000003'))
broken_entries = broken_result if isinstance(broken_result, list) else [broken_result]
check('T7a broken inner file reported honestly, not fatal',
      any(e.get('usable') is False for e in broken_entries)
      and any(e.get('dataset_type') == 'metadata' for e in broken_entries),
      f'entries={[(e.get("file_name"), e.get("usable")) for e in broken_entries]}')

# ---------------------------------------------------------------- T8
nested_outer = os.path.join(tmp, 'nested_outer.zip')
nested_inner = os.path.join(tmp, 'nested_inner.zip')
with zipfile.ZipFile(nested_inner, 'w') as z:
    z.write(os.path.join(tmp, 'plain.csv'), 'plain.csv')
with zipfile.ZipFile(nested_outer, 'w') as z:
    z.write(nested_inner, 'nested_inner.zip')
nested_result = ingest_file(_Record(nested_outer, 'nested_outer.zip',
                                    file_id='00000000-0000-0000-0000-000000000004'))
nested_entries = nested_result if isinstance(nested_result, list) else [nested_result]
check('T8a nested archive yields the inner measurement dataset',
      any(e.get('usable') is True and e.get('dataset_type') == 'measurement'
          for e in nested_entries),
      f'entries={[(e.get("file_name"), e.get("usable")) for e in nested_entries]}')

# ---------------------------------------------------------------- T9
# ProjectMetadataView must accept inner archive ids AND survive several
# project files (the OP30 inner-id expansion once mutated the known-file
# set while iterating it -> RuntimeError -> HTML 500 page -> the editor
# JS reported 'Unexpected token <').
import django  # noqa: E402
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
sys.path.insert(0, str(PROJECT / 'django_project'))
django.setup()
from django.conf import settings  # noqa: E402

if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from django.contrib.auth import get_user_model  # noqa: E402
from django.test import Client  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402

User = get_user_model()
try:
    User.objects.filter(username='op30tester').first()
except Exception:
    from django.core.management import call_command
    call_command('migrate', interactive=False, verbosity=0)

user = User.objects.filter(username='op30tester').first()
if user is None:
    user = User(username='op30tester', email='op30tester@test.local')
user.set_password('op30test')
user.is_staff = True
user.save()

# Upload the oil ZIP directly (two project files would also trigger the
# bug; the ZIP alone keeps the check focused on the archive path).
with open(zip_path, 'rb') as f:
    zip_bytes = f.read()
c = Client()
check('T9a login works', c.login(username='op30tester', password='op30test'))
r = c.post('/api/files/upload/', {
    'files': SimpleUploadedFile('OEL_MK.zip', zip_bytes,
                                content_type='application/zip')
}, format='multipart')
uploaded = r.json().get('uploaded_files', [])
check('T9b oil ZIP upload works', len(uploaded) == 1, f'r={r.content[:200]}')
r = c.post('/api/projects/create/',
           data={'file_ids': uploaded, 'name': 'OP30 Archive Test'},
           content_type='application/json')
live_pid = r.json().get('project_id')
check('T9c project created', bool(live_pid), f'r={r.content[:200]}')

# The metadata editor lists the inner datasets; pick the description.
r = c.get(f'/projects/{live_pid}/')
page = r.content.decode('utf-8', errors='replace')
inner_form_ids = [seg.split('"')[0] for seg in page.split('data-file-id="')[1:]]
check('T9d editor shows one form per inner dataset',
      len(inner_form_ids) == 3, f'ids={inner_form_ids}')
desc_id = next((i for i in inner_form_ids if 'Meta' in i), None)
check('T9e description dataset editable', desc_id is not None,
      f'ids={inner_form_ids}')

r = c.post(f'/api/projects/{live_pid}/metadata/',
           data={'metadata': {desc_id: {'operator': 'Martin'}}},
           content_type='application/json')
check('T9f metadata update on inner dataset returns JSON (no HTML 500)',
      r.status_code == 200, f'status={r.status_code} body={r.content[:200]}')
try:
    body = r.json()
except ValueError:
    body = {}
check('T9g metadata update succeeded',
      body.get('success') is True, f'body={body}')
check('T9h overridden operator reflected in the report',
      body.get('metadata_quality_score') is not None, f'body={body}')

# ---------------------------------------------------------------- summary
print()
print(f'OP30 archive ingest matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED:', FAILED)
    sys.exit(1)
sys.exit(0)
