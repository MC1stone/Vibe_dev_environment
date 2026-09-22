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

# ---------------------------------------------------------------- summary
print()
failed = [name for name, ok in results if not ok]
print(f'{len(results) - len(failed)}/{len(results)} tests passed')
if failed:
    print('FAILED:', failed)
    sys.exit(1)
