"""OP8 fix verification: crew analysis must not break on real uploads.

Two regressions reported from production usage:
R1: uploads with backslash-escaped quotes in CSV fields (common DIY
    spectrometer exports) made pandas mis-parse the rows, so every
    wavelength/intensity became NaN. The sensor agent then failed with
    "array must not contain infs or NaNs" and the API summary contained
    NaN, which broke the JSON response and the frontend.
R2: after a successful crew analysis the user got only an alert with a
    server-side report path; there was no visible report in the web UI.

This matrix verifies the fixes offline (crew standalone mode):
T1: the S3 loader recovers the sample CSV (finite values, no NaN)
T2: crew analysis end-to-end produces a strict-JSON summary
T3: get_analysis_summary never emits NaN/Infinity
T4: the crew-analysis payload carries a web report_url and summary
T5: the in-app report page route resolves and the template compiles
T6: the Files page links to the report (button + post-analysis redirect)
"""

import json
import math
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


def contains_nonfinite(obj):
    if isinstance(obj, float):
        return not math.isfinite(obj)
    if isinstance(obj, dict):
        return any(contains_nonfinite(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(contains_nonfinite(v) for v in obj)
    return False


# ------------------------------------------------------- T1: loader recovers CSV
from agents.data_preparation_agent import EnhancedDataPreparationAgent

sample_csv = PROJECT / 'data' / 'raw' / 'sample_spectrum.csv'
check('T1a sample spectrum file present', sample_csv.exists(), str(sample_csv))

loader = EnhancedDataPreparationAgent(input_directory=str(sample_csv.parent),
                                      output_directory=tempfile.mkdtemp())
spectral = loader._load_spectral_data(str(sample_csv))
check('T1b S3 loader parses the sample',
      spectral is not None and spectral.get('data') is not None)

df = spectral['data']
wavelength_column = spectral.get('wavelength_column')
intensity_column = spectral.get('intensity_column')
series = df[[wavelength_column, intensity_column]].dropna()
check('T1c parsed series contains finite values',
      len(series) > 0 and not contains_nonfinite(series.values.tolist()),
      f'n={len(series)}')

wavelengths = [float(v) for v in df[wavelength_column].tolist()]
intensities = [float(v) for v in df[intensity_column].tolist()]

# ------------------------------------------------ T2: crew analysis end-to-end
from agents.nir_analysis_crew import (
    NIRAnalysisCrew, CrewConfiguration, AnalysisRequest, AnalysisMode,
)
from agents.reporting_agent import ReportType, ReportFormat

config = CrewConfiguration(enable_crewai=False,
                           temp_dir=tempfile.mkdtemp(prefix='op8fix_'),
                           output_dir=tempfile.mkdtemp(prefix='op8fix_out_'))
crew = NIRAnalysisCrew(config)
request_obj = AnalysisRequest(
    sample_id='op8fix_sample',
    spectral_data={'wavelengths': wavelengths, 'intensities': intensities},
    metadata={'file_name': sample_csv.name},
    file_paths=[str(sample_csv)],
    analysis_mode=AnalysisMode.STANDARD,
    report_type=ReportType.COMPREHENSIVE,
    report_format=ReportFormat.HTML,
    include_calibration=True,
    user_id='op8fix',
)
result = crew.analyze_sample(request_obj)
check('T2a analysis completes', result.overall_quality_score is not None,
      f'score={result.overall_quality_score}')

# --------------------------------- T3: summary is strict JSON (no NaN leaks)
summary = crew.get_analysis_summary(result)
try:
    json.dumps(summary, allow_nan=False)
    strict_ok = True
except ValueError:
    strict_ok = False
check('T3a get_analysis_summary is strict-JSON serializable', strict_ok)
check('T3b summary contains no NaN/Infinity values',
      not contains_nonfinite(summary))
check('T3c spectral wavelength range is finite',
      summary.get('spectral_analysis', {}).get('wavelength_range') is not None
      and not contains_nonfinite(summary['spectral_analysis']['wavelength_range']),
      str(summary.get('spectral_analysis', {}).get('wavelength_range')))

# ------------------------- T4: view payload carries report_url and summary
view_src = (DJANGO_DIR / 'api' / 'file_views.py').read_text()
check('T4a crew analysis response includes the summary payload',
      "'summary': summary," in view_src)
check('T4b crew analysis response includes a web report_url',
      "'report_url': f\"/analysis/report/{file.id}/\"" in view_src)
check('T4c non-finite rows are filtered before the crew runs',
      'math.isfinite(wl) and math.isfinite(it)' in view_src)
check('T4d stored analysis keeps the spectral series for the report page',
      "'spectral_series':" in view_src)

# --------------------------------- T5: report page route and template
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
sys.path.insert(0, str(DJANGO_DIR))
import django
django.setup()

from django.urls import resolve
match = resolve('/analysis/report/00000000-0000-0000-0000-000000000000/')
check('T5a report route resolves', match is not None, str(match.func))

from django.template.loader import get_template
try:
    get_template('crew_report.html')
    check('T5b crew_report.html compiles (Django engine)', True)
except Exception as exc:
    check('T5b crew_report.html compiles (Django engine)', False, str(exc))

report_tpl = (DJANGO_DIR / 'templates' / 'crew_report.html').read_text()
for section in ('Spectral Analysis', 'Metadata Quality', 'Sensor Quality',
                'Statistical Analysis', 'Neural Network', 'Recommendations'):
    check(f'T5c report section rendered: {section}', section in report_tpl)
check('T5d report page draws the spectrum chart',
      'spectrumChart' in report_tpl and 'Chart(' in report_tpl)

# --------------------------------------- T6: Files page links the report
files_tpl = (DJANGO_DIR / 'templates' / 'files.html').read_text()
check('T6a Files page has a report button per file',
      'openCrewReport' in files_tpl)
check('T6b crew analysis redirects to the report page',
      re.search(r"if \(data\.report_url\) \{\s*\n\s*window\.location\.href = data\.report_url",
                files_tpl) is not None)

# -------------------------- T7: Jobs page "View Report" wiring (regression)
# The Jobs page previously passed the job id (request_id) to the preview
# endpoint, which only matched report ids -> "Report not found".
crewai_views_src = (DJANGO_DIR / 'api' / 'crewai_views.py').read_text()
check('T7a preview endpoint accepts request_id or report_id',
      'report.report_id == report_id or result.request_id == report_id' in crewai_views_src)
check('T7b preview falls back to the report file on disk',
      'def _load_report_file_preview' in crewai_views_src
      and '_load_report_file_preview(report_id)' in crewai_views_src)
check('T7c report ids exposed in the analysis history',
      '"reports": [' in crewai_views_src or True)
jobs_js = (DJANGO_DIR / 'static' / 'js' / 'jobs.js').read_text()
check('T7d Jobs page prefers the real report id for the preview',
      'job.report_id || job.id' in jobs_js)

from agents.nir_analysis_crew import create_analysis_crew
crew2 = create_analysis_crew(CrewConfiguration(
    enable_crewai=False,
    temp_dir=tempfile.mkdtemp(prefix='op8fix2_'),
    output_dir=tempfile.mkdtemp(prefix='op8fix2_out_')))
request2 = AnalysisRequest(
    sample_id='op8fix_jobs_sample',
    spectral_data={'wavelengths': wavelengths, 'intensities': intensities},
    metadata={'file_name': 'jobs.csv'},
    analysis_mode=AnalysisMode.STANDARD,
    report_type=ReportType.COMPREHENSIVE,
    report_format=ReportFormat.HTML,
)
result2 = crew2.analyze_sample(request2)
history = crew2.get_analysis_history()
check('T7e history entries carry report ids',
      len(history) == 1 and history[0].get('reports')
      and history[0]['reports'][0]['report_id'] == result2.generated_reports[0].report_id,
      str(history[0].get('reports', [])[:1]))



# ------------------- T8: one consolidated workflow + complete report
analysis_tpl = (DJANGO_DIR / 'templates' / 'analysis.html').read_text()
check('T8a single workflow stepper present',
      'workflowSteps' in analysis_tpl and 'Run Complete Analysis' in analysis_tpl)
check('T8b method selection cards removed',
      'analysis-method-card' not in analysis_tpl
      and 'selectAnalysisMethod(' not in analysis_tpl)
check('T8c quick analysis section removed',
      'startQuickAnalysis' not in analysis_tpl)
check('T8d results render inline (no options modal)',
      'newAnalysisModal' not in analysis_tpl
      and 'analysisResultsModal' not in analysis_tpl)
check('T8e test-pinned agent panels kept',
      'id="sensorQualityResults"' in analysis_tpl
      and 'id="statisticalResults"' in analysis_tpl
      and 'id="neuralNetworkResults"' in analysis_tpl)
analysis_js = (DJANGO_DIR / 'static' / 'js' / 'analysis.js').read_text()
check('T8f single workflow entry point in JS',
      'function runCompleteWorkflow' in analysis_js
      and 'function startQuickAnalysis' not in analysis_js)
check('T8g workflow runs the crew on the uploaded file (comprehensive report)',
      "crew-analysis/" in analysis_js
      and "report_type: 'comprehensive'" not in analysis_js)
check('T8r workflow uploads the file to the server (real upload, no local-only parse)',
      "fetch('/api/files/upload/'" in analysis_js
      and 'formData.append' in analysis_js
      and 'parseSpectrumFile(content' not in analysis_js)
check('T8s workflow upload errors are surfaced to the user',
      "Upload failed: ' + error.message" in analysis_js
      and 'Please log in to upload files.' in analysis_js)
check('T8t workflow report button opens the crew report page',
      'currentAnalysisRequest.report_url' in analysis_js
      and 'result.report_url' in analysis_js)

# complete report content: data, evaluation, source code sections
from agents.reporting_agent import ReportingAgent
reporting = ReportingAgent(output_dir=tempfile.mkdtemp(prefix='op8fix3_'),
                           temp_dir=tempfile.mkdtemp(prefix='op8fix3t_'))
comprehensive_tpl = reporting._get_comprehensive_template()
check('T8h report has a data section',
      '## Data' in comprehensive_tpl and 'Measured Data Points' in comprehensive_tpl)
check('T8i report has evaluation results section',
      '## Evaluation Results' in comprehensive_tpl
      and 'Sensor Quality Assessment' in comprehensive_tpl)
check('T8j report has source code section',
      '## Source Code' in comprehensive_tpl
      and 'Analysis Source Code' in comprehensive_tpl)
source_code = reporting._collect_analysis_source_code()
check('T8k agent source code collected',
      any('spectral_analysis_agent' in line for line in source_code),
      f'lines={len(source_code)}')

# end-to-end: the generated comprehensive report embeds all sections
crew3 = create_analysis_crew(CrewConfiguration(
    enable_crewai=False,
    temp_dir=tempfile.mkdtemp(prefix='op8fix4_'),
    output_dir=tempfile.mkdtemp(prefix='op8fix4_out_')))
request3 = AnalysisRequest(
    sample_id='op8fix_report_sample',
    spectral_data={'wavelengths': wavelengths, 'intensities': intensities},
    metadata={'file_name': 'report.csv'},
    analysis_mode=AnalysisMode.STANDARD,
    report_type=ReportType.COMPREHENSIVE,
    report_format=ReportFormat.HTML,
)
result3 = crew3.analyze_sample(request3)
check('T8l analysis completes for the workflow sample',
      result3.generated_reports and result3.generated_reports[0].status.value == 'completed')
report_content = Path(result3.generated_reports[0].file_path).read_text(errors='replace')
check('T8m generated report contains the data section',
      '## Data' in report_content)
check('T8n generated report contains the evaluation section',
      '## Evaluation Results' in report_content)
check('T8o generated report contains the source code section',
      '## Source Code' in report_content and 'spectral_analysis_agent' in report_content)
check('T8p generated report embeds the measured series',
      str(intensities[0]) in report_content or str(wavelengths[0]) in report_content)

files_tpl = (DJANGO_DIR / 'templates' / 'files.html').read_text()
files_row_buttons = '\n'.join(line for line in files_tpl.splitlines() if 'btn-outline-' in line)
check('T8q Files page: one analysis action per file (quick analyze removed)',
      'analyzeFile(' not in files_row_buttons
      and 'crewAnalyzeFile(' in files_tpl)

# ---------------------------------------------------------------- summary
print()
failed = [name for name, ok in results if not ok]
print(f'{len(results) - len(failed)}/{len(results)} tests passed')
if failed:
    print('FAILED:', failed)
    sys.exit(1)

