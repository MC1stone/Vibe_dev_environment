"""OP38 verification: honest spectrum figure after the outlier analysis.

User requirement: "wir sollten aber die verfaelschte darstellung der
hochgeladenen spektren nach der ausreisser analyse hinzufuegen, da sonst
die Abbildung 1 falsch darstellt."

Abbildung 1 plots the preparation preview - the median over ALL
measurements, outliers included. That misrepresented the data as soon as
the OP37 outlier analysis found deviants. OP38 adds the honest view:
when outliers exist, the raw median is drawn dashed grey AND the cleaned
median (non-outlier measurements only) is added as the solid curve.

T1  cleaned median differs from the raw median when outliers exist
T2  cleaned median equals the median over the non-outlier measurements
T3  not assessable -> None (honest, no invented curve)
T4  all measurements outliers -> None (nothing left to clean)
T5  numpy/guard: verdict without assessable flag -> None
T6  spectrum_outlier_map: verdicts + cleaned medians from per_agent
T7  spectrum_outlier_map: not-assessable sections are ignored (empty map)
T8  spectrum_outlier_map: length mismatch -> no cleaned curve (no crash)
T9  chart with outliers renders (data url, cleaned curve drawn)
T10 chart without outlier verdict stays exactly as before (compat)
T11 chart with verdict but missing samples falls back (no crash)
T12 empty datasets -> '' (OP11 contract kept)
T13 chart title carries the 'bereinigt' suffix only when cleaned
T14 caption title is honest (mentions Median + bereinigte Kurve)
T15 student report explanation mentions the dashed/cleaned curves
T16 full report render: figure 1 caption + cleaned chart embedded
T17 full report render without outlier section: unchanged overview
T18 wiring: generate_final_html_report feeds the outlier map
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
from services import outlier_analysis, project_report, student_report  # noqa: E402

rng = np.random.default_rng(11)
WL = np.array([610.0, 680.0, 730.0, 760.0, 810.0, 860.0, 560.0, 585.0,
               645.0, 705.0, 900.0, 940.0])
WL_LIST = WL.tolist()


def _spectrum():
    base = 1000.0 + 50.0 * np.sin((WL - 560.0) / 100.0)
    return base + rng.normal(0, 3.0, len(WL))


clean = np.array([_spectrum() for _ in range(20)])
dirty = clean.copy()
dirty[4] = (dirty[4]
            - 120.0 * np.exp(-((WL - 940.0) / 25.0) ** 2)
            + 90.0 * np.exp(-((WL - 760.0) / 30.0) ** 2))
verdict = outlier_analysis.detect_outliers(dirty.tolist(), WL_LIST)

# ---------------------------------------------------------------- T1-T5
cleaned = outlier_analysis.cleaned_median(dirty.tolist(), verdict)
raw_median = np.median(dirty, axis=0)
check('T1 cleaned median differs from raw median (outliers removed)',
      verdict['outlier_indices'] == [4]
      and cleaned is not None
      and not np.allclose(cleaned, raw_median),
      f"outliers={verdict['outlier_indices']}")
inlier_median = np.median(
    [dirty[i] for i in range(20) if i != 4], axis=0)
check('T2 cleaned median equals the median over non-outliers',
      np.allclose(cleaned, inlier_median), '')

verdict_few = outlier_analysis.detect_outliers(clean[:3].tolist(), WL_LIST)
check('T3 not assessable -> None (honest)',
      outlier_analysis.cleaned_median(clean[:3].tolist(), verdict_few) is None)
check('T4 all measurements outliers -> None',
      outlier_analysis.cleaned_median(
          dirty.tolist(),
          {'assessable': True, 'outlier_indices': list(range(20))}) is None)
check('T5 unassessable verdict dict -> None',
      outlier_analysis.cleaned_median(
          dirty.tolist(), {'outlier_indices': [4]}) is None)

# ---------------------------------------------------------------- T6-T8
dataset = {'file_name': 'oel.csv',
           'usable': True,
           'wavelengths': WL_LIST,
           'intensities': raw_median.tolist(),
           'measurement_samples': dirty.tolist()}
outlier_section = {'agent': 'outlier_analysis', 'status': 'completed',
                   'data': {'file_name': 'oel.csv', 'assessable': True,
                            'measurement_count': 20,
                            'outlier_indices': [4], 'threshold': 3.5,
                            'findings': []}}
v_map, c_map = project_report.spectrum_outlier_map(
    [outlier_section], [dataset])
check('T6 map carries verdict + cleaned median for the dataset',
      v_map.get('oel.csv', {}).get('outlier_indices') == [4]
      and len(c_map.get('oel.csv', [])) == len(WL_LIST),
      f'v={list(v_map)} c={list(c_map)}')

not_assessable = {'agent': 'outlier_analysis', 'status': 'completed',
                  'data': {'file_name': 'oel.csv', 'assessable': False,
                           'measurement_count': 3, 'outlier_indices': [],
                           'reason': 'zu wenige Messungen'}}
v_empty, c_empty = project_report.spectrum_outlier_map(
    [not_assessable], [dataset])
check('T7 not-assessable section -> empty map (no false marking)',
      not v_empty and not c_empty, f'v={v_empty} c={c_empty}')

mismatch = dict(dataset)
mismatch['wavelengths'] = WL_LIST[:6]
v_mm, c_mm = project_report.spectrum_outlier_map(
    [outlier_section], [mismatch])
check('T8 wavelength length mismatch -> no cleaned curve, no crash',
      v_mm.get('oel.csv') is not None and 'oel.csv' not in c_mm,
      f'c={list(c_mm)}')

# ---------------------------------------------------------------- T9-T13
url_cleaned = project_report.spectrum_chart_data_url(
    [dataset], outlier_map=v_map, cleaned_medians=c_map)
check('T9 chart with outliers + cleaned curve renders',
      url_cleaned.startswith('data:image/png;base64,'),
      f'got {url_cleaned[:40]}')
url_plain = project_report.spectrum_chart_data_url([dataset])
url_plain_again = project_report.spectrum_chart_data_url(
    [dataset], outlier_map={}, cleaned_medians={})
check('T10 without outlier verdict the chart is unchanged (compat)',
      url_plain.startswith('data:image/png;base64,')
      and url_plain == url_plain_again)
url_missing_samples = project_report.spectrum_chart_data_url(
    [dataset], outlier_map=v_map, cleaned_medians={})
check('T11 verdict but no cleaned curve -> plain line fallback (no crash)',
      url_missing_samples.startswith('data:image/png;base64,'))
check('T12 empty datasets -> empty string (OP11 contract)',
      project_report.spectrum_chart_data_url([]) == '')

src = (PROJECT / 'services' / 'project_report.py').read_text(encoding='utf-8')
check('T13 chart title suffix only when cleaned (source wiring)',
      "has_cleaned = False" in src
      and "if has_cleaned else ''" in src
      and "bereinigt nach Ausreisser-Analyse" in src)

check('T14 figure caption title is honest',
      'Median' in project_report._CHART_TITLES['spectrum']
      and 'bereinigte' in project_report._CHART_TITLES['spectrum'],
      f"title={project_report._CHART_TITLES['spectrum']!r}")
explanation = student_report._CHART_EXPLANATIONS['spectrum']
check('T15 student report explains dashed raw + cleaned curve',
      'gestrichelt' in explanation and 'bereinigte' in explanation,
      f'text={explanation[:120]!r}')

# ---------------------------------------------------------------- T16-T18
sys.path.insert(0, str(PROJECT / 'django_project'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
import django  # noqa: E402
django.setup()


class _StubProject:
    def __init__(self, prep):
        self.id = 'p38'
        self.name = 'OP38 Testprojekt'
        self.preparation_report = prep
        self.crew_results = {}
        self.final_report_path = ''


crew_results = {
    'request_id': 'req-op38',
    'overall_quality_score': 80.0,
    'datasets_analyzed': 1,
    'processing_time': 0.5,
    'recommendations': [],
    'warnings': [],
    'errors': [],
    'per_agent_reports': [outlier_section],
}
project = _StubProject({'datasets': [dict(dataset)]})
report_path = Path(project_report.generate_final_html_report(
    project, crew_results, full_series=[{
        'file_name': 'oel.csv', 'wavelengths': WL_LIST,
        'intensities': raw_median.tolist()}]))
html = report_path.read_text(encoding='utf-8') if report_path.exists() else ''
overview = html.split('<h2>Agenten-Berichte')[0]
check('T16 full report embeds figure 1 with honest caption + note',
      report_path.exists()
      and 'Abbildung 1' in overview
      and 'Ausreisser-Hinweis' in overview
      and 'data:image/png;base64,' in overview,
      f'path={report_path}')

project_plain = _StubProject({'datasets': [dict(dataset)]})
crew_plain = dict(crew_results)
crew_plain['per_agent_reports'] = [
    {'agent': 'spectral_analysis', 'title': 'Spektralanalyse',
     'status': 'completed', 'data': {'quality_score': 90.0}}]
html_plain = Path(project_report.generate_final_html_report(
    project_plain, crew_plain, full_series=[{
        'file_name': 'oel.csv', 'wavelengths': WL_LIST,
        'intensities': raw_median.tolist()}])).read_text(encoding='utf-8')
overview_plain = html_plain.split('<h2>Agenten-Berichte')[0]
check('T17 report without outlier section: no cleaned-note',
      'Abbildung 1' in overview_plain
      and 'Ausreisser-Hinweis' not in overview_plain, '')

check('T18 generate_final_html_report feeds the outlier map (source wiring)',
      'spectrum_outlier_map(per_agent, datasets)' in src, '')

# ---------------------------------------------------------------- summary
print()
print(f'OP38 spectrum cleaned matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', FAILED)
    sys.exit(1)
