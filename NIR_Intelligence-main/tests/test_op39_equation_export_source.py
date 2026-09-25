"""OP39 verification: calibration equation + print/MD export + source code.

User requirement: "Die Kalllibrungsgleichung fehlt; Füge auch eine Print
option ein MD und PDF; Es fehlt auch noch der Sourcode der Auswertungen,
fuege diesen in alle abschnitte als ausfuehrbaren code mit ein."

T1  equation: PLS fit returns intercept + coefficient per channel
T2  equation is executable: y = intercept + sum(coef*(x-mean)/std)
T3  equation carries R2_fit/RMSEC (in-sample, documented) + top terms
T4  equation: too few samples -> honest 'unavailable', no invention
T5  equation: constant target -> honest 'unavailable'
T6  crew: calibration section carries the equation in its data
T7  HTML report: equation block rendered (intercept, terms table)
T8  HTML report: unavailable equation -> no block (no invention)
T9  HTML report: print button + @media print CSS present
T10 HTML report: markdown download link present
T11 HTML report: source code embedded per agent section
T12 source mapping covers all 8 agent keys
T13 markdown report: heading, KPI table, equation, findings
T14 markdown report: source code fences (executable python blocks)
T15 markdown route resolves (Django URL config)
T16 view: markdown download endpoint exists and serves attachment
"""
import os
import sys
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


import numpy as np  # noqa: E402
from services.calibration_charts import calibration_equation  # noqa: E402
from services import project_report  # noqa: E402

rng = np.random.default_rng(7)
WL = np.arange(600.0, 1100.0, 25.0)
base = 1000.0 + 50.0 * np.sin((WL - 600.0) / 150.0)
samples, refs = [], []
for i in range(30):
    x = base + rng.normal(0, 8.0, len(WL))
    samples.append(x.tolist())
    refs.append(5.0 + 0.01 * (x[3] - 1000.0) * 20 + rng.normal(0, 0.1))

# ---------------------------------------------------------------- T1-T5
eq = calibration_equation(samples, refs, WL.tolist(), target_name='Fett')
check('T1 equation: intercept + coefficient per channel',
      eq['status'] == 'ok'
      and isinstance(eq['intercept'], float)
      and len(eq['coefficients']) == len(WL)
      and len(eq['wavelengths_nm']) == len(WL),
      f"status={eq.get('status')}")
pred = eq['intercept'] + sum(
    c * (x - m) / s for c, x, m, s in
    zip(eq['coefficients'], samples[0], eq['channel_mean'], eq['channel_std']))
check('T2 equation is executable (reproduces the prediction)',
      abs(pred - refs[0]) < 1.0,
      f'pred={pred:.3f} vs ref={refs[0]:.3f}')
check('T3 equation carries R2_fit/RMSEC + top terms',
      0 <= eq['r2_fit'] <= 1 and eq['rmsec'] >= 0
      and eq['top_terms'] and all('coefficient' in t for t in eq['top_terms'])
      and eq['note'],
      f"r2={eq.get('r2_fit')} terms={len(eq.get('top_terms') or [])}")
eq_few = calibration_equation(samples[:3], refs[:3], WL.tolist())
check('T4 too few samples -> honest unavailable',
      eq_few['status'] == 'unavailable' and eq_few.get('reason'), '')
eq_const = calibration_equation(samples, [5.0] * 30, WL.tolist())
check('T5 constant target -> honest unavailable',
      eq_const['status'] == 'unavailable', '')

# ---------------------------------------------------------------- T6
src = (PROJECT / 'services' / 'project_crew.py').read_text(encoding='utf-8')
check('T6 crew wires the equation into the calibration section',
      'calibration_equation(' in src
      and "cal_section['data']['calibration_equation'] = equation" in src, '')

# ---------------------------------------------------------------- T7-T12
cal_section = {'agent': 'calibration', 'title': 'Kalibration (PLS, PCR)',
               'status': 'completed',
               'data': {'best_method': 'PLS', 'calibration_equation': eq,
                        'methods_tested': ['PLS']}}
html = project_report._agent_section_html(cal_section)
check('T7 equation block rendered with intercept + terms',
      'Kalibrierungsgleichung' in html
      and 'coef' in html and 'Kanal-Mittelwert' in html,
      html[:200])
html_no_eq = project_report._agent_section_html(
    {'agent': 'calibration', 'status': 'completed',
     'data': {'calibration_equation': {'status': 'unavailable'}}})
check('T8 unavailable equation -> no block (no invention)',
      'Kalibrierungsgleichung' not in html_no_eq, '')


class _StubProject:
    id = 'p39'
    name = 'OP39 Testprojekt'
    preparation_report = {'datasets': []}
    crew_results = {}


crew_results = {'request_id': 'req-op39', 'overall_quality_score': 82.0,
                'datasets_analyzed': 1, 'processing_time': 1.0,
                'recommendations': [], 'warnings': [], 'errors': [],
                'per_agent_reports': [cal_section]}
report_path = Path(project_report.generate_final_html_report(
    _StubProject(), crew_results))
full_html = report_path.read_text(encoding='utf-8')
check('T9 print button + print CSS in the report',
      'window.print()' in full_html and '@media print' in full_html, '')
check('T10 markdown download link in the report',
      'final-report/markdown/' in full_html, '')
check('T11 source code embedded per agent section',
      'calibration_agent.py' in full_html
      and 'calibration_charts.py' in full_html
      and 'def calibration_equation' in full_html,
      '')
check('T12 source mapping covers all 8 agent keys',
      set(project_report.AGENT_SOURCE_FILES) == {
          'spectral_analysis', 'metadata_quality', 'sensor_quality',
          'statistical_analysis', 'neural_network', 'calibration',
          'faiss_similarity', 'outlier_analysis'},
      f"keys={sorted(project_report.AGENT_SOURCE_FILES)}")

# ---------------------------------------------------------------- T13-T14
md_path = Path(project_report.generate_markdown_report(
    _StubProject(), crew_results))
md = md_path.read_text(encoding='utf-8')
check('T13 markdown: heading + KPI table + equation',
      md.startswith('# OP39 Testprojekt')
      and '| Kennzahl | Wert |' in md
      and 'Kalibrierungsgleichung' in md and 'SUM_i' in md,
      md[:150])
check('T14 markdown: executable python source fences',
      '```python' in md and 'def calibration_equation' in md
      and 'ausführbar' in md, '')

# ---------------------------------------------------------------- T15-T16
sys.path.insert(0, str(PROJECT / 'django_project'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
import django  # noqa: E402
django.setup()

from django.urls import resolve  # noqa: E402
match = resolve(
    '/projects/12345678-1234-5678-1234-567812345678/final-report/markdown/')
check('T15 markdown route resolves',
      match.url_name == 'project-final-report-markdown', '')

views_src = (PROJECT / 'django_project' / 'api' / 'project_views.py'
             ).read_text(encoding='utf-8')
check('T16 markdown view serves an attachment download',
      'ProjectFinalReportMarkdownView' in views_src
      and "Content-Disposition" in views_src
      and 'generate_markdown_report' in views_src, '')

report_path.unlink()
md_path.unlink()

# ---------------------------------------------------------------- summary
print()
print(f'OP39 equation + export + source matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', FAILED)
    sys.exit(1)
