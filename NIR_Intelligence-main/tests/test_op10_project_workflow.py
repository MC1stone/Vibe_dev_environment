"""OP10 verification: project workflow upload -> preparation -> release -> crew -> report.

Tests the project workflow in the leading project (NIR_Intelligence-main):
an uploaded file opens a new AnalysisProject (phase 1 'drafted'), the ingest
service turns it into usable datasets (measurement data + metadata assessment
with improvement recommendations), the user releases the project, phase 2 runs
the full NIRAnalysisCrew with per-agent report sections and the final
comprehensive report is generated and served. Offline; the crew runs in
standalone mode (CrewAI package optional, S6/OP6 guarantee).
"""
import json
import os
import sys
import tempfile
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
# T1: preparation report (phase 1) from the S3 loader over real repo data
# ---------------------------------------------------------------------------
from services.project_ingest import build_preparation_report  # noqa: E402


class _StubFile:
    """Minimal GenericFile stand-in for offline ingest tests."""

    def __init__(self, path, name, file_id='f1', file_extension='.csv', file_category='spectral'):
        self.id = file_id
        self.name = name
        self.file_extension = file_extension
        self.file_category = file_category
        self._path = path

    def get_file_path(self):
        return self._path


class _StubProject:
    """Minimal AnalysisProject stand-in (no Django ORM in offline tests)."""

    def __init__(self, files):
        self.id = 'p1'
        self.name = 'OP10 Testprojekt'
        self.files = _StubFileList(files)
        self.preparation_report = {}

    def save(self, **kwargs):
        return None


class _StubFileList:
    def __init__(self, files):
        self._files = files

    def all(self):
        return list(self._files)


sample_csv = PROJECT / 'data' / 'raw' / 'sample_spectrum.csv'
check('T1a sample spectrum present', sample_csv.exists(), str(sample_csv))

stub_file = _StubFile(str(sample_csv), 'sample_spectrum.csv')
project = _StubProject([stub_file])
report = build_preparation_report(project)
check('T1b preparation report built', isinstance(report, dict), f'keys={sorted(report.keys())}')
datasets = report.get('datasets', [])
check('T1c one dataset per file', len(datasets) == 1, f'n={len(datasets)}')
check('T1d dataset usable', datasets and datasets[0].get('usable') is True,
      f'dataset={datasets[0] if datasets else None}')
check('T1e dataset has measurement data',
      datasets and datasets[0].get('preview', {}).get('wavelengths'),
      'no wavelength preview')
check('T1f dataset has metadata dict',
      datasets and isinstance(datasets[0].get('metadata'), dict))
check('T1g metadata quality assessed',
      'overall_quality_score' in report.get('metadata_quality', {}),
      f'quality={report.get("metadata_quality")}')
check('T1h recommendations for the user',
      len(report.get('recommendations', [])) >= 1,
      f'recs={report.get("recommendations")}')

# Unusable file reported, not fatal
stub_txt = _StubFile(str(sample_csv) + '.missing', 'gone.csv', file_id='f2')
report2 = build_preparation_report(_StubProject([stub_file, stub_txt]))
check('T1i unusable file reported gracefully',
      report2.get('usable_dataset_count') == 1 and report2.get('total_dataset_count') == 2,
      f'report={report2.get("usable_dataset_count")}/{report2.get("total_dataset_count")}')
check('T1j improvement recommendation for unusable file',
      any('gone.csv' in r for r in report2.get('recommendations', [])),
      f'recs={report2.get("recommendations")}')

# ---------------------------------------------------------------------------
# T2: phase 2 crew run with per-agent reports and final report file
# ---------------------------------------------------------------------------
from services.project_crew import run_project_crew  # noqa: E402


class _StubUser:
    id = 'u1'
    user_id = 'u1'


class _FullStubProject(_StubProject):
    def __init__(self, files):
        super().__init__(files)
        self.user = _StubUser()
        self.crew_results = {}
        self.final_report_path = ''
        self.phase = 'released'

    def save(self, **kwargs):
        return None


full_project = _FullStubProject([stub_file])
build_preparation_report(full_project)
crew_results = run_project_crew(full_project)
check('T2a crew run returns results', isinstance(crew_results, dict),
      f'keys={sorted(crew_results.keys())}')
check('T2b overall quality score computed',
      isinstance(crew_results.get('overall_quality_score'), (int, float)),
      f'score={crew_results.get("overall_quality_score")}')
per_agent = crew_results.get('per_agent_reports', [])
check('T2c per-agent reports present', len(per_agent) >= 5,
      f'n={len(per_agent)} sections={[(s.get("agent"), s.get("status")) for s in per_agent]}')
agent_keys = {s.get('agent') for s in per_agent}
check('T2d spectral analysis section', 'spectral_analysis' in agent_keys, str(agent_keys))
check('T2e metadata quality section', 'metadata_quality' in agent_keys, str(agent_keys))
check('T2f sensor quality section', 'sensor_quality' in agent_keys, str(agent_keys))
check('T2g statistical analysis section', 'statistical_analysis' in agent_keys, str(agent_keys))
check('T2h neural network section', 'neural_network' in agent_keys, str(agent_keys))
check('T2i similarity section', 'faiss_similarity' in agent_keys, str(agent_keys))
completed_sections = [s for s in per_agent if s.get('status') == 'completed']
check('T2j agent sections completed', len(completed_sections) >= 5,
      f'completed={len(completed_sections)}/{len(per_agent)}')
check('T2k spectral chart data available',
      crew_results.get('spectral_series', {}).get('wavelengths') is not None,
      'no spectral series for charts')
final_path = Path(full_project.final_report_path)
check('T2l final comprehensive report generated',
      final_path.exists() and final_path.suffix == '.html',
      f'path={full_project.final_report_path}')
if final_path.exists():
    content = final_path.read_text(encoding='utf-8')
    check('T2m final report has content', len(content) > 500, f'len={len(content)}')

# strict JSON serializability of the crew results (web API contract)
try:
    json.dumps(crew_results, allow_nan=False)
    check('T2n crew results strictly JSON serializable', True)
except ValueError as e:
    check('T2n crew results strictly JSON serializable', False, str(e))

# ---------------------------------------------------------------------------
# T3: Django wiring - model, migration, views, URLs, templates
# ---------------------------------------------------------------------------
models_src = (PROJECT / 'django_project' / 'core' / 'models.py').read_text(encoding='utf-8')
check('T3a AnalysisProject model exists', 'class AnalysisProject' in models_src)
migration = PROJECT / 'django_project' / 'core' / 'migrations' / '0004_analysisproject.py'
check('T3b AnalysisProject migration exists', migration.exists(), str(migration))
if migration.exists():
    mig_src = migration.read_text(encoding='utf-8')
    check('T3c migration creates the project table',
          'AnalysisProject' in mig_src and 'CreateModel' in mig_src)

views_src = (PROJECT / 'django_project' / 'api' / 'project_views.py').read_text(encoding='utf-8')
for view_name in ('ProjectListView', 'ProjectCreateView', 'ProjectDetailView',
                  'ProjectReingestView', 'ProjectReleaseView', 'ProjectFinalReportView'):
    check(f'T3d view {view_name}', f'class {view_name}' in views_src)
check('T3e release runs the crew via service',
      'run_project_crew' in views_src)
check('T3f create runs the ingest via service',
      'build_preparation_report' in views_src)

urls_src = (PROJECT / 'django_project' / 'api' / 'project_urls.py').read_text(encoding='utf-8')
for route in ("path('',", 'create/', 'reingest/', 'release/', 'final-report/'):
    check(f'T3g project route {route!r}', route in urls_src)

root_urls = (PROJECT / 'django_project' / 'nir_web' / 'urls.py').read_text(encoding='utf-8')
check('T3h project urls included', "include('api.project_urls')" in root_urls)

for template in ('projects.html', 'project_report.html'):
    tpath = PROJECT / 'django_project' / 'templates' / template
    check(f'T3i template {template} exists', tpath.exists())
template_src = (PROJECT / 'django_project' / 'templates' / 'project_report.html').read_text(encoding='utf-8')
check('T3j release button wired (drafted phase)',
      'btn-release' in template_src and '/release/' in template_src)
check('T3k reingest button wired (user adaptation)',
      'btn-reingest' in template_src and '/reingest/' in template_src)
check('T3l per-agent sections rendered', 'per_agent_reports' in template_src)
check('T3m final report link rendered', 'final_report_url' in template_src)

# template syntax compile (same approach as the OP3 matrix)
import django  # noqa: E402
from django.conf import settings  # noqa: E402

if not settings.configured:
    settings.configure(
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [str(PROJECT / 'django_project' / 'templates')],
            'APP_DIRS': False,
            'OPTIONS': {},
        }],
        INSTALLED_APPS=['django.contrib.contenttypes', 'django.contrib.auth'],
    )
django.setup()
from django.template.loader import get_template  # noqa: E402
for template in ('projects.html', 'project_report.html'):
    try:
        get_template(template)
        check(f'T3n template {template} compiles', True)
    except Exception as e:
        check(f'T3n template {template} compiles', False, str(e))

# URL resolution smoke test: read the URL config the same way Django does
# without configuring the full settings (offline; 'core' app import needs DB
# settings, so we verify the module source and its imports statically here
# plus via the manage.py check run in CI).
try:
    import ast as _ast
    src = (PROJECT / 'django_project' / 'api' / 'project_urls.py').read_text(encoding='utf-8')
    tree = _ast.parse(src)
    views_imported = {a.name for node in tree.body if isinstance(node, _ast.ImportFrom)
                      for a in node.names}
    for view_name in ('ProjectListView', 'ProjectCreateView', 'ProjectDetailView',
                      'ProjectReingestView', 'ProjectReleaseView', 'ProjectFinalReportView'):
        check(f'T3o-{view_name} imported in urls', view_name in views_imported)
    check('T3o urlpatterns defined', 'urlpatterns' in src)
except Exception as e:
    check('T3o project urls static check', False, str(e))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f'OP10 project workflow matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', FAILED)
sys.exit(1 if FAIL else 0)
