"""OP7 verification: upload -> crew analysis -> report pipeline bridge.

Tests the CrewAI pipeline bridge in the leading project
(NIR_Intelligence-main): the S3 format-agnostic loader feeds the OP6
NIRAnalysisCrew, the crew analysis produces a comprehensive HTML report,
the Django endpoint wiring is correct, and the UI template exposes the
crew analysis button. Offline; the crew runs in standalone mode
(CrewAI package optional, S6/OP6 guarantee).
"""
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

results = []


def check(name, ok, detail=''):
    results.append((name, ok))
    print(f'[{"PASS" if ok else "FAIL"}] {name} {detail}')


PROJECT = Path(__file__).resolve().parent.parent
DJANGO_DIR = PROJECT / 'django_project'

# T1: S3 loader feeds the crew schema (real file from the repo)
from agents.data_preparation_agent import EnhancedDataPreparationAgent

sample_csv = PROJECT / 'data' / 'raw' / 'sample_spectrum.csv'
check('T1a sample spectrum file present', sample_csv.exists(), str(sample_csv))
loader = EnhancedDataPreparationAgent(input_directory=str(sample_csv.parent),
                                      output_directory=tempfile.mkdtemp())
spectral = loader._load_spectral_data(str(sample_csv))
check('T1b S3 loader parses the sample',
      spectral is not None and spectral.get('data') is not None,
      f'keys={sorted(spectral.keys()) if spectral else None}')
df = spectral['data']
wavelength_column = spectral.get('wavelength_column')
intensity_column = spectral.get('intensity_column')
check('T1c unified schema columns resolved',
      wavelength_column in df.columns and intensity_column in df.columns,
      f'wl={wavelength_column} int={intensity_column}')
wavelengths = [float(v) for v in df[wavelength_column].tolist()]
intensities = [float(v) for v in df[intensity_column].tolist()]
check('T1d numeric series extracted', len(wavelengths) > 0 and len(wavelengths) == len(intensities),
      f'n={len(wavelengths)}')

# T2: crew analysis end-to-end with report generation
from agents.nir_analysis_crew import (
    NIRAnalysisCrew, CrewConfiguration, AnalysisRequest, AnalysisMode,
)
from agents.reporting_agent import ReportType, ReportFormat

out_dir = Path(tempfile.mkdtemp(prefix='op7_out_'))
config = CrewConfiguration(enable_crewai=False,
                           temp_dir=tempfile.mkdtemp(prefix='op7_tmp_'),
                           output_dir=str(out_dir))
crew = NIRAnalysisCrew(config)
request = AnalysisRequest(
    sample_id='op7_test',
    spectral_data={'wavelengths': wavelengths, 'intensities': intensities},
    metadata={'file_name': sample_csv.name},
    file_paths=[str(sample_csv)],
    analysis_mode=AnalysisMode.STANDARD,
    report_type=ReportType.COMPREHENSIVE,
    report_format=ReportFormat.HTML,
)
result = crew.analyze_sample(request)
check('T2a crew analysis runs without errors', result.errors == [], f'errors={result.errors}')
check('T2b spectral analysis executed', result.spectral_analysis is not None)
check('T2c quality score defined', result.overall_quality_score >= 0.0)
check('T2d comprehensive HTML report generated',
      len(result.generated_reports) == 1
      and result.generated_reports[0].status.value == 'completed'
      and str(result.generated_reports[0].file_path).endswith('.html'),
      f'reports={len(result.generated_reports)}')
report_path = Path(result.generated_reports[0].file_path)
check('T2e report file exists on disk', report_path.exists(), str(report_path.name))
if report_path.exists():
    content = report_path.read_text(errors='replace')
    check('T2f report is a Quarto document with html format',
          content.startswith('---') and 'format: html' in content
          and 'Comprehensive NIR Analysis Report' in content)

# T3: spectral agent enum regression (INVALID member used by error paths)
from agents.spectral_analysis_agent import SpectrometerIssue
check('T3a SpectrometerIssue.INVALID exists', hasattr(SpectrometerIssue, 'INVALID'))
from agents.spectral_analysis_agent import SpectralAnalysisAgent, AgentStatus
agent = SpectralAnalysisAgent()
ctx = {
    'spectral_data': {'wavelengths': list(range(700, 2500, 10)),
                      'intensities': [1000.0 + (i % 50) for i in range(180)],
                      'sample_id': 'op7'},
    'sample_id': 'op7',
    'metadata': {},
}
spectral_output = agent.execute(ctx)
check('T3b spectral agent completes on valid data',
      spectral_output.status == AgentStatus.COMPLETED,
      f'status={spectral_output.status}')

# T4: crew passes sample_id into the spectral contract
crew_source = (PROJECT / 'agents' / 'nir_analysis_crew.py').read_text()
check('T4a crew injects sample_id into spectral_data',
      '"sample_id": request.sample_id,' in crew_source
      and re.search(r'\*\*request\.spectral_data', crew_source) is not None)

# T5: Django endpoint wiring
sys.path.insert(0, str(DJANGO_DIR))
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
import django
django.setup()
from api.file_urls import urlpatterns
paths = [str(p.pattern) for p in urlpatterns]
check('T5a crew-analysis route registered',
      '<uuid:file_id>/crew-analysis/' in paths)

from django.urls import resolve, Resolver404

for _path, _name in [
    ('/api/files/', 'file-list'),
    ('/api/files/upload/', 'file-upload'),
    ('/api/files/categories/', 'file-categories'),
    ('/api/files/statistics/', 'file-statistics'),
    ('/api/files/delete-multiple/', 'file-delete-multiple'),
    ('/api/files/analyze-multiple/', 'file-analyze-multiple'),
    ('/api/files/00000000-0000-0000-0000-000000000000/crew-analysis/', 'file-crew-analysis'),
    ('/api/files/00000000-0000-0000-0000-000000000000/analyze/', 'file-analyze'),
    ('/api/files/00000000-0000-0000-0000-000000000000/download/', 'file-download'),
    ('/api/files/00000000-0000-0000-0000-000000000000/delete/', 'file-delete'),
]:
    try:
        match = resolve(_path)
        check(f'T5f {_path} resolves', match.view_name == _name,
              f'{match.view_name}')
    except Resolver404:
        check(f'T5f {_path} resolves', False, 'Resolver404')
from api.file_views import FileCrewAnalysisView
check('T5b FileCrewAnalysisView importable', FileCrewAnalysisView is not None)
view_source = (DJANGO_DIR / 'api' / 'file_views.py').read_text()
check('T5c view bridges S3 loader to the crew',
      'EnhancedDataPreparationAgent' in view_source
      and 'NIRAnalysisCrew' in view_source
      and 'analyze_sample' in view_source)
check('T5d view persists crew results on the file record',
      'crew_analysis' in view_source and 'is_analyzed = True' in view_source)
check('T5e view handles non-spectral files gracefully (422)',
      '422' in view_source or 'UNPROCESSABLE' in view_source)

# T6: UI wiring in files.html
template = (DJANGO_DIR / 'templates' / 'files.html').read_text()
check('T6a crewAnalyzeFile JS function present', 'function crewAnalyzeFile(' in template)
check('T6b crew analysis button rendered per file',
      re.search(r"crewAnalyzeFile\(.*file\.id", template) is not None)
check('T6c button calls the crew-analysis endpoint',
      "/api/files/' + fileId + '/crew-analysis/'" in template)

# T7: template compiles with the real Django engine
from django.template.loader import get_template
try:
    get_template('files.html')
    check('T7a files.html compiles', True)
except Exception as exc:
    check('T7a files.html compiles', False, str(exc)[:120])

# T8: regression spot checks (OP6 crew standalone, S3 loader)
from agents.nir_analysis_crew import create_analysis_crew
try:
    crew2 = create_analysis_crew(CrewConfiguration(enable_crewai=False))
    check('T8a crew factory works (OP6 regression)', crew2 is not None)
except Exception as exc:
    check('T8a crew factory works (OP6 regression)', False, str(exc)[:120])

print(f'\n{sum(1 for _, ok in results if ok)}/{len(results)} tests passed')
sys.exit(1 if any(not ok for _, ok in results) else 0)
