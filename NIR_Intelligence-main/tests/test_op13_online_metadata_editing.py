"""OP13 verification: online metadata editing in the project report.

The OP10 phase-1 report told the user which metadata fields were missing,
but the only adaptation path was editing files externally and re-uploading
them (out of scope in OP10, MO 2-4 wants the user to improve the metadata
assessment). OP13 adds the online path: a metadata editor per dataset on
the project page stores overrides on the project, the preparation report
is rebuilt and the metadata quality score updates immediately. Offline;
the crew runs in standalone mode (S6/OP6 guarantee).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


PROJECT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# T1: ingest service applies metadata overrides (offline stub project)
# ---------------------------------------------------------------------------
from services.project_ingest import (  # noqa: E402
    RECOMMENDED_METADATA_FIELDS, apply_metadata_overrides, build_preparation_report,
)


class _StubFile:
    def __init__(self, path, name, file_id='f1'):
        self.id = file_id
        self.name = name
        self.file_extension = '.csv'
        self.file_category = 'spectral'
        self._path = path

    def get_file_path(self):
        return self._path


class _StubFileList:
    def __init__(self, files):
        self._files = files

    def all(self):
        return list(self._files)


class _StubProject:
    def __init__(self, files):
        self.id = 'p13'
        self.name = 'OP13 Testprojekt'
        self.files = _StubFileList(files)
        self.preparation_report = {}
        self.metadata_overrides = {}

    def save(self, **kwargs):
        return None


sample_csv = PROJECT / 'data' / 'raw' / 'sample_spectrum.csv'
stub_file = _StubFile(str(sample_csv), 'sample_spectrum.csv')
project = _StubProject([stub_file])
report = build_preparation_report(project)
initial_score = report['metadata_quality']['overall_quality_score']
missing = report['metadata_quality']['missing_recommended_fields']
check('T1a metadata missing initially', len(missing) >= 1, f'missing={missing}')

entry = report['datasets'][0]
apply_metadata_overrides(entry, {'operator': 'M. Meister', 'humidity': ''})
check('T1b override applied', entry['metadata'].get('operator') == 'M. Meister')
check('T1c empty override ignored', 'humidity' not in entry['metadata_user_entered'],
      f'entered={entry.get("metadata_user_entered")}')

project.metadata_overrides = {'f1': {'operator': 'M. Meister'}}
report2 = build_preparation_report(project)
check('T1d score improves via overrides',
      report2['metadata_quality']['overall_quality_score'] > initial_score,
      f'{initial_score} -> {report2["metadata_quality"]["overall_quality_score"]}')
check('T1e user-entered fields tracked',
      report2['datasets'][0].get('metadata_user_entered') == ['operator'])

# ---------------------------------------------------------------------------
# T2: Django wiring - model field, migration, view, route, template
# ---------------------------------------------------------------------------
models_src = (PROJECT / 'django_project' / 'core' / 'models.py').read_text(encoding='utf-8')
check('T2a metadata_overrides field on the model', 'metadata_overrides' in models_src)
migration = PROJECT / 'django_project' / 'core' / 'migrations' / '0005_analysisproject_metadata_overrides.py'
check('T2b migration 0005 exists', migration.exists(), str(migration))

views_src = (PROJECT / 'django_project' / 'api' / 'project_views.py').read_text(encoding='utf-8')
check('T2c ProjectMetadataView exists', 'class ProjectMetadataView' in views_src)
check('T2d metadata view rejects released projects',
      'Project already released' in views_src)
check('T2e metadata view rebuilds the preparation report',
      'build_preparation_report' in views_src.split('class ProjectMetadataView')[1].split('class ProjectReleaseView')[0])

urls_src = (PROJECT / 'django_project' / 'api' / 'project_urls.py').read_text(encoding='utf-8')
check("T2f route 'metadata/' wired", "metadata/" in urls_src
      and 'ProjectMetadataView' in urls_src)

template_src = (PROJECT / 'django_project' / 'templates' / 'project_report.html').read_text(encoding='utf-8')
check('T2g metadata editor in the template', 'metadata-form' in template_src)
check('T2h editor only in drafted phase',
      'project.phase == ' + repr('drafted') in template_src)
check('T2i editor posts to the metadata route', '/metadata/' in template_src)
check('T2j recommended fields prefilled from the assessment',
      'missing_recommended_fields' in template_src)
check('T2k custom fields addable', 'meta-add-field' in template_src)
check('T2l existing override values prefilled',
      'd.metadata.field|default' in template_src)

# ---------------------------------------------------------------------------
# T3: live API contract (Django test client, real ORM)
# ---------------------------------------------------------------------------
import os  # noqa: E402
import django  # noqa: E402

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
sys.path.insert(0, str(PROJECT / 'django_project'))
django.setup()

from django.conf import settings  # noqa: E402
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from django.test import Client  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from core.models import AnalysisProject  # noqa: E402

User = get_user_model()
try:
    User.objects.filter(username='op13tester').first()
except Exception:
    from django.core.management import call_command
    call_command('migrate', interactive=False, verbosity=0)
user = User.objects.filter(username='op13tester').first()
if user is None:
    user = User(username='op13tester', email='op13tester@test.local')
user.set_password('op13test')
user.is_staff = True
user.save()

c = Client()
check('T3a login works', c.login(username='op13tester', password='op13test'))

csv_bytes = (b'wavelength,intensity\n'
             b'700,0.10\n750,0.20\n800,0.30\n850,0.40\n900,0.50\n'
             b'950,0.60\n1000,0.70\n1050,0.80\n1100,0.85\n1150,0.90\n')
r = c.post('/api/files/upload/', {
    'files': SimpleUploadedFile('op13_sample.csv', csv_bytes, content_type='text/csv')
}, format='multipart')
file_ids = r.json().get('uploaded_files', [])
check('T3b upload works', len(file_ids) == 1)

r = c.post('/api/projects/create/',
           data={'file_ids': file_ids, 'name': 'OP13 Metadaten Test'},
           content_type='application/json')
pid = r.json().get('project_id')
check('T3c project created in drafted phase', bool(pid))

r = c.post(f'/api/projects/{pid}/metadata/',
           data={'metadata': {file_ids[0]: {'operator': 'M. Meister',
                                             'instrument': 'DIY-Spektrometer V2'}}},
           content_type='application/json')
body = r.json() if r.status_code == 200 else {}
check('T3d metadata update accepted', r.status_code == 200 and body.get('success') is True,
      f'status={r.status_code} body={str(body)[:200]}')
check('T3e score reported back', 'metadata_quality_score' in body,
      f'body={str(body)[:200]}')

project = AnalysisProject.objects.get(id=pid)
prep = project.preparation_report
score = prep['metadata_quality']['overall_quality_score']
check('T3f preparation report updated (score improved)', score == 40.0,
      f'score={score}')
check('T3g overrides persisted on the project',
      project.metadata_overrides.get(file_ids[0], {}).get('operator') == 'M. Meister')
check('T3h merged metadata visible in the report dataset',
      prep['datasets'][0]['metadata'].get('instrument') == 'DIY-Spektrometer V2')

r = c.post(f'/api/projects/{pid}/release/', content_type='application/json')
check('T3i project can be released after metadata edit', r.status_code == 200)

r = c.post(f'/api/projects/{pid}/metadata/',
           data={'metadata': {file_ids[0]: {'operator': 'X'}}},
           content_type='application/json')
check('T3j metadata edit rejected after release', r.status_code == 409,
      f'status={r.status_code}')

# ---------------------------------------------------------------------------
# T4: template compiles
# ---------------------------------------------------------------------------
from django.template.loader import get_template  # noqa: E402

try:
    get_template('project_report.html')
    check('T4a project_report.html compiles', True)
except Exception as e:
    check('T4a project_report.html compiles', False, str(e))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f'OP13 online metadata editing matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', FAILED)
sys.exit(1 if FAIL else 0)
