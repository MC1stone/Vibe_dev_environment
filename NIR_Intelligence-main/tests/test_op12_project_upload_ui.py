"""OP12 verification: project creation UI on the projects page.

The OP10 UI linked 'Dateien hochladen' to the legacy files page - files
were uploaded there, but no project was created; the project workflow
was only reachable via the API. OP12 closes the gap in the UI per the
mission statement (MO 1): the projects page gets its own upload modal
that uploads the files, creates the project and navigates to the
preparation report. Offline; no network, no CrewAI package needed.
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
# T1: projects.html upload modal wiring (static template checks)
# ---------------------------------------------------------------------------
template_path = PROJECT / 'django_project' / 'templates' / 'projects.html'
check('T1a projects.html exists', template_path.exists())
src = template_path.read_text(encoding='utf-8') if template_path.exists() else ''

check('T1b upload modal present',
      'projectUploadModal' in src)
check('T1c multi-file input in the modal',
      'id="projectFiles"' in src and 'multiple' in src)
check('T1d project name input optional',
      'id="projectName"' in src)
check('T1e upload posts to /api/files/upload/',
      "/api/files/upload/" in src)
check('T1f project creation posts to /api/projects/create/',
      "/api/projects/create/" in src)
check('T1g file ids from upload passed to project create',
      'uploaded_files' in src and 'file_ids' in src)
check('T1h navigates to the project detail after creation',
      "window.location.href = '/projects/' + projectData.project_id" in src)
check('T1i csrf token sent on both requests',
      src.count('X-CSRFToken') >= 2)
check('T1j error path shown to the user (upload failure)',
      'Upload fehlgeschlagen' in src)
check('T1k error path shown to the user (project failure)',
      'Projekt konnte nicht angelegt werden' in src)
check('T1l legacy /files/ link replaced by the modal',
      'href="/files/"' not in src)

# ---------------------------------------------------------------------------
# T2: API contract the modal relies on (offline, Django test client)
# ---------------------------------------------------------------------------
import django  # noqa: E402
import os  # noqa: E402

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
sys.path.insert(0, str(PROJECT / 'django_project'))
django.setup()

from django.test import Client  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from core.models import AnalysisProject  # noqa: E402

User = get_user_model()
user = User.objects.filter(username='op12tester').first()
if user is None:
    user = User(username='op12tester', email='op12tester@test.local')
user.set_password('op12test')
user.is_staff = True
user.save()

c = Client()
check('T2a login works', c.login(username='op12tester', password='op12test'))

csv_bytes = (b'wavelength,intensity\n'
             b'700,0.10\n750,0.20\n800,0.30\n850,0.40\n900,0.50\n'
             b'950,0.60\n1000,0.70\n1050,0.80\n1100,0.85\n1150,0.90\n')
r = c.post('/api/files/upload/', {
    'files': SimpleUploadedFile('op12_sample.csv', csv_bytes, content_type='text/csv')
}, format='multipart')
body = r.json() if r.status_code == 200 else {}
check('T2b upload endpoint works (modal contract)',
      r.status_code == 200 and body.get('success') is True,
      f'status={r.status_code} body={str(body)[:200]}')
file_ids = body.get('uploaded_files', [])
check('T2c uploaded_files ids returned (modal contract)',
      len(file_ids) == 1, f'ids={file_ids}')

r = c.post('/api/projects/create/',
           data={'file_ids': file_ids, 'name': 'OP12 UI Projekt'},
           content_type='application/json')
body = r.json() if r.status_code == 200 else {}
check('T2d project create endpoint works (modal contract)',
      r.status_code == 200 and body.get('success') is True and body.get('project_id'),
      f'status={r.status_code} body={str(body)[:200]}')
pid = body.get('project_id')
if pid:
    project = AnalysisProject.objects.get(id=pid)
    check('T2e project in drafted phase with preparation report',
          project.phase == 'drafted' and bool(project.preparation_report))
    r = c.get(f'/projects/{pid}/')
    check('T2f project detail page renders (navigation target)',
          r.status_code == 200)

# ---------------------------------------------------------------------------
# T3: template compiles
# ---------------------------------------------------------------------------
from django.template.loader import get_template  # noqa: E402

try:
    get_template('projects.html')
    check('T3a projects.html compiles', True)
except Exception as e:
    check('T3a projects.html compiles', False, str(e))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f'OP12 project creation UI matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', FAILED)
sys.exit(1 if FAIL else 0)
