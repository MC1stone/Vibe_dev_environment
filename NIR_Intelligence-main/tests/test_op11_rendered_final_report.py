"""OP11 verification: rendered final project report with embedded charts.

The OP10 local test showed that the final report was delivered as raw
Quarto markdown inside a .html file and contained no charts. OP11 replaces
the project final report with a rendered, self-contained HTML document:
overview KPIs, spectrum chart (measurement data), per-agent quality bar
chart (evaluation), per-agent sections, original data, recommendations
and the analysis source code. Offline; matplotlib optional (charts
degrade gracefully), the crew runs in standalone mode (S6/OP6 guarantee).
"""
import json
import re
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
# T1: report builder unit checks (matplotlib optional, charts degrade)
# ---------------------------------------------------------------------------
import services.project_report as project_report  # noqa: E402
from services.project_report import (  # noqa: E402
    generate_final_html_report,
    quality_bar_chart_data_url,
    spectrum_chart_data_url,
)

check('T1a matplotlib availability detected correctly',
      project_report.MATPLOTLIB_AVAILABLE == bool(_try_mpl()) if (_try_mpl := lambda: __import__('importlib').util.find_spec('matplotlib')) else True)

check('T1b spectrum chart empty without data',
      spectrum_chart_data_url([]) == '')

sample_csv = PROJECT / 'data' / 'raw' / 'sample_spectrum.csv'
datasets_stub = [{
    'file_name': 'sample.csv',
    'wavelengths': [700.0, 750.0, 800.0, 850.0],
    'intensities': [0.1, 0.2, 0.3, 0.4],
}, {
    'file_name': 'preview_only.csv',
    'preview': {'wavelengths': [900.0, 950.0], 'intensities': [0.5, 0.6]},
}]
spectrum_url = spectrum_chart_data_url(datasets_stub)
check('T1c spectrum chart from full series + preview fallback',
      spectrum_url.startswith('data:image/png;base64,'),
      f'got {spectrum_url[:40]}')

per_agent_stub = [
    {'agent': 'spectral_analysis', 'title': 'Spektralanalyse', 'status': 'completed',
     'data': {'quality_score': 100.0}},
    {'agent': 'metadata_quality', 'title': 'Metadatenbewertung', 'status': 'completed',
     'data': {'overall_quality_score': 72.0}},
    {'agent': 'sensor_quality', 'title': 'Sensorqualität', 'status': 'completed',
     'data': {'overall_quality_score': 0.91}},  # 0-1 score must scale to 100
    {'agent': 'failed_agent', 'title': 'Ohne Score', 'status': 'failed', 'data': {}},
]
bar_url = quality_bar_chart_data_url(per_agent_stub)
check('T1d quality bar chart rendered', bar_url.startswith('data:image/png;base64,'))
check('T1e quality bar chart empty without scored sections',
      quality_bar_chart_data_url([]) == '')

# ---------------------------------------------------------------------------
# T2: full rendered report (offline stub project, no Django ORM)
# ---------------------------------------------------------------------------
from services.project_ingest import build_preparation_report  # noqa: E402


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
        self.id = 'p11'
        self.name = 'OP11 Testprojekt'
        self.files = _StubFileList(files)
        self.preparation_report = {}
        self.crew_results = {}
        self.final_report_path = ''

    def save(self, **kwargs):
        return None


stub_file = _StubFile(str(sample_csv), 'sample_spectrum.csv')
project = _StubProject([stub_file])
build_preparation_report(project)
usable = [d for d in project.preparation_report.get('datasets', []) if d.get('usable')]
full_series = [{'file_name': d['file_name'],
                'wavelengths': d['preview']['wavelengths'],
                'intensities': d['preview']['intensities']} for d in usable]

crew_results = {
    'request_id': 'req-op11',
    'overall_quality_score': 88.8,
    'datasets_analyzed': 1,
    'processing_time': 1.23,
    'recommendations': ['Metadatenfeld "operator" ergänzen'],
    'warnings': ['Demo-Warnung'],
    'errors': [],
    'per_agent_reports': [
        {'agent': 'spectral_analysis', 'title': 'Spektralanalyse (Qualität)',
         'status': 'completed',
         'data': {'quality_score': 100.0, 'quality_grade': 'excellent'}},
        {'agent': 'metadata_quality', 'title': 'Metadatenbewertung',
         'status': 'completed',
         'data': {'overall_quality_score': 72.0, 'recommendations': ['operator ergänzen']}},
        {'agent': 'sensor_quality', 'title': 'Sensorqualität', 'status': 'completed',
         'data': {'overall_quality_score': 91.0, 'noise_level': 0.004}},
        {'agent': 'statistical_analysis', 'title': 'Statistische Analyse',
         'status': 'completed', 'data': {'methods_applied': ['pca', 'pls']}},
        {'agent': 'neural_network', 'title': 'Neuronale Netzwerkanalyse',
         'status': 'completed', 'data': {'r2_score': 0.87}},
        {'agent': 'calibration', 'title': 'Kalibration', 'status': 'completed',
         'data': {'rmse': 0.21}},
        {'agent': 'faiss_similarity', 'title': 'Spektren-Datenbankvergleich',
         'status': 'completed', 'data': {'similarity_score': 0.95}},
    ],
}

report_path = Path(generate_final_html_report(project, crew_results,
                                             full_series=full_series))
check('T2a report file written', report_path.exists() and report_path.suffix == '.html',
      str(report_path))
html = report_path.read_text(encoding='utf-8') if report_path.exists() else ''

check('T2b rendered HTML document (not raw markdown)',
      html.lstrip().lower().startswith('<!doctype html') and '<html' in html.lower())
check('T2c no raw quarto/r fragments left',
      '```{r}' not in html and '`r params$' not in html and '`r ifelse' not in html)
chart_imgs = re.findall(r'<img class="chart" src="data:image/png;base64,', html)
check('T2d embedded spectrum + quality charts',
      len(chart_imgs) == 2, f'charts={len(chart_imgs)}')
check('T2e overview KPIs rendered',
      'Gesamtqualität' in html and 'Datensätze analysiert' in html)
check('T2f per-agent sections rendered',
      all(title in html for title in
          ('Spektralanalyse', 'Metadatenbewertung', 'Sensorqualität',
           'Statistische Analyse', 'Neuronale Netzwerkanalyse',
           'Kalibration', 'Spektren-Datenbankvergleich')))
check('T2g original data table rendered',
      'Originaldaten' in html and 'Wellenlänge (nm)' in html)
check('T2h source code section rendered',
      'Quellcode der Analyse' in html and 'project_crew.py' in html)
check('T2i recommendations rendered',
      'Metadatenfeld "operator" ergänzen' in html or 'operator' in html)
check('T2j warnings section rendered', 'Demo-Warnung' in html)
check('T2k status badges rendered', 'badge-ok' in html)

# per-agent chart data must survive the strict web API JSON contract
try:
    json.dumps(crew_results, allow_nan=False)
    check('T2l crew results strictly JSON serializable', True)
except ValueError as e:
    check('T2l crew results strictly JSON serializable', False, str(e))

# ---------------------------------------------------------------------------
# T3: crew integration - the final report comes from the OP11 builder
# ---------------------------------------------------------------------------
from services.project_crew import run_project_crew, _generate_final_report  # noqa: E402


class _StubUser:
    id = 'u1'
    user_id = 'u1'


class _FullStubProject(_StubProject):
    def __init__(self, files):
        super().__init__(files)
        self.user = _StubUser()
        self.phase = 'released'

    def save(self, **kwargs):
        return None


full_project = _FullStubProject([stub_file])
build_preparation_report(full_project)
crew_out = run_project_crew(full_project)
final_path = Path(full_project.final_report_path)
check('T3a crew run completed', isinstance(crew_out, dict)
      and crew_out.get('overall_quality_score') is not None)
check('T3b final report is a rendered OP11 html report',
      final_path.exists() and final_path.name.startswith('final_'),
      f'path={full_project.final_report_path}')
if final_path.exists():
    final_html = final_path.read_text(encoding='utf-8')
    check('T3c crew final report rendered (no raw quarto markdown)',
          final_html.lstrip().lower().startswith('<!doctype html')
          and '```{r}' not in final_html)
    check('T3d crew final report has embedded charts',
          len(re.findall(r'<img class="chart" src="data:image/png;base64,', final_html)) >= 1)
    check('T3e crew final report has original data',
          'Originaldaten' in final_html)
    check('T3f crew final report has source code',
          'Quellcode der Analyse' in final_html)

import inspect  # noqa: E402
src = inspect.getsource(_generate_final_report)
check('T3g crew final report uses the OP11 report builder',
      'generate_final_html_report' in src)

# ---------------------------------------------------------------------------
# T4: source wiring checks
# ---------------------------------------------------------------------------
crew_src = (PROJECT / 'services' / 'project_crew.py').read_text(encoding='utf-8')
check('T4a legacy template rendering kept as fallback',
      '_generate_final_report_legacy' in crew_src)
check('T4b full measurement series passed to the report',
      'full_series' in crew_src)
check('T4c report builder module exists',
      (PROJECT / 'services' / 'project_report.py').exists())
report_src = (PROJECT / 'services' / 'project_report.py').read_text(encoding='utf-8')
check('T4d matplotlib optional (degrades without charts)',
      'MATPLOTLIB_AVAILABLE' in report_src)
check('T4e source files embedded in the report',
      'project_ingest.py' in report_src and 'project_crew.py' in report_src)

views_src = (PROJECT / 'django_project' / 'api' / 'project_views.py').read_text(encoding='utf-8')
check('T4f final report view serves the generated file',
      'final_report_path' in views_src and 'text/html' in views_src)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f'OP11 rendered final report matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', FAILED)
sys.exit(1 if FAIL else 0)
